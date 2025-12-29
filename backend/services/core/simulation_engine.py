from sqlalchemy.orm import Session
from typing import Any, List, Dict
from models import Draw
from algorithms.base import ALGORITHM_REGISTRY
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from services.simulation_helpers.simulation_print import print_combo_index_insights, print_table_summary
from services.core.algorithm_runner import AlgorithmRunner
from services.core.simulation_constants import MAX_WORKERS, MIN_TRAINING_DRAWS
from shared.logging_service import get_backend_logger

logger = get_backend_logger()

class SimulationEngine:
    def __init__(self, db: Session):
        self.db = db

    def run_comparison(
        self, 
        train_start, 
        train_end, 
        test_count=12, 
        top_n=3, 
        algo_names=None, 
        strong_algo_names=None, 
        use_cache=True
    ):
        """Run comparison of algorithm pairs"""
        logger.info(
            "[FSM DEBUG] Starting run_comparison",
            context={
                "train_start": train_start,
                "train_end": train_end,
                "test_count": test_count,
                "top_n": top_n,
                "algo_names": algo_names,
                "strong_algo_names": strong_algo_names,
                "use_cache": use_cache
            }
        )
        t_start = time.time()
        logger.info(
            "Arrr! Available algorithms in registry",
            context={"algorithms": list(ALGORITHM_REGISTRY.keys())}
        )
        logger.info(
            "Arrr! Available strong number algorithms",
            context={"algorithms": list(STRONG_NUMBER_REGISTRY.keys())}
        )
        
        # Check cache
        if not hasattr(self, '_cache'):
            self._cache = {}
        cache_key = (
            str(train_start), str(train_end), test_count, top_n,
            tuple(sorted(algo_names)) if algo_names else None,
            tuple(sorted(strong_algo_names)) if strong_algo_names else None
        )
        if use_cache and cache_key in self._cache:
            logger.info("[FSM DEBUG] Returning cached result", context={"cache_key": cache_key})
            return self._cache[cache_key]
        
        # Load and validate draws
        draws, test_draws = self._load_and_validate_draws(train_start, train_end, test_count)
        
        # Get algorithms to run
        algos_to_run = ALGORITHM_REGISTRY.items() if not algo_names else [
            (k, v) for k, v in ALGORITHM_REGISTRY.items() if k in algo_names
        ]
        strong_algos_to_run = STRONG_NUMBER_REGISTRY.items() if not strong_algo_names else [
            (k, v) for k, v in STRONG_NUMBER_REGISTRY.items() if k in strong_algo_names
        ]
        
        # Run algorithm pairs in parallel
        results = self._run_algorithm_pairs(
            draws, test_draws, algos_to_run, strong_algos_to_run, 
            top_n, use_cache, test_count, train_start, train_end
        )
        
        logger.info(
            "[FSM DEBUG] run_comparison finished",
            context={"execution_time": f"{time.time() - t_start:.2f}s"}
        )
        self._cache[cache_key] = results
        return results
    
    def _load_and_validate_draws(self, train_start, train_end, test_count) -> tuple[List[Draw], List[Draw]]:
        """Load and validate training and test draws"""
        t_start = time.time()
        draws = self.db.query(Draw).filter(
            Draw.date >= train_start, 
            Draw.date <= train_end, 
            Draw.strong_number <= 7
        ).order_by(Draw.date).all()
        filtered_count = self.db.query(Draw).filter(
            Draw.date >= train_start, 
            Draw.date <= train_end, 
            Draw.strong_number == 8
        ).count()
        logger.info(
            "Arrr! Filtered out draws with strong_number == 8 in training, praisin' the FSM!",
            context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
        )
        logger.info(
            "[FSM DEBUG] Loaded training draws",
            context={"count": len(draws), "time": f"{time.time() - t_start:.2f}s"}
        )
        
        t_test = time.time()
        test_draws = self.db.query(Draw).filter(
            Draw.date > train_end, 
            Draw.strong_number <= 7
        ).order_by(Draw.date).limit(test_count).all()
        filtered_test_count = self.db.query(Draw).filter(
            Draw.date > train_end, 
            Draw.strong_number == 8
        ).count()
        logger.info(
            "Arrr! Filtered out draws with strong_number == 8 in testing, praisin' the FSM!",
            context={"filtered_count": filtered_test_count, "total_after_filter": len(test_draws)}
        )
        logger.info(
            "[FSM DEBUG] Loaded test draws",
            context={"count": len(test_draws), "time": f"{time.time() - t_test:.2f}s"}
        )
        
        if not draws:
            logger.error(
                "[FSM ERROR] No training draws loaded",
                context={"train_start": train_start, "train_end": train_end}
            )
            raise ValueError(f"No training draws loaded for range {train_start} to {train_end}")
        if not test_draws:
            logger.error(
                "[FSM ERROR] No test draws loaded",
                context={"train_end": train_end}
            )
            raise ValueError(f"No test draws loaded after {train_end}")
        
        # Validate draw data
        for idx, draw in enumerate(draws):
            if not hasattr(draw, 'numbers') or draw.numbers is None or not isinstance(draw.numbers, (list, tuple)):
                logger.error(
                    "[FSM ERROR] Training draw has invalid numbers",
                    context={"index": idx, "numbers": getattr(draw, 'numbers', None)}
                )
                raise ValueError(f"Training draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
        
        for idx, draw in enumerate(test_draws):
            if not hasattr(draw, 'numbers') or draw.numbers is None or not isinstance(draw.numbers, (list, tuple)):
                logger.error(
                    "[FSM ERROR] Test draw has invalid numbers",
                    context={"index": idx, "numbers": getattr(draw, 'numbers', None)}
                )
                raise ValueError(f"Test draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
            if not hasattr(draw, 'strong_number') or draw.strong_number is None:
                logger.error(
                    "[FSM ERROR] Test draw has invalid strong_number",
                    context={"index": idx, "strong_number": getattr(draw, 'strong_number', None)}
                )
                raise ValueError(f"Test draw at index {idx} has invalid strong_number: {getattr(draw, 'strong_number', None)}")
        
        return draws, test_draws
    
    def _run_algorithm_pairs(
        self, 
        draws: List[Draw], 
        test_draws: List[Draw],
        algos_to_run: List[tuple],
        strong_algos_to_run: List[tuple],
        top_n: int,
        use_cache: bool,
        test_count: int,
        train_start,
        train_end
    ) -> Dict:
        """Run algorithm pairs in parallel"""
        runner = AlgorithmRunner(draws, test_draws, top_n, use_cache, train_start, train_end)
        
        max_workers = min(MAX_WORKERS, len(list(algos_to_run)) * len(list(strong_algos_to_run)))
        logger.info(
            "Arrr! Processing algorithm pairs with concurrent workers",
            context={
                "max_workers": max_workers,
                "total_pairs": len(list(algos_to_run)) * len(list(strong_algos_to_run))
            }
        )
        
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pair = {
                executor.submit(
                    runner.run_algo_pair, main_version, algo_cls, strong_version, strong_cls, test_count
                ): (main_version, strong_version)
                for main_version, algo_cls in algos_to_run
                for strong_version, strong_cls in strong_algos_to_run
            }
            for future in as_completed(future_to_pair):
                pair, result = future.result()
                results[pair] = result

        return results

    def print_combo_index_insights(self, results):
        print_combo_index_insights(results)

    def print_table_summary(self, results):
        print_table_summary(results)

    def run_strong_number_comparison(self, train_start, train_end, test_count=12, algo_names=None):
        logger.info(f"[FSM DEBUG] Starting run_strong_number_comparison: train_start={train_start}, train_end={train_end}, test_count={test_count}, algo_names={algo_names}")
        t_start = time.time()
        draws = self.db.query(Draw).filter(Draw.date >= train_start, Draw.date <= train_end).order_by(Draw.date).all()
        test_draws = self.db.query(Draw).filter(Draw.date > train_end).order_by(Draw.date).limit(test_count).all()
        results = {}
        algos_to_run = STRONG_NUMBER_REGISTRY.items() if not algo_names else [
            (k, v) for k, v in STRONG_NUMBER_REGISTRY.items() if k in algo_names
        ]
        for version, algo_cls in algos_to_run:
            logger.info(f"[FSM DEBUG] Running strong number algorithm: {version}")
            algo = algo_cls()
            correct = 0
            total = 0
            predictions = []
            for test_draw in test_draws:
                available_draws = [d for d in draws if d.date < test_draw.date]
                pred = algo.predict(available_draws)
                predictions.append({
                    "date": test_draw.date,
                    "predicted": pred,
                    "actual": test_draw.strong_number,
                    "correct": pred == test_draw.strong_number
                })
                if pred == test_draw.strong_number:
                    correct += 1
                total += 1
            accuracy = correct / total if total else 0
            results[version] = {
                "accuracy": accuracy,
                "predictions": predictions,
                "total": total,
                "correct": correct
            }
            logger.info(f"[FSM DEBUG] Strong number algorithm {version} accuracy: {accuracy:.3f} ({correct}/{total})")
        logger.info(f"[FSM DEBUG] run_strong_number_comparison finished in {time.time() - t_start:.2f}s")
        return results 