from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from services.core.cron_tracker import CronTracker
from services.core.simulation_engine import SimulationEngine
from models import Prediction
from config import NUM_COMBINATIONS_TO_RECOMMEND
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from logger import logger
from ..utils import get_balanced_algorithm_list
from .base_combination_generator import (
    get_db_session, load_draws_with_filter, generate_combinations,
    validate_combos_result, get_model_objects, store_combinations_in_db,
    send_weekly_combinations_email
)
from services.queue.job_queue import enqueue_job
import time
import uuid

router = APIRouter()


@router.post("/cron/generate-weekly-combinations")
async def generate_weekly_combinations(sync: bool = Query(False, description="Run synchronously (for fallback)")):
    """
    Generate weekly combinations - called by cron service.
    By default, enqueues job to background worker. Use ?sync=true for synchronous execution.
    """
    # If sync mode, run the old synchronous logic
    if sync:
        return await _generate_weekly_combinations_sync()
    
    # Otherwise, enqueue to background worker
    try:
        # Use string-based function reference to avoid circular import
        job_id = f"weekly-combinations-{uuid.uuid4().hex[:8]}"
        job = enqueue_job(
            None,  # func not needed when using func_name
            job_id=job_id,
            job_timeout=600,  # 10 minutes
            func_name="services.queue.workers.generate_weekly_combinations_task"
        )
        
        logger.info(
            "Arrr! Weekly combinations job enqueued!",
            context={"job_id": job.id, "execution_mode": "background"}
        )
        
        return {
            "success": True,
            "data": {
                "status": "queued",
                "job_id": job.id,
                "message": "Job enqueued successfully. Use /api/jobs/{job_id}/status to check progress.",
                "status_url": f"/api/jobs/{job.id}/status"
            }
        }
    except Exception as e:
        logger.error(
            "Arrr! Failed to enqueue job!",
            context={"error": str(e)}
        )
        # Fallback to synchronous execution on error
        logger.warning("Arrr! Falling back to synchronous execution!")
        return await _generate_weekly_combinations_sync()


async def _generate_weekly_combinations_sync():
    """Synchronous version of weekly combination generation (fallback)"""
    start_time = time.time()
    logger.info("Arrr! Starting weekly combination generation (sync mode), praisin' the FSM!", context={"start_time": start_time})
    
    # Initialize cron tracking
    db = get_db_session()
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
            draws, filtered_count, draws_time = load_draws_with_filter(db)
            
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
            
            unique_combinations = []
            
            if not balanced_algorithms:
                logger.info("Arrr! All models have sufficient prediction details, running all algorithms")
                # If all models are balanced, create combinations of top algorithms with all strong algorithms
                all_algorithms = [algo for algo in ALGORITHM_REGISTRY.keys() 
                                if 'gridsearch' not in algo.lower()]
                
                # Take top 10 main algorithms and create combinations with all strong algorithms
                top_main_algorithms = all_algorithms[:10]
                all_strong_algorithms = list(STRONG_NUMBER_REGISTRY.keys())
                
                # Create combinations: each main algo with each strong algo
                seen_combinations = set()
                for main_algo in top_main_algorithms:
                    for strong_algo in all_strong_algorithms:
                        combination_key = f"{main_algo}_{strong_algo}"
                        if combination_key not in seen_combinations:
                            unique_combinations.append({
                                'main_algo': main_algo,
                                'strong_algo': strong_algo,
                                'current_details': 0,  # All balanced, so assume 0 needed
                                'priority_score': 0
                            })
                            seen_combinations.add(combination_key)
                
                total_algorithms = len(unique_combinations)
                
                logger.info(
                    "Arrr! Created algorithm combinations from top main algorithms with all strong algorithms",
                    context={
                        "total_main_algorithms": len(all_algorithms),
                        "top_main_algorithms_selected": len(top_main_algorithms),
                        "total_strong_algorithms": len(all_strong_algorithms),
                        "total_combinations_created": total_algorithms,
                        "sample_combinations": [f"{c['main_algo']}+{c['strong_algo']}" for c in unique_combinations[:5]]
                    }
                )
            else:
                # Use the top algorithms that need more data (excluding grid search)
                top_algorithms = [combo for combo in balanced_algorithms[:10] 
                                if 'gridsearch' not in combo['main_algo'].lower()]
                # Keep all unique main+strong combinations
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
            main_algo_name, strong_algo_name = best_pair
            combos, strong_number, generation_time = generate_combinations(
                db=db,
                main_algo_name=main_algo_name,
                strong_algo_name=strong_algo_name,
                draws=draws,
                top_n=3,
                num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND,
                version="weekly_generation",
                cron_job=cron_job,
                start_time=start_time
            )
            
            # Validate algorithm result
            error_msg = validate_combos_result(combos, main_algo_name, "weekly_generation", cron_job, start_time)
            if error_msg:
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
            main_model, strong_model = get_model_objects(db, main_algo_name, strong_algo_name)
            
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
            valid_combos_processed = store_combinations_in_db(
                db=db,
                combos=combos,
                strong_number=strong_number,
                prediction_id=new_prediction.id,
                version="weekly_generation",
                now=now
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
            
            # Send email with the generated combinations (non-blocking - log errors but don't fail the job)
            email_sent, email_error = send_weekly_combinations_email(
                db=db,
                prediction_id=new_prediction.id,
                prediction=new_prediction,
                main_model=main_model,
                strong_model=strong_model,
                version="weekly_generation"
            )
            
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
                    "email_sent": email_sent,
                    "email_error": email_error,
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
                "total_time": f"{total_time:.2f}s",
                "email_sent": email_sent,
                "email_error": email_error
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

