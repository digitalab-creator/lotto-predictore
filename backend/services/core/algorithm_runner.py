"""
Algorithm runner for simulation engine.
Extracted from simulation_engine to reduce complexity.
Praisin' the FSM! 🍝⚓
"""
import time
import inspect
import copy
import traceback
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from models import Draw, Prediction, PredictionDetail, ModelType
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import TICKET_COST_PER_TABLE, NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND
from db.base import SessionLocal
from services.simulation_helpers.simulation_utils import calculate_roi_with_tax, to_native
from services.simulation_helpers.simulation_db import get_or_create_model
from services.simulation_helpers.simulation_prize import calculate_prize
from services.core.simulation_constants import (
    MAX_RETRY_ATTEMPTS,
    DEFAULT_BACKOFF_BASE,
    LSTM_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_SECONDS
)
from shared.logging_service import get_backend_logger

logger = get_backend_logger()


class AlgorithmRunner:
    """Handles running algorithm pairs with retry logic"""
    
    def __init__(self, draws: List[Draw], test_draws: List[Draw], top_n: int, use_cache: bool, train_start=None, train_end=None):
        self.draws = draws
        self.test_draws = test_draws
        self.top_n = top_n
        self.use_cache = use_cache
        self.train_start = train_start
        self.train_end = train_end
    
    def run_algo_pair(
        self, 
        main_version: str, 
        algo_cls: Any, 
        strong_version: str, 
        strong_cls: Any, 
        test_count: int
    ) -> Tuple[Tuple[str, str], Dict[str, Any]]:
        """Run an algorithm pair with retry logic and proper connection handling"""
        logger.debug(
            "[FSM DEBUG] Entering run_algo_pair with retry logic",
            context={
                "main_version": main_version,
                "strong_version": strong_version
            }
        )
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                with SessionLocal() as session:
                    t_algo = time.time()
                    algo = algo_cls()
                    strong_algo = strong_cls()
                    
                    # Set a longer timeout for LSTM models
                    if 'lstm' in main_version.lower():
                        session.execute(text(f"SET statement_timeout = '{LSTM_TIMEOUT_SECONDS}s'"))
                    
                    run_sig = inspect.signature(algo.run)
                    run_kwargs = dict(
                        draws=self.draws,
                        top_n=self.top_n,
                        num_for_analysis=NUM_COMBINATIONS_FOR_ANALYSIS,
                        num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND
                    )
                    
                    if 'db' in run_sig.parameters:
                        run_kwargs['db'] = session
                    if (hasattr(algo, 'version') and 
                        getattr(algo, 'version', None) == 'sequence_lstm_classifier_gridsearch' and 
                        'use_cache' in run_sig.parameters):
                        run_kwargs['use_cache'] = self.use_cache
                    
                    logger.debug(
                        "[FSM DEBUG] Running algorithm attempt",
                        context={
                            "main_version": main_version,
                            "strong_version": strong_version,
                            "attempt": attempt + 1
                        }
                    )
                    
                    algo_results = algo.run(**run_kwargs)
                    
                    # Reset timeout after LSTM models
                    if 'lstm' in main_version.lower():
                        session.execute(text(f"SET statement_timeout = '{DEFAULT_TIMEOUT_SECONDS}s'"))
                    
                    logger.debug(
                        "[FSM DEBUG] algo.run returned",
                        context={
                            "main_version": main_version,
                            "strong_version": strong_version,
                            "algo_results_raw": str(algo_results)
                        }
                    )
                    
                    if not isinstance(algo_results, list):
                        algo_results = [algo_results]
                    
                    if algo_results and isinstance(algo_results[0], dict) and 'numbers' in algo_results[0]:
                        result = self._process_algorithm_results(
                            algo_results, strong_algo, main_version, strong_version,
                            session, test_count
                        )
                        algo_results = [result]
                    
                    if not algo_results:
                        draw_info = [
                            (getattr(d, 'date', None), getattr(d, 'numbers', None), 
                             getattr(d, 'strong_number', None)) for d in self.draws
                        ]
                        logger.error(
                            "[FSM ERROR] No results returned!",
                            context={
                                "main_version": main_version,
                                "strong_version": strong_version,
                                "params": run_kwargs,
                                "draws": draw_info,
                                "trace": ''.join(traceback.format_stack())
                            }
                        )
                        raise ValueError(
                            f"Arrr! No results returned for {main_version} + {strong_version}! "
                            f"Params: {run_kwargs}\nDraws: {draw_info}"
                        )
                    
                    self._store_predictions(
                        algo_results, main_version, strong_version, session, test_count,
                        self.train_start, self.train_end
                    )
                    session.commit()
                    
                    best_result = max(algo_results, key=lambda x: x['roi'])
                    logger.debug(
                        "[FSM DEBUG] Exiting run_algo_pair",
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
                    "[FSM ERROR] Database error in run_algo_pair attempt",
                    context={
                        "main_version": main_version,
                        "strong_version": strong_version,
                        "error": str(e),
                        "attempt": attempt + 1
                    }
                )
                if attempt == MAX_RETRY_ATTEMPTS - 1:  # Last attempt
                    raise
                time.sleep(DEFAULT_BACKOFF_BASE ** attempt)  # Exponential backoff
                continue
            except Exception as e:
                logger.error(
                    "[FSM ERROR] Unexpected error in run_algo_pair",
                    context={
                        "main_version": main_version,
                        "strong_version": strong_version,
                        "error": str(e)
                    }
                )
                raise
    
    def _process_algorithm_results(
        self, 
        algo_results: List[Dict], 
        strong_algo: Any, 
        main_version: str, 
        strong_version: str,
        session: Session,
        test_count: int
    ) -> Dict[str, Any]:
        """Process algorithm results and calculate prizes"""
        combos = algo_results
        for combo in combos:
            combo['strong'] = strong_algo.predict(self.draws)
        
        logger.debug(
            "[FSM DEBUG] combos after strong assignment",
            context={
                "main_version": main_version,
                "strong_version": strong_version,
                "combos_with_strong": str(combos)
            }
        )
        
        prizes = []
        dates = []
        for test_draw in self.test_draws:
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
        total_tickets = len(combos) * len(self.test_draws)
        total_cost = total_tickets * TICKET_COST_PER_TABLE
        roi = calculate_roi_with_tax(prizes, total_cost)
        test_count = len(self.test_draws)
        
        params = copy.deepcopy(algo_results[0]["params"]) if "params" in algo_results[0] else {}
        logger.debug(
            "[FSM DEBUG] params extracted",
            context={
                "main_version": main_version,
                "strong_version": strong_version,
                "params_extracted": params
            }
        )
        
        if not params:
            logger.error(
                "[FSM ERROR] No params found in result!",
                context={
                    "main_version": main_version,
                    "strong_version": strong_version,
                    "error_result": str(algo_results[0])
                }
            )
            raise ValueError(
                f"Arrr! No params found in result for {main_version} + {strong_version}! "
                f"Praisin' the FSM for catchin' this! Result: {algo_results[0]}"
            )
        
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
                "[FSM DEBUG] Arrr! No strong_algo version found! Praisin' the FSM for catchin' this!",
                context={
                    "main_version": main_version,
                    "strong_version": strong_version
                }
            )
        
        return result
    
    def _store_predictions(
        self, 
        algo_results: List[Dict], 
        main_version: str, 
        strong_version: str,
        session: Session,
        test_count: int,
        train_start=None,
        train_end=None
    ) -> None:
        """Store predictions in database"""
        for result in algo_results:
            logger.debug(
                "[FSM DEBUG] Storing prediction",
                context={
                    "main_version": main_version,
                    "strong_version": strong_version,
                    "storing_prediction_result": result
                }
            )
            
            # Get algorithm instances to extract version
            algo = ALGORITHM_REGISTRY[main_version]()
            strong_algo = STRONG_NUMBER_REGISTRY[strong_version]()
            
            prediction = Prediction(
                model_id=get_or_create_model(
                    session, main_version, getattr(algo, 'version', 'v1'), 
                    ModelType.main, result.get('params', {})
                ).id,
                strong_model_id=get_or_create_model(
                    session, strong_version, getattr(strong_algo, 'version', 'v1'), 
                    ModelType.strong, {}
                ).id,
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
                        roi=to_native(
                            (combo['prize'] - TICKET_COST_PER_TABLE) / TICKET_COST_PER_TABLE 
                            if TICKET_COST_PER_TABLE else 0
                        )
                    )
                    session.add(detail)

