import torch
import numpy as np
import random
import itertools
import pickle
import hashlib
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Draw
from pathlib import Path

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from algorithms.base import Algorithm, register_algorithm
from config import (
    SEQUENCE_CLASSIFIER_MODEL_DIR,
    PRIZE_TABLE,
    TICKET_COST_PER_TABLE,
    NUM_COMBINATIONS_TO_RECOMMEND
)
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from services.simulation_helpers.simulation_utils import calculate_roi_with_tax
from .lstm_model import LottoLSTM, draws_to_sequences

logger = get_backend_logger()

@register_algorithm
class SequenceClassificationLSTM_GridSearch_Algorithm(Algorithm):
    version = "sequence_lstm_classifier_gridsearch"
    description = "Grid search over LSTM hyperparameters, returns best results. Praisin' the FSM!"

    _best_params_cache = {}

    def _get_cache_key(self, draws):
        # Use a hash of the draw dates as a cache key
        key = ','.join(str(d.date) for d in draws)
        return hashlib.md5(key.encode()).hexdigest()

    def _load_best_params_from_disk(self, cache_key):
        cache_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"gridsearch_best_{cache_key}.pkl")
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_best_params_to_disk(self, cache_key, best_params):
        cache_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"gridsearch_best_{cache_key}.pkl")
        with open(cache_path, 'wb') as f:
            pickle.dump(best_params, f)

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, db: Session = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        logger.info("Arrr! LSTM Grid Search run method called! Praisin' the FSM!")
        hyperparams_grid = {
            'hidden_size': [64, 128, 256],
            'num_layers': [1, 2, 3],
            'seq_len': [10, 20],
            'lr': [0.001, 0.0005, 0.0003],
            'batch_size': [8, 16],
            'epochs': [20],
        }
        test_count = 12
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
            logger.info(f"Arrr! [FSM GRID] No cached best params, runnin' grid search! Praisin' the FSM!")
            results = []
            param_names = list(hyperparams_grid.keys())
            best_result = None
            best_roi = float('-inf')
            for values in itertools.product(*hyperparams_grid.values()):
                params = dict(zip(param_names, values))
                model_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"sequence_classifier_grid_h{params['hidden_size']}_l{params['num_layers']}_s{params['seq_len']}_lr{params['lr']}_b{params['batch_size']}.pt")
                logger.info(f"Arrr! [FSM GRID] Trainin' with params: {params}")
                model = LottoLSTM(num_numbers=37, seq_len=params['seq_len'], hidden_size=params['hidden_size'], num_layers=params['num_layers'])
                need_train = True
                if os.path.exists(model_path):
                    try:
                        state_dict = torch.load(model_path)
                        model.load_state_dict(state_dict)
                        dummy_input = torch.zeros((1, params['seq_len'], 37))
                        model.eval()
                        with torch.no_grad():
                            _ = model(dummy_input)
                        logger.info(f"Arrr! [FSM GRID] Loaded existing model for {params}")
                        need_train = False
                    except Exception as e:
                        logger.warning(f"Arrr! [FSM GRID] Model file mismatch or unusable, will retrain: {e}")
                        try:
                            os.remove(model_path)
                            logger.info(f"Arrr! [FSM GRID] Deleted mismatched model file: {model_path}")
                        except Exception as del_e:
                            logger.error(f"Arrr! [FSM GRID] Failed to delete model file: {model_path}, error: {del_e}")
                        if os.path.exists(model_path):
                            logger.error(f"Arrr! [FSM GRID] Model file still exists after delete attempt: {model_path}")
                        need_train = True
                if need_train:
                    X, y = draws_to_sequences(train_draws, seq_len=params['seq_len'], num_numbers=37)
                    criterion = torch.nn.BCELoss()
                    optimizer = torch.optim.Adam(model.parameters(), lr=params['lr'])
                    for epoch in range(params['epochs']):
                        model.train()
                        permutation = torch.randperm(X.size(0))
                        for i in range(0, X.size(0), params['batch_size']):
                            indices = permutation[i:i+params['batch_size']]
                            batch_x, batch_y = X[indices], y[indices]
                            optimizer.zero_grad()
                            outputs = model(batch_x)
                            loss = criterion(outputs, batch_y)
                            loss.backward()
                            optimizer.step()
                    torch.save(model.state_dict(), model_path)
                    # File sync to ensure data is written to disk
                    try:
                        with open(model_path, 'rb+') as f:
                            f.flush()
                            os.fsync(f.fileno())
                        logger.debug(f"Arrr! [FSM DEBUG] File sync completed for {model_path}", context={"model_path": model_path})
                    except Exception as e:
                        logger.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
                    # Integrity check: try to load the state_dict back
                    try:
                        _ = torch.load(model_path)
                        logger.debug(f"Arrr! [FSM DEBUG] Model integrity check passed for {model_path}", context={"model_path": model_path})
                    except Exception as e:
                        logger.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}", context={"model_path": model_path, "error": str(e)})
                def predict_next_numbers_patched(draws, seq_len=10, threshold=0.5, model_path=None):
                    model = LottoLSTM(
                        num_numbers=37,
                        seq_len=seq_len,
                        hidden_size=params['hidden_size'],
                        num_layers=params['num_layers']
                    )
                    if not os.path.exists(model_path):
                        raise FileNotFoundError(f"Model file not found: {model_path}")
                    model.load_state_dict(torch.load(model_path))
                    model.eval()
                    seq = draws[-seq_len:]
                    x_seq = []
                    for d in seq:
                        onehot = [0]*37
                        for n in d.numbers:
                            onehot[n-1] = 1
                        x_seq.append(onehot)
                    x_tensor = torch.tensor([x_seq], dtype=torch.float32)
                    with torch.no_grad():
                        output = model(x_tensor)[0]
                    pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
                    numbers = [i+1 for i in pred]
                    if len(numbers) > 6:
                        top6 = output.topk(6).indices.tolist()
                        numbers = [i+1 for i in top6]
                    elif len(numbers) < 6:
                        all_numbers = [n for d in draws for n in d.numbers]
                        from collections import Counter
                        freq = Counter(all_numbers)
                        for n, _ in freq.most_common():
                            if n not in numbers:
                                numbers.append(n)
                            if len(numbers) == 6:
                                break
                    return sorted(numbers)
                for strong_name, strong_cls in STRONG_NUMBER_REGISTRY.items():
                    if len(train_draws) < params['seq_len'] + 1:
                        logger.error(f"Arrr! [FSM GRID] Not enough draws for evaluation!")
                        continue
                    strong_algo = strong_cls()
                    all_prizes = 0
                    total_tickets = 0
                    NUM_TABLES_PER_DRAW = 8
                    prizes_list = []
                    for i, test_draw in enumerate(test_draws):
                        available_draws = train_draws + test_draws[:i]
                        combos = []
                        for j in range(NUM_TABLES_PER_DRAW):
                            torch.manual_seed(j)
                            np.random.seed(j)
                            random.seed(j)
                            numbers = predict_next_numbers_patched(available_draws, seq_len=params['seq_len'], threshold=0.2, model_path=model_path)
                            strong = strong_algo.predict(available_draws, numbers=numbers)
                            combos.append({"numbers": numbers, "strong": strong})
                        for combo in combos:
                            hits = sum([n in test_draw.numbers for n in combo["numbers"]])
                            strong_hit = (combo["strong"] == test_draw.strong_number)
                            prize = PRIZE_TABLE.get((hits, strong_hit), 0)
                            all_prizes += prize
                            total_tickets += 1
                            prizes_list.append(prize)
                    total_cost = total_tickets * TICKET_COST_PER_TABLE
                    roi = calculate_roi_with_tax(prizes_list, total_cost)
                    result = {
                        'params': params,
                        'model_path': model_path,
                        'strong_algo': strong_name,
                        'roi': roi,
                        'total_prize': all_prizes,
                        'total_cost': total_cost,
                        'test_count': test_count
                    }
                    results.append(result)
                    logger.info(f"Arrr! [FSM GRID] Model result: {result}")
                    if result['roi'] > best_roi:
                        best_roi = result['roi']
                        best_result = result
            # Instead of returning only the best/top3, return all results for saving
            if use_cache:
                # Save best params to cache
                self._best_params_cache[cache_key] = best_result
                self._save_best_params_to_disk(cache_key, best_result)
            return results
        else:
            logger.debug(f"Arrr! [FSM GRID] Using cached best params! Praisin' the FSM! Params: {best_params}", context={"params": best_params})
            model_path = best_params['model_path']
            strong_cls = STRONG_NUMBER_REGISTRY[best_params['strong_algo']]
            model = LottoLSTM(num_numbers=37, seq_len=best_params['params']['seq_len'], hidden_size=best_params['params']['hidden_size'], num_layers=best_params['params']['num_layers'])
            model.load_state_dict(torch.load(model_path))
            model.eval()
            # Get model output probabilities for the next draw
            seq = draws[-best_params['params']['seq_len']:]
            x_seq = []
            for d in seq:
                onehot = [0]*37
                for n in d.numbers:
                    try:
                        onehot[int(n)-1] = 1  # ensure n is int
                    except Exception as e:
                        logger.error(f"Arrr! [FSM GRID] Error converting number to int: {n}, error: {e}")
                        raise
                x_seq.append(onehot)
            x_tensor = torch.tensor([x_seq], dtype=torch.float32)
            with torch.no_grad():
                output = model(x_tensor)[0].cpu().numpy()
            logger.debug(f"Arrr! [FSM GRID] Model output shape: {output.shape}, dtype: {output.dtype}")
            # Get the top 12 numbers by probability
            top_n_numbers = output.argsort()[-12:][::-1]
            logger.debug(f"Arrr! [FSM GRID] Top 12 numbers: {top_n_numbers}")
            # Generate all 6-number combinations from the top 12
            from itertools import combinations
            combo_candidates = list(combinations(top_n_numbers, 6))
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
                logger.warning(f"[FSM DEBUG] No combos generated, fallback to last test draws! Praisin' the FSM!")
                try:
                    combos = [{
                        "numbers": [int(n) for n in sorted(test_draws[-1].numbers)],
                        "strong": int(getattr(test_draws[-1], 'strong_number', 1)),
                        "params": best_params['params'].copy()
                    }]
                except Exception as e:
                    logger.error(f"Arrr! [FSM GRID] Fallback combo generation failed: {e}")
                    combos = []
            logger.info(f"Arrr! [FSM GRID] Final combos returned: {combos}")
            return combos 