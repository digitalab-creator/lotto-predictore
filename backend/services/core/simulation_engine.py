from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
from models import Draw, Model, ModelType, Prediction, GeneratedCombination, PredictionDetail
from algorithms.base import ALGORITHM_REGISTRY
from config import TICKET_COST_PER_TABLE, NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import logger
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
import inspect
import copy
from db.base import SessionLocal, get_db
from services.simulation_helpers.simulation_utils import calculate_roi_with_tax, to_native
from services.simulation_helpers.simulation_db import get_or_create_model
from services.simulation_helpers.simulation_prize import calculate_prize
from services.simulation_helpers.simulation_print import print_combo_index_insights, print_table_summary
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import backoff  # Add this to requirements.txt if not present

class SimulationEngine:
    def __init__(self, db: Session):
        self.db = db

    def run_comparison(self, train_start, train_end, test_count=12, top_n=3, algo_names=None, strong_algo_names=None, use_cache=True):
        logger.info(f"[FSM DEBUG] Starting run_comparison: train_start={train_start}, train_end={train_end}, test_count={test_count}, top_n={top_n}, algo_names={algo_names}, strong_algo_names={strong_algo_names}, use_cache={use_cache}")
        t_start = time.time()
        logger.info(f"Arrr! Available algorithms in registry: {list(ALGORITHM_REGISTRY.keys())}")
        logger.info(f"Arrr! Available strong number algorithms: {list(STRONG_NUMBER_REGISTRY.keys())}")
        if not hasattr(self, '_cache'):
            self._cache = {}
        cache_key = (str(train_start), str(train_end), test_count, top_n, tuple(sorted(algo_names)) if algo_names else None, tuple(sorted(strong_algo_names)) if strong_algo_names else None)
        if use_cache and cache_key in self._cache:
            logger.info(f"[FSM DEBUG] Returning cached result for key: {cache_key}")
            return self._cache[cache_key]
        draws = self.db.query(Draw).filter(Draw.date >= train_start, Draw.date <= train_end, Draw.strong_number <= 7).order_by(Draw.date).all()
        filtered_count = self.db.query(Draw).filter(Draw.date >= train_start, Draw.date <= train_end, Draw.strong_number == 8).count()
        logger.info(
            "Arrr! Filtered out draws with strong_number == 8 in training, praisin' the FSM!",
            context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
        )
        logger.info(f"[FSM DEBUG] Loaded {len(draws)} training draws in {time.time() - t_start:.2f}s")
        t_test = time.time()
        test_draws = self.db.query(Draw).filter(Draw.date > train_end, Draw.strong_number <= 7).order_by(Draw.date).limit(test_count).all()
        filtered_test_count = self.db.query(Draw).filter(Draw.date > train_end, Draw.strong_number == 8).count()
        logger.info(
            "Arrr! Filtered out draws with strong_number == 8 in testing, praisin' the FSM!",
            context={"filtered_count": filtered_test_count, "total_after_filter": len(test_draws)}
        )
        logger.info(f"[FSM DEBUG] Loaded {len(test_draws)} test draws in {time.time() - t_test:.2f}s")
        if not draws:
            logger.error(f"[FSM ERROR] No training draws loaded for range {train_start} to {train_end}")
            raise ValueError(f"No training draws loaded for range {train_start} to {train_end}")
        if not test_draws:
            logger.error(f"[FSM ERROR] No test draws loaded after {train_end}")
            raise ValueError(f"No test draws loaded after {train_end}")
        for idx, draw in enumerate(draws):
            if not hasattr(draw, 'numbers') or draw.numbers is None or not isinstance(draw.numbers, (list, tuple)):
                logger.error(f"[FSM ERROR] Training draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
                raise ValueError(f"Training draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
        for idx, draw in enumerate(test_draws):
            if not hasattr(draw, 'numbers') or draw.numbers is None or not isinstance(draw.numbers, (list, tuple)):
                logger.error(f"[FSM ERROR] Test draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
                raise ValueError(f"Test draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
            if not hasattr(draw, 'strong_number') or draw.strong_number is None:
                logger.error(f"[FSM ERROR] Test draw at index {idx} has invalid strong_number: {getattr(draw, 'strong_number', None)}")
                raise ValueError(f"Test draw at index {idx} has invalid strong_number: {getattr(draw, 'strong_number', None)}")
        results = {}
        algos_to_run = ALGORITHM_REGISTRY.items() if not algo_names else [
            (k, v) for k, v in ALGORITHM_REGISTRY.items() if k in algo_names
        ]
        strong_algos_to_run = STRONG_NUMBER_REGISTRY.items() if not strong_algo_names else [
            (k, v) for k, v in STRONG_NUMBER_REGISTRY.items() if k in strong_algo_names
        ]

        @backoff.on_exception(
            backoff.expo,
            (OperationalError, SQLAlchemyError),
            max_tries=3,
            max_time=300
        )
        def run_algo_pair(main_version, algo_cls, strong_version, strong_cls, test_count):
            """Run an algorithm pair with retry logic and proper connection handling"""
            logger.debug(
                f"[FSM DEBUG] Entering run_algo_pair with retry logic",
                context={
                    "main_version": main_version,
                    "strong_version": strong_version
                }
            )
            
            for attempt in range(3):  # Try up to 3 times
                try:
                    with SessionLocal() as session:
                        t_algo = time.time()
                        algo = algo_cls()
                        strong_algo = strong_cls()
                        
                        # Set a longer timeout for LSTM models
                        if 'lstm' in main_version.lower():
                            session.execute(text("SET statement_timeout = '300s'"))  # 5 minutes timeout
                        
                        run_sig = inspect.signature(algo.run)
                        run_kwargs = dict(
                            draws=draws,
                            top_n=top_n,
                            num_for_analysis=NUM_COMBINATIONS_FOR_ANALYSIS,
                            num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND
                        )
                        
                        if 'db' in run_sig.parameters:
                            run_kwargs['db'] = session
                        if hasattr(algo, 'version') and getattr(algo, 'version', None) == 'sequence_lstm_classifier_gridsearch' and 'use_cache' in run_sig.parameters:
                            run_kwargs['use_cache'] = use_cache
                        
                        logger.debug(
                            f"[FSM DEBUG] Running algorithm attempt {attempt + 1}",
                            context={
                                "main_version": main_version,
                                "strong_version": strong_version,
                                "attempt": attempt + 1
                            }
                        )
                        
                        algo_results = algo.run(**run_kwargs)
                        
                        # Reset timeout after LSTM models
                        if 'lstm' in main_version.lower():
                            session.execute(text("SET statement_timeout = '30s'"))  # Reset to default
                        
                        logger.debug(
                            f"[FSM DEBUG] algo.run returned",
                            context={
                                "main_version": main_version,
                                "strong_version": strong_version,
                                "algo_results_raw": str(algo_results)
                            }
                        )
                        if not isinstance(algo_results, list):
                            algo_results = [algo_results]
                        if algo_results and isinstance(algo_results[0], dict) and 'numbers' in algo_results[0]:
                            combos = algo_results
                            for combo in combos:
                                combo['strong'] = strong_algo.predict(draws)
                            logger.debug(
                                f"[FSM DEBUG] combos after strong assignment",
                                context={
                                    "main_version": main_version,
                                    "strong_version": strong_version,
                                    "combos_with_strong": str(combos)
                                }
                            )
                            prizes = []
                            dates = []
                            for i, test_draw in enumerate(test_draws):
                                combo_results = []
                                max_hits = 0
                                any_strong_hit = False
                                total_prize = 0
                                for combo in combos:
                                    hits = sum([n in test_draw.numbers for n in combo["numbers"]])
                                    strong_hit = (combo.get("strong") == getattr(test_draw, "strong_number", None))
                                    prize = calculate_prize(hits, strong_hit)
                                    combo_results.append({
                                        "numbers": combo["numbers"],
                                        "strong": combo.get("strong"),
                                        "hits": hits,
                                        "strong_hit": strong_hit,
                                        "prize": prize
                                    })
                                    if hits > max_hits:
                                        max_hits = hits
                                    if strong_hit:
                                        any_strong_hit = True
                                    total_prize += prize
                                    prizes.append(prize)
                                dates.append({
                                    "test_draw_date": test_draw.date,
                                    "actual_numbers": test_draw.numbers,
                                    "actual_strong": getattr(test_draw, "strong_number", None),
                                    "max_hits": max_hits,
                                    "any_strong_hit": any_strong_hit,
                                    "total_prize": total_prize,
                                    "combos": combo_results
                                })
                            total_prize = sum(prizes)
                            total_tickets = len(combos) * len(test_draws)
                            total_cost = total_tickets * TICKET_COST_PER_TABLE
                            roi = calculate_roi_with_tax(prizes, total_cost)
                            test_count = len(test_draws)
                            params = copy.deepcopy(algo_results[0]["params"]) if "params" in algo_results[0] else {}
                            logger.debug(
                                f"[FSM DEBUG] params extracted",
                                context={
                                    "main_version": main_version,
                                    "strong_version": strong_version,
                                    "params_extracted": params
                                }
                            )
                            if not params:
                                logger.error(
                                    f"[FSM ERROR] No params found in result!",
                                    context={
                                        "main_version": main_version,
                                        "strong_version": strong_version,
                                        "error_result": str(algo_results[0])
                                    }
                                )
                                raise ValueError(f"Arrr! No params found in result for {main_version} + {strong_version}! Praisin' the FSM for catchin' this! Result: {algo_results[0]}")
                            result = {
                                "params": params,
                                "roi": roi,
                                "total_prize": total_prize,
                                "total_cost": total_cost,
                                "test_count": test_count,
                                "combos": combos,
                                "dates": dates
                            }
                            result["strong_algo"] = getattr(strong_algo, 'version', None)
                            if not result["strong_algo"]:
                                logger.warning(
                                    f"[FSM DEBUG] Arrr! No strong_algo version found! Praisin' the FSM for catchin' this!",
                                    context={
                                        "main_version": main_version,
                                        "strong_version": strong_version
                                    }
                                )
                            algo_results = [result]
                        if not algo_results:
                            import traceback
                            trace = traceback.format_stack()
                            draw_info = [(getattr(d, 'date', None), getattr(d, 'numbers', None), getattr(d, 'strong_number', None)) for d in draws]
                            logger.error(
                                f"[FSM ERROR] No results returned!",
                                context={
                                    "main_version": main_version,
                                    "strong_version": strong_version,
                                    "params": run_kwargs,
                                    "draws": draw_info,
                                    "trace": ''.join(trace)
                                }
                            )
                            raise ValueError(f"Arrr! No results returned for {main_version} + {strong_version}! Params: {run_kwargs}\nDraws: {draw_info}")
                        for result in algo_results:
                            logger.debug(
                                f"[FSM DEBUG] Storing prediction",
                                context={
                                    "main_version": main_version,
                                    "strong_version": strong_version,
                                    "storing_prediction_result": result
                                }
                            )
                            prediction = Prediction(
                                model_id=get_or_create_model(session, main_version, getattr(algo, 'version', 'v1'), ModelType.main, result.get('params', {})).id,
                                strong_model_id=get_or_create_model(session, strong_version, getattr(strong_algo, 'version', 'v1'), ModelType.strong, {}).id,
                                roi=result['roi'],
                                total_prize=result['total_prize'],
                                total_cost=result['total_cost'],
                                test_count=result['test_count'],
                                notes=f"Sim run for {main_version} + {strong_version} | params: {result.get('params', {})}",
                                train_start_date=train_start,
                                train_end_date=train_end,
                                num_test_draws=test_count,
                                main_model_params=result.get('params', {}),
                                strong_model_params={"strong_algo": result.get('strong_algo')}
                            )
                            session.add(prediction)
                            session.flush()
                            for date_entry in result.get('dates', []):
                                for combo in date_entry['combos']:
                                    detail = PredictionDetail(
                                        prediction_id=prediction.id,
                                        test_draw_date=date_entry['test_draw_date'],
                                        actual_numbers=to_native(date_entry['actual_numbers']),
                                        actual_strong=to_native(date_entry['actual_strong']),
                                        predicted_numbers=to_native(combo['numbers']),
                                        predicted_strong=to_native(combo.get('strong')),
                                        hits=to_native(combo['hits']),
                                        strong_hit=to_native(combo['strong_hit']),
                                        prize=to_native(combo['prize']),
                                        roi=to_native((combo['prize'] - TICKET_COST_PER_TABLE) / TICKET_COST_PER_TABLE if TICKET_COST_PER_TABLE else 0)
                                    )
                                    session.add(detail)
                        session.commit()
                        best_result = max(algo_results, key=lambda x: x['roi'])
                        logger.debug(
                            f"[FSM DEBUG] Exiting run_algo_pair",
                            context={
                                "main_version": main_version,
                                "strong_version": strong_version,
                                "best_result": best_result
                            }
                        )
                        return (main_version, strong_version), {
                            "roi": best_result['roi'],
                            "total_prize": best_result['total_prize'],
                            "total_cost": best_result['total_cost'],
                            "params": best_result['params'],
                            "dates": best_result.get('dates', [])
                        }
                
                except (OperationalError, SQLAlchemyError) as e:
                    logger.error(
                        f"[FSM ERROR] Database error in run_algo_pair attempt {attempt + 1}",
                        context={
                            "main_version": main_version,
                            "strong_version": strong_version,
                            "error": str(e),
                            "attempt": attempt + 1
                        }
                    )
                    if attempt == 2:  # Last attempt
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                except Exception as e:
                    logger.error(
                        f"[FSM ERROR] Unexpected error in run_algo_pair",
                        context={
                            "main_version": main_version,
                            "strong_version": strong_version,
                            "error": str(e)
                        }
                    )
                    raise

        # Process algorithm pairs in parallel batches (4 concurrent to match CPU count)
        max_workers = min(4, len(list(algos_to_run)) * len(list(strong_algos_to_run)))
        logger.info(
            f"Arrr! Processing algorithm pairs with {max_workers} concurrent workers",
            context={
                "max_workers": max_workers,
                "total_pairs": len(list(algos_to_run)) * len(list(strong_algos_to_run))
            }
        )
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pair = {
                executor.submit(run_algo_pair, main_version, algo_cls, strong_version, strong_cls, test_count): (main_version, strong_version)
                for main_version, algo_cls in algos_to_run
                for strong_version, strong_cls in strong_algos_to_run
            }
            for future in as_completed(future_to_pair):
                pair, result = future.result()
                results[pair] = result

        logger.info(f"[FSM DEBUG] run_comparison finished in {time.time() - t_start:.2f}s")
        self._cache[cache_key] = results
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