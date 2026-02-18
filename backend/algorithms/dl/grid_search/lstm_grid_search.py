"""LSTM Grid Search Algorithm - Main class"""
import torch
import itertools
import pickle
import hashlib
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Draw
from multiprocessing import Pool, cpu_count

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from algorithms.base import Algorithm, register_algorithm
from config import (
    SEQUENCE_CLASSIFIER_MODEL_DIR,
    NUM_COMBINATIONS_TO_RECOMMEND,
    LOTTO_NUMBERS_COUNT,
    LSTM_GRID_SEARCH_TEST_COUNT,
    LSTM_GRID_SEARCH_THRESHOLD
)
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from ..core.lstm_model import LottoLSTM
from .lstm_grid_search_utils import get_device
from .lstm_grid_search_workers import _evaluate_single_combination_worker

logger = get_backend_logger()


@register_algorithm
class SequenceClassificationLSTM_GridSearch_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_gridsearch"
    description = "Grid search over LSTM hyperparameters, returns best results. Praisin' the FSM!"

    _best_params_cache = {}
    
    def __init__(self):
        """Initialize with configurable parallelization settings"""
        super().__init__() if hasattr(super(), '__init__') else None
        self.parallel_workers = min(3, max(1, cpu_count() - 1))  # Leave 1 core for system
        self.strong_algo_workers = min(5, len(STRONG_NUMBER_REGISTRY)) if STRONG_NUMBER_REGISTRY else 3
        self.use_gpu = True  # Auto-detect GPU
        self.enable_parallel_strong = True
        self.device = get_device() if self.use_gpu else torch.device('cpu')
    
    def _ensure_initialized(self):
        """Ensure instance is initialized (in case __init__ wasn't called)"""
        if not hasattr(self, 'device'):
            self.parallel_workers = min(3, max(1, cpu_count() - 1))
            self.strong_algo_workers = min(5, len(STRONG_NUMBER_REGISTRY)) if STRONG_NUMBER_REGISTRY else 3
            self.use_gpu = True
            self.enable_parallel_strong = True
            self.device = get_device() if self.use_gpu else torch.device('cpu')

    def _get_cache_key(self, draws):
        """Use a hash of the draw dates as a cache key"""
        key = ','.join(str(d.date) for d in draws)
        return hashlib.md5(key.encode()).hexdigest()

    def _load_best_params_from_disk(self, cache_key):
        """Load best parameters from disk cache"""
        cache_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"gridsearch_best_{cache_key}.pkl")
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_best_params_to_disk(self, cache_key, best_params):
        """Save best parameters to disk cache"""
        cache_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"gridsearch_best_{cache_key}.pkl")
        with open(cache_path, 'wb') as f:
            pickle.dump(best_params, f)

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Run grid search over LSTM hyperparameters"""
        self._ensure_initialized()  # Ensure initialization
        logger.info("Arrr! LSTM Grid Search run method called! Praisin' the FSM!")
        hyperparams_grid = {
            'hidden_size': [64, 128, 256],
            'num_layers': [1, 2, 3],
            'seq_len': [10, 20],
            'lr': [0.001, 0.0005, 0.0003],
            'batch_size': [8, 16],
            'epochs': [20],
        }
        test_count = LSTM_GRID_SEARCH_TEST_COUNT
        if len(draws) < max(hyperparams_grid['seq_len']) + test_count:
            logger.error(f"Arrr! [FSM GRID] Not enough draws for grid search evaluation!")
            return []
        train_draws = draws[:-test_count]
        test_draws = draws[-test_count:]
        cache_key = self._get_cache_key(train_draws)
        best_params = None
        if use_cache:
            best_params = self._best_params_cache.get(cache_key) or self._load_best_params_from_disk(cache_key)
        if not best_params:
            # Calculate total combinations for progress tracking
            all_combinations = list(itertools.product(*hyperparams_grid.values()))
            total_combinations = len(all_combinations)
            strong_algos_count = len(STRONG_NUMBER_REGISTRY)
            estimated_time_per_combo = 10  # minutes
            total_estimated_hours = (total_combinations * estimated_time_per_combo) / 60
            
            logger.info(
                f"Arrr! [FSM GRID] No cached best params, runnin' grid search! Praisin' the FSM!",
                context={
                    "total_combinations": total_combinations,
                    "strong_algos_per_combo": strong_algos_count,
                    "test_draws_per_eval": test_count,
                    "estimated_time_per_combo_minutes": estimated_time_per_combo,
                    "estimated_total_hours": round(total_estimated_hours, 1)
                }
            )
            results = []
            param_names = list(hyperparams_grid.keys())
            best_result = None
            best_roi = float('-inf')
            
            # Prepare arguments for parallel processing
            combination_args = [
                (combo_idx, dict(zip(param_names, values)), train_draws, test_draws, total_combinations, strong_algos_count)
                for combo_idx, values in enumerate(all_combinations, 1)
            ]
            
            # Use parallel processing for combinations
            logger.info(
                f"Arrr! [FSM GRID] Starting parallel grid search with {self.parallel_workers} workers",
                context={
                    "parallel_workers": self.parallel_workers,
                    "strong_algo_workers": self.strong_algo_workers,
                    "device": str(self.device),
                    "use_gpu": self.use_gpu and torch.cuda.is_available(),
                    "parallel_strong": self.enable_parallel_strong
                }
            )
            
            # Process combinations in parallel
            # Create wrapper that includes instance configuration
            def worker_wrapper(args):
                return _evaluate_single_combination_worker(
                    args, self.device, self.enable_parallel_strong, self.strong_algo_workers
                )
            
            with Pool(processes=self.parallel_workers) as pool:
                combination_results = pool.map(worker_wrapper, combination_args)
            
            # Flatten results from all combinations
            for combo_results in combination_results:
                if combo_results:
                    results.extend(combo_results)
                    # Track best result
                    for result in combo_results:
                        if result['roi'] > best_roi:
                            best_roi = result['roi']
                            best_result = result
            # Instead of returning only the best/top3, return all results for saving
            logger.info(
                f"Arrr! [FSM GRID] Grid search complete! Tested {total_combinations} combinations",
                context={
                    "total_combinations": total_combinations,
                    "total_results": len(results),
                    "best_roi": best_roi,
                    "best_params": best_result['params'] if best_result else None
                }
            )
            if use_cache:
                # Save best params to cache
                self._best_params_cache[cache_key] = best_result
                self._save_best_params_to_disk(cache_key, best_result)
            return results
        else:
            # Use cached best params to generate predictions
            logger.debug(f"Arrr! [FSM GRID] Using cached best params! Praisin' the FSM! Params: {best_params}", context={"params": best_params})
            model_path = best_params['model_path']
            strong_cls = STRONG_NUMBER_REGISTRY[best_params['strong_algo']]
            model = LottoLSTM(num_numbers=LOTTO_NUMBERS_COUNT, seq_len=best_params['params']['seq_len'], hidden_size=best_params['params']['hidden_size'], num_layers=best_params['params']['num_layers'])
            model.load_state_dict(torch.load(model_path, map_location=self.device))
            model = model.to(self.device)
            model.eval()
            # Get model output probabilities for the next draw
            seq = draws[-best_params['params']['seq_len']:]
            x_seq = []
            for d in seq:
                onehot = [0]*LOTTO_NUMBERS_COUNT
                for n in d.numbers:
                    try:
                        onehot[int(n)-1] = 1  # ensure n is int
                    except Exception as e:
                        logger.error(f"Arrr! [FSM GRID] Error converting number to int: {n}, error: {e}")
                        raise
                x_seq.append(onehot)
            x_tensor = torch.tensor([x_seq], dtype=torch.float32).to(self.device)
            with torch.no_grad():
                output = model(x_tensor)[0].cpu().numpy()
            logger.debug(f"Arrr! [FSM GRID] Model output shape: {output.shape}, dtype: {output.dtype}")
            # Get the top 12 numbers by probability
            TOP_N_FOR_COMBOS = 12
            top_n_numbers = output.argsort()[-TOP_N_FOR_COMBOS:][::-1]
            logger.debug(f"Arrr! [FSM GRID] Top {TOP_N_FOR_COMBOS} numbers: {top_n_numbers}")
            # Generate all 6-number combinations from the top 12
            from itertools import combinations
            NUMBERS_PER_COMBO = 6
            combo_candidates = list(combinations(top_n_numbers, NUMBERS_PER_COMBO))
            logger.debug(f"Arrr! [FSM GRID] Generated {len(combo_candidates)} combo candidates")
            # Score each combo by the sum of probabilities
            scored_combos = []
            for combo in combo_candidates:
                score = sum(output[i] for i in combo)
                scored_combos.append((score, combo))
            # Sort combos by score, descending
            scored_combos.sort(reverse=True, key=lambda x: x[0])
            # Take the top 8 unique combos
            unique_combos = []
            seen = set()
            for score, combo in scored_combos:
                sorted_combo = tuple(sorted(combo))
                if sorted_combo not in seen:
                    seen.add(sorted_combo)
                    unique_combos.append(sorted_combo)
                if len(unique_combos) == (num_to_recommend or NUM_COMBINATIONS_TO_RECOMMEND):
                    break
            logger.debug(f"Arrr! [FSM GRID] Unique combos count: {len(unique_combos)}")
            # Convert combos to the required format, ensure native ints and always include params
            combos = []
            strong_algo = strong_cls()
            for combo in unique_combos:
                try:
                    numbers = [int(i)+1 for i in combo]  # ensure native int
                    strong = strong_algo.predict(draws, numbers=numbers)
                    params = {
                        "seq_len": best_params['params']['seq_len'],
                        "model_version": self.version,
                        "top_n": top_n,
                        "num_for_analysis": num_for_analysis,
                        "num_to_recommend": num_to_recommend
                    }
                    combos.append({
                        "numbers": [int(n) for n in numbers],
                        "strong": int(strong) if hasattr(strong, '__int__') else strong,
                        "params": params
                    })
                except Exception as e:
                    logger.error(f"Arrr! [FSM GRID] Error generating combo: {combo}, error: {e}")
            if not combos:
                logger.warning(f"[FSM DEBUG] No combos generated, fallback to last draw! Praisin' the FSM!")
                try:
                    last_draw = draws[-1] if draws else None
                    if last_draw:
                        combos = [{
                            "numbers": [int(n) for n in sorted(last_draw.numbers)],
                            "strong": int(getattr(last_draw, 'strong_number', 1)),
                            "params": best_params['params'].copy()
                        }]
                    else:
                        combos = []
                except Exception as e:
                    logger.error(f"Arrr! [FSM GRID] Fallback combo generation failed: {e}")
                    combos = []
            logger.info(f"Arrr! [FSM GRID] Final combos returned: {combos}")
            return combos
