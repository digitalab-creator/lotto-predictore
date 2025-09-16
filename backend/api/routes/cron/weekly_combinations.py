from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import datetime
from services.cron_tracker import CronTracker
from services.simulation_engine import SimulationEngine
from services.grid_search_service import WeeklyCombinationsGridSearch
from models import Draw, Prediction, Model, GeneratedCombination
from config import NUM_COMBINATIONS_TO_RECOMMEND
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from utils.model_utils import normalize_model_name, denormalize_model_name
from logger import logger
from .utils import get_balanced_algorithm_list
import time

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/cron/generate-weekly-combinations-fast")
async def generate_weekly_combinations_fast():
    """Generate weekly combinations FAST - for debugging (only runs 2 algorithms)"""
    start_time = time.time()
    logger.info("Arrr! Starting FAST weekly combination generation for debugging, praisin' the FSM!", context={"start_time": start_time})
    
    # Initialize cron tracking
    db = next(get_db())
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="generate-weekly-combinations-fast",
            job_type="debug",
            metadata={"start_time": start_time}
        )
        
        # Use the same logic as the /generate-combinations endpoint but with limited algorithms
        
        try:
            # Get all draws, filtering out strong_number == 8
            draws_start = time.time()
            draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
            filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
            draws_time = time.time() - draws_start
            
            logger.info(
                "Arrr! Filtered out draws with strong_number == 8 for FAST weekly generation, praisin' the FSM!",
                context={
                    "filtered_count": filtered_count, 
                    "total_after_filter": len(draws),
                    "draws_load_time": f"{draws_time:.2f}s"
                }
            )
            
            if len(draws) < 20:
                error_msg = "Not enough draws in database for recommendation."
                logger.error(error_msg)
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            # Use last 12 draws as test set, rest as training
            train_draws = draws[:-12]
            test_draws = draws[-12:]
            train_start = train_draws[0].date
            train_end = train_draws[-1].date
            test_count = 12
            
            # FAST MODE: Only test 2 specific algorithm combinations
            fast_combinations = [
                {"main_algo": "most_common", "strong_algo": "random"},
                {"main_algo": "random_from_top15_pool", "strong_algo": "most_common"}
            ]
            
            logger.info(
                "Arrr! FAST MODE: Testing only 2 algorithm combinations",
                context={
                    "fast_combinations": fast_combinations,
                    "total_combinations": len(fast_combinations)
                }
            )
            
            # Find best algorithm pair by ROI using SimulationEngine
            engine_start = time.time()
            engine = SimulationEngine(db)
            results = {}
            best_pair = None
            best_roi = float('-inf')
            
            logger.info(
                f"Arrr! Starting FAST algorithm evaluation for {len(fast_combinations)} algorithms",
                context={
                    "total_algorithms": len(fast_combinations),
                    "algorithms": [combo['main_algo'] for combo in fast_combinations]
                }
            )
            
            for idx, combo in enumerate(fast_combinations, 1):
                combo_start = time.time()
                
                logger.info(
                    f"Arrr! Running FAST algorithm {idx}/{len(fast_combinations)}: {combo['main_algo']} + {combo['strong_algo']}",
                    context={
                        "algorithm": f"{combo['main_algo']} + {combo['strong_algo']}",
                        "progress": f"{idx}/{len(fast_combinations)}",
                        "elapsed_time": f"{time.time() - start_time:.2f}s"
                    }
                )
                
                try:
                    res = engine.run_comparison(train_start, train_end, test_count, 3, algo_names=[combo['main_algo']], strong_algo_names=[combo['strong_algo']])
                    for (main_algo, strong_algo), r in res.items():
                        results[(main_algo, strong_algo)] = r
                        if r["roi"] > best_roi:
                            best_pair = (main_algo, strong_algo)
                            best_roi = r["roi"]
                            
                    combo_time = time.time() - combo_start
                    logger.info(
                        f"Arrr! Completed FAST algorithm {combo['main_algo']} + {combo['strong_algo']}",
                        context={
                            "algorithm": f"{combo['main_algo']} + {combo['strong_algo']}",
                            "algorithm_time": f"{combo_time:.2f}s",
                            "best_roi_so_far": best_roi,
                            "total_elapsed": f"{time.time() - start_time:.2f}s"
                        }
                    )
                    
                except Exception as e:
                    combo_time = time.time() - combo_start
                    logger.error(
                        f"Arrr! Skipping FAST {combo['main_algo']} + {combo['strong_algo']} due to error",
                        context={
                            "algorithm": f"{combo['main_algo']} + {combo['strong_algo']}",
                            "error": str(e),
                            "algorithm_time": f"{combo_time:.2f}s"
                        }
                    )
                    continue
            
            engine_time = time.time() - engine_start
            logger.info(
                f"Arrr! Completed FAST algorithm evaluation",
                context={
                    "total_engine_time": f"{engine_time:.2f}s",
                    "best_pair": best_pair,
                    "best_roi": best_roi,
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            
            if not best_pair:
                error_msg = "No algorithm produced results."
                logger.error(error_msg)
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            # Generate final combinations
            generation_start = time.time()
            main_algo_name, strong_algo_name = best_pair
            main_algo_cls = ALGORITHM_REGISTRY[main_algo_name]
            strong_algo_cls = STRONG_NUMBER_REGISTRY[strong_algo_name]
            
            # Generate combinations using all draws
            all_draws = draws
            combos = main_algo_cls().run(all_draws, top_n=3, num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND)
            strong_algo = strong_algo_cls()
            strong_number = strong_algo.predict(all_draws)
            
            # Validate algorithm result
            if not isinstance(combos, list):
                error_msg = f"Algorithm {main_algo_name} returned invalid result type: {type(combos)}"
                logger.error(
                    "Arrr! Algorithm returned invalid result type!",
                    context={
                        "algorithm": main_algo_name,
                        "result_type": type(combos),
                        "result_value": str(combos)[:200],
                        "total_elapsed": f"{time.time() - start_time:.2f}s"
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            if not combos:
                error_msg = f"Algorithm {main_algo_name} returned empty result"
                logger.error(
                    "Arrr! Algorithm returned empty result!",
                    context={
                        "algorithm": main_algo_name,
                        "total_elapsed": f"{time.time() - start_time:.2f}s"
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            logger.info(
                f"Arrr! Algorithm {main_algo_name} returned {len(combos)} combinations",
                context={
                    "algorithm": main_algo_name,
                    "num_combinations": len(combos),
                    "first_combo_keys": list(combos[0].keys()) if combos and isinstance(combos[0], dict) else "N/A",
                    "first_combo_type": type(combos[0]) if combos else "N/A",
                    "first_combo_sample": str(combos[0])[:200] if combos else "N/A"
                }
            )
            
            generation_time = time.time() - generation_start
            logger.info(
                f"Arrr! Generated final combinations",
                context={
                    "generation_time": f"{generation_time:.2f}s",
                    "num_combinations": len(combos),
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            
            now = datetime.utcnow()
            
            # Create a new Prediction row for this generation event
            db_start = time.time()
            
            # Get model IDs with proper error handling
            main_model = db.query(Model).filter(Model.name == denormalize_model_name(normalize_model_name(main_algo_name), 'main')).first()
            strong_model = db.query(Model).filter(Model.name == denormalize_model_name(normalize_model_name(strong_algo_name), 'strong')).first()
            
            if not main_model:
                error_msg = f"Main model '{main_algo_name}' not found in database"
                logger.error(
                    "Arrr! Main model not found in database!",
                    context={"main_algo_name": main_algo_name, "total_elapsed": f"{time.time() - start_time:.2f}s"}
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            if not strong_model:
                error_msg = f"Strong model '{strong_algo_name}' not found in database"
                logger.error(
                    "Arrr! Strong model not found in database!",
                    context={"strong_algo_name": strong_algo_name, "total_elapsed": f"{time.time() - start_time:.2f}s"}
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            new_prediction = Prediction(
                model_id=main_model.id,
                strong_model_id=strong_model.id,
                run_time=now,
                roi=best_roi,
                total_prize=results[best_pair]["total_prize"],
                total_cost=results[best_pair]["total_cost"],
                test_count=test_count,
                notes=f"FAST Weekly combination generation at {now.isoformat()} | Best ROI: {best_roi:.4f}",
                train_start_date=train_start,
                train_end_date=train_end,
                num_test_draws=test_count,
                main_model_params={"top_n": 3, "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND},
                strong_model_params={"strong_algo": strong_algo_name}
            )
            db.add(new_prediction)
            db.flush()  # Get the new prediction.id
            
            # Store each combo in DB
            valid_combos_processed = 0
            for idx, combo in enumerate(combos):
                # Validate combo format and extract numbers safely
                if not isinstance(combo, dict):
                    logger.error(
                        f"Arrr! Invalid combo format at index {idx}: not a dict",
                        context={
                            "combo_type": type(combo),
                            "combo_value": str(combo)[:100],
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                # Try to extract numbers from different possible formats
                numbers = None
                if "numbers" in combo:
                    numbers = combo["numbers"]
                elif "strong" in combo and isinstance(combo.get("strong"), (list, tuple)):
                    # Some algorithms might put numbers in "strong" field
                    numbers = combo["strong"]
                else:
                    logger.error(
                        f"Arrr! Combo at index {idx} missing 'numbers' key",
                        context={
                            "combo_keys": list(combo.keys()),
                            "combo_value": str(combo)[:100],
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                # Validate numbers format
                if not isinstance(numbers, (list, tuple)) or len(numbers) != 6:
                    logger.error(
                        f"Arrr! Invalid numbers format at index {idx}",
                        context={
                            "numbers_type": type(numbers),
                            "numbers_value": numbers,
                            "numbers_length": len(numbers) if isinstance(numbers, (list, tuple)) else "N/A",
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                # Ensure all numbers are integers
                try:
                    numbers = [int(n) for n in numbers]
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Arrr! Error converting numbers to int at index {idx}",
                        context={
                            "error": str(e),
                            "numbers": numbers,
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                generated = GeneratedCombination(
                    prediction_id=new_prediction.id,
                    numbers=numbers,
                    strong_number=strong_number,
                    position=valid_combos_processed+1,
                    version="fast_weekly_generation",  # Set version for tracking
                    generated_at=now
                )
                db.add(generated)
                valid_combos_processed += 1
                
                logger.info(
                    f"Stored FAST combo {valid_combos_processed}: {numbers} + {strong_number}",
                    context={
                        "prediction_id": new_prediction.id,
                        "numbers": numbers,
                        "strong_number": strong_number,
                        "position": valid_combos_processed
                    }
                )
            
            # Check if we processed any valid combos
            if valid_combos_processed == 0:
                error_msg = f"No valid combinations found from algorithm {main_algo_name}"
                logger.error(
                    "Arrr! No valid combinations processed!",
                    context={
                        "algorithm": main_algo_name,
                        "total_combos_received": len(combos),
                        "valid_combos_processed": valid_combos_processed,
                        "total_elapsed": f"{time.time() - start_time:.2f}s"
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            logger.info(
                f"Arrr! Successfully processed {valid_combos_processed} valid combinations out of {len(combos)} received",
                context={
                    "algorithm": main_algo_name,
                    "total_combos_received": len(combos),
                    "valid_combos_processed": valid_combos_processed,
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            
            db.commit()
            db_time = time.time() - db_start
            
            total_time = time.time() - start_time
            
            # Mark job as completed
            if cron_job:
                tracker.complete_job(cron_job, total_time)
            
            logger.info(
                f"Arrr! Generated {valid_combos_processed} FAST weekly combinations using {main_algo_name} + {strong_algo_name}",
                context={
                    "main_algo": main_algo_name,
                    "strong_algo": strong_algo_name,
                    "best_roi": best_roi,
                    "num_combinations": valid_combos_processed,
                    "prediction_id": new_prediction.id,
                    "total_time": f"{total_time:.2f}s",
                    "breakdown": {
                        "draws_load": f"{draws_time:.2f}s",
                        "engine_evaluation": f"{engine_time:.2f}s",
                        "generation": f"{generation_time:.2f}s",
                        "database": f"{db_time:.2f}s"
                    }
                }
            )
            
            return {
                "status": "success", 
                "message": f"FAST Weekly combinations generated successfully using {main_algo_name} + {strong_algo_name}",
                "num_combinations": valid_combos_processed,
                "prediction_id": new_prediction.id,
                "total_time": f"{total_time:.2f}s"
            }
            
        except Exception as e:
            error_msg = f"Error in FAST weekly combination generation: {str(e)}"
            logger.error(
                "Arrr! Error in FAST weekly combination generation!",
                context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
            )
            if cron_job:
                tracker.fail_job(cron_job, error_msg, time.time() - start_time)
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Error in FAST weekly combination generation endpoint: {str(e)}"
        logger.error(
            "Arrr! Error in FAST weekly combination generation endpoint!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron/generate-weekly-combinations")
async def generate_weekly_combinations():
    """Generate weekly combinations - called by cron service"""
    start_time = time.time()
    logger.info("Arrr! Starting weekly combination generation, praisin' the FSM!", context={"start_time": start_time})
    
    # Initialize cron tracking
    db = next(get_db())
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="generate-weekly-combinations",
            job_type="scheduled",
            metadata={"start_time": start_time}
        )
        
        # Use the same logic as the /generate-combinations endpoint
        
        try:
            # Get all draws, filtering out strong_number == 8
            draws_start = time.time()
            draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
            filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
            draws_time = time.time() - draws_start
            
            logger.info(
                "Arrr! Filtered out draws with strong_number == 8 for weekly generation, praisin' the FSM!",
                context={
                    "filtered_count": filtered_count, 
                    "total_after_filter": len(draws),
                    "draws_load_time": f"{draws_time:.2f}s"
                }
            )
            
            if len(draws) < 20:
                error_msg = "Not enough draws in database for recommendation."
                logger.error(error_msg)
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            # Use last 12 draws as test set, rest as training
            train_draws = draws[:-12]
            test_draws = draws[-12:]
            train_start = train_draws[0].date
            train_end = train_draws[-1].date
            test_count = 12
            
            # Get balanced algorithm list based on current prediction details
            balanced_algorithms = get_balanced_algorithm_list(db, target_details_per_model=1000)
            
            logger.info(
                "Arrr! Retrieved balanced algorithms list",
                context={
                    "balanced_algorithms_count": len(balanced_algorithms) if balanced_algorithms else 0,
                    "balanced_algorithms": balanced_algorithms[:3] if balanced_algorithms else None  # Show first 3 for debugging
                }
            )
            
            if not balanced_algorithms:
                logger.info("Arrr! All models have sufficient prediction details, running all algorithms")
                # If all models are balanced, run all algorithms (excluding grid search)
                all_algorithms = [algo for algo in ALGORITHM_REGISTRY.keys() 
                                if 'gridsearch' not in algo.lower()]
                total_algorithms = len(all_algorithms)
                
                logger.info(
                    "Arrr! Filtered out grid search algorithms from weekly evaluation",
                    context={
                        "total_algorithms_after_filter": total_algorithms,
                        "filtered_algorithms": all_algorithms[:5]  # Show first 5 for debugging
                    }
                )
            else:
                # Use the top algorithms that need more data (excluding grid search)
                top_algorithms = [combo for combo in balanced_algorithms[:10] 
                                if 'gridsearch' not in combo['main_algo'].lower()]
                # Keep all unique main+strong combinations
                unique_combinations = []
                seen_combinations = set()
                
                for combo in top_algorithms:
                    combination_key = f"{combo['main_algo']}_{combo['strong_algo']}"
                    if combination_key not in seen_combinations:
                        unique_combinations.append(combo)
                        seen_combinations.add(combination_key)
                
                total_algorithms = len(unique_combinations)
                
                logger.info(
                    f"Arrr! Selected {total_algorithms} unique main+strong combinations based on prediction details balance",
                    context={
                        "selected_combinations": [{"main": combo['main_algo'], "strong": combo['strong_algo'], "current_details": combo['current_details'], "priority": combo['priority_score']} for combo in unique_combinations[:5]],
                        "total_combinations": total_algorithms
                    }
                )
            
            # Find best algorithm pair by ROI using SimulationEngine
            engine_start = time.time()
            engine = SimulationEngine(db)
            results = {}
            best_pair = None
            best_roi = float('-inf')
            
            logger.info(
                f"Arrr! Starting algorithm evaluation for {total_algorithms} algorithms",
                context={
                    "total_algorithms": total_algorithms,
                    "algorithms": [combo['main_algo'] for combo in unique_combinations]
                }
            )
            
            for idx, combo in enumerate(unique_combinations, 1):
                combo_start = time.time()
                
                logger.info(
                    f"Arrr! Running algorithm {idx}/{total_algorithms}: {combo['main_algo']} + {combo['strong_algo']}",
                    context={
                        "algorithm": f"{combo['main_algo']} + {combo['strong_algo']}",
                        "progress": f"{idx}/{total_algorithms}",
                        "elapsed_time": f"{time.time() - start_time:.2f}s"
                    }
                )
                
                try:
                    res = engine.run_comparison(train_start, train_end, test_count, 3, algo_names=[combo['main_algo']], strong_algo_names=[combo['strong_algo']])
                    for (main_algo, strong_algo), r in res.items():
                        results[(main_algo, strong_algo)] = r
                        if r["roi"] > best_roi:
                            best_pair = (main_algo, strong_algo)
                            best_roi = r["roi"]
                            
                    combo_time = time.time() - combo_start
                    logger.info(
                        f"Arrr! Completed algorithm {combo['main_algo']} + {combo['strong_algo']}",
                        context={
                            "algorithm": f"{combo['main_algo']} + {combo['strong_algo']}",
                            "algorithm_time": f"{combo_time:.2f}s",
                            "best_roi_so_far": best_roi,
                            "total_elapsed": f"{time.time() - start_time:.2f}s"
                        }
                    )
                    
                except Exception as e:
                    combo_time = time.time() - combo_start
                    logger.error(
                        f"Arrr! Skipping {combo['main_algo']} + {combo['strong_algo']} due to error",
                        context={
                            "algorithm": f"{combo['main_algo']} + {combo['strong_algo']}",
                            "error": str(e),
                            "algorithm_time": f"{combo_time:.2f}s"
                        }
                    )
                    continue
            
            engine_time = time.time() - engine_start
            logger.info(
                f"Arrr! Completed algorithm evaluation",
                context={
                    "total_engine_time": f"{engine_time:.2f}s",
                    "best_pair": best_pair,
                    "best_roi": best_roi,
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            
            if not best_pair:
                error_msg = "No algorithm produced results."
                logger.error(error_msg)
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            # Generate final combinations
            generation_start = time.time()
            main_algo_name, strong_algo_name = best_pair
            main_algo_cls = ALGORITHM_REGISTRY[main_algo_name]
            strong_algo_cls = STRONG_NUMBER_REGISTRY[strong_algo_name]
            
            # Generate combinations using all draws
            all_draws = draws
            combos = main_algo_cls().run(all_draws, top_n=3, num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND)
            strong_algo = strong_algo_cls()
            strong_number = strong_algo.predict(all_draws)
            
            # Validate algorithm result
            if not isinstance(combos, list):
                error_msg = f"Algorithm {main_algo_name} returned invalid result type: {type(combos)}"
                logger.error(
                    "Arrr! Algorithm returned invalid result type!",
                    context={
                        "algorithm": main_algo_name,
                        "result_type": type(combos),
                        "result_value": str(combos)[:200],
                        "total_elapsed": f"{time.time() - start_time:.2f}s"
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            if not combos:
                error_msg = f"Algorithm {main_algo_name} returned empty result"
                logger.error(
                    "Arrr! Algorithm returned empty result!",
                    context={
                        "algorithm": main_algo_name,
                        "total_elapsed": f"{time.time() - start_time:.2f}s"
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            logger.info(
                f"Arrr! Algorithm {main_algo_name} returned {len(combos)} combinations",
                context={
                    "algorithm": main_algo_name,
                    "num_combinations": len(combos),
                    "first_combo_keys": list(combos[0].keys()) if combos and isinstance(combos[0], dict) else "N/A",
                    "first_combo_type": type(combos[0]) if combos else "N/A",
                    "first_combo_sample": str(combos[0])[:200] if combos else "N/A"
                }
            )
            
            generation_time = time.time() - generation_start
            logger.info(
                f"Arrr! Generated final combinations",
                context={
                    "generation_time": f"{generation_time:.2f}s",
                    "num_combinations": len(combos),
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            
            now = datetime.utcnow()
            
            # Create a new Prediction row for this generation event
            db_start = time.time()
            
            # Get model IDs with proper error handling
            main_model = db.query(Model).filter(Model.name == denormalize_model_name(normalize_model_name(main_algo_name), 'main')).first()
            strong_model = db.query(Model).filter(Model.name == denormalize_model_name(normalize_model_name(strong_algo_name), 'strong')).first()
            
            if not main_model:
                error_msg = f"Main model '{main_algo_name}' not found in database"
                logger.error(
                    "Arrr! Main model not found in database!",
                    context={"main_algo_name": main_algo_name, "total_elapsed": f"{time.time() - start_time:.2f}s"}
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            if not strong_model:
                error_msg = f"Strong model '{strong_algo_name}' not found in database"
                logger.error(
                    "Arrr! Strong model not found in database!",
                    context={"strong_algo_name": strong_algo_name, "total_elapsed": f"{time.time() - start_time:.2f}s"}
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            new_prediction = Prediction(
                model_id=main_model.id,
                strong_model_id=strong_model.id,
                run_time=now,
                roi=best_roi,
                total_prize=results[best_pair]["total_prize"],
                total_cost=results[best_pair]["total_cost"],
                test_count=test_count,
                notes=f"Weekly combination generation at {now.isoformat()} | Best ROI: {best_roi:.4f}",
                train_start_date=train_start,
                train_end_date=train_end,
                num_test_draws=test_count,
                main_model_params={"top_n": 3, "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND},
                strong_model_params={"strong_algo": strong_algo_name}
            )
            db.add(new_prediction)
            db.flush()  # Get the new prediction.id
            
            # Store each combo in DB
            valid_combos_processed = 0
            for idx, combo in enumerate(combos):
                # Validate combo format and extract numbers safely
                if not isinstance(combo, dict):
                    logger.error(
                        f"Arrr! Invalid combo format at index {idx}: not a dict",
                        context={
                            "combo_type": type(combo),
                            "combo_value": str(combo)[:100],
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                # Try to extract numbers from different possible formats
                numbers = None
                if "numbers" in combo:
                    numbers = combo["numbers"]
                elif "strong" in combo and isinstance(combo.get("strong"), (list, tuple)):
                    # Some algorithms might put numbers in "strong" field
                    numbers = combo["strong"]
                else:
                    logger.error(
                        f"Arrr! Combo at index {idx} missing 'numbers' key",
                        context={
                            "combo_keys": list(combo.keys()),
                            "combo_value": str(combo)[:100],
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                # Validate numbers format
                if not isinstance(numbers, (list, tuple)) or len(numbers) != 6:
                    logger.error(
                        f"Arrr! Invalid numbers format at index {idx}",
                        context={
                            "numbers_type": type(numbers),
                            "numbers_value": numbers,
                            "numbers_length": len(numbers) if isinstance(numbers, (list, tuple)) else "N/A",
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                # Ensure all numbers are integers
                try:
                    numbers = [int(n) for n in numbers]
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Arrr! Error converting numbers to int at index {idx}",
                        context={
                            "error": str(e),
                            "numbers": numbers,
                            "prediction_id": new_prediction.id
                        }
                    )
                    continue
                
                generated = GeneratedCombination(
                    prediction_id=new_prediction.id,
                    numbers=numbers,
                    strong_number=strong_number,
                    position=valid_combos_processed+1,
                    version="weekly_generation",  # Set version for tracking
                    generated_at=now
                )
                db.add(generated)
                valid_combos_processed += 1
                
                logger.info(
                    f"Stored combo {valid_combos_processed}: {numbers} + {strong_number}",
                    context={
                        "prediction_id": new_prediction.id,
                        "numbers": numbers,
                        "strong_number": strong_number,
                        "position": valid_combos_processed
                    }
                )
            
            # Check if we processed any valid combos
            if valid_combos_processed == 0:
                error_msg = f"No valid combinations found from algorithm {main_algo_name}"
                logger.error(
                    "Arrr! No valid combinations processed!",
                    context={
                        "algorithm": main_algo_name,
                        "total_combos_received": len(combos),
                        "valid_combos_processed": valid_combos_processed,
                        "total_elapsed": f"{time.time() - start_time:.2f}s"
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            logger.info(
                f"Arrr! Successfully processed {valid_combos_processed} valid combinations out of {len(combos)} received",
                context={
                    "algorithm": main_algo_name,
                    "total_combos_received": len(combos),
                    "valid_combos_processed": valid_combos_processed,
                    "total_elapsed": f"{time.time() - start_time:.2f}s"
                }
            )
            
            db.commit()
            db_time = time.time() - db_start
            
            total_time = time.time() - start_time
            
            # Mark job as completed
            if cron_job:
                tracker.complete_job(cron_job, total_time)
            
            logger.info(
                f"Arrr! Generated {valid_combos_processed} weekly combinations using {main_algo_name} + {strong_algo_name}",
                context={
                    "main_algo": main_algo_name,
                    "strong_algo": strong_algo_name,
                    "best_roi": best_roi,
                    "num_combinations": valid_combos_processed,
                    "prediction_id": new_prediction.id,
                    "total_time": f"{total_time:.2f}s",
                    "breakdown": {
                        "draws_load": f"{draws_time:.2f}s",
                        "engine_evaluation": f"{engine_time:.2f}s",
                        "generation": f"{generation_time:.2f}s",
                        "database": f"{db_time:.2f}s"
                    }
                }
            )
            
            return {
                "status": "success", 
                "message": f"Weekly combinations generated successfully using {main_algo_name} + {strong_algo_name}",
                "num_combinations": valid_combos_processed,
                "prediction_id": new_prediction.id,
                "total_time": f"{total_time:.2f}s"
            }
            
        except Exception as e:
            error_msg = f"Error in weekly combination generation: {str(e)}"
            logger.error(
                "Arrr! Error in weekly combination generation!",
                context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
            )
            if cron_job:
                tracker.fail_job(cron_job, error_msg, time.time() - start_time)
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Error in weekly combination generation endpoint: {str(e)}"
        logger.error(
            "Arrr! Error in weekly combination generation endpoint!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e)) 