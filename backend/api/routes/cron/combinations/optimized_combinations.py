from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from services.core.cron_tracker import CronTracker
from services.core.grid_search_service import WeeklyCombinationsGridSearch
from models import Prediction
from config import NUM_COMBINATIONS_TO_RECOMMEND
from logger import logger
from .base_combination_generator import (
    get_db_session, load_draws_with_filter, generate_combinations,
    validate_combos_result, get_model_objects, store_combinations_in_db
)
import time

router = APIRouter()


@router.post("/cron/generate-weekly-combinations-optimized")
async def generate_weekly_combinations_optimized():
    """Generate weekly combinations using grid search optimization"""
    start_time = time.time()
    logger.info("Arrr! Starting OPTIMIZED weekly combination generation with grid search, praisin' the FSM!", context={"start_time": start_time})
    
    # Initialize cron tracking
    db = get_db_session()
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="generate-weekly-combinations-optimized",
            job_type="optimized",
            metadata={"start_time": start_time}
        )
        
        try:
            # Get all draws, filtering out strong_number == 8
            draws, filtered_count, draws_time = load_draws_with_filter(db)
            
            logger.info(
                "Arrr! Filtered out draws with strong_number == 8 for OPTIMIZED weekly generation, praisin' the FSM!",
                context={
                    "filtered_count": filtered_count, 
                    "total_after_filter": len(draws),
                    "draws_load_time": f"{draws_time:.2f}s"
                }
            )
            
            if len(draws) < 30:
                error_msg = "Not enough draws in database for optimization (need at least 30)."
                logger.error(error_msg)
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            # Run grid search optimization
            grid_search_start = time.time()
            grid_search = WeeklyCombinationsGridSearch(db)
            optimized_params = grid_search.get_optimized_parameters(
                draws=draws,
                quick_mode=True,  # Use quick mode for cron jobs
                use_cache=True
            )
            grid_search_time = time.time() - grid_search_start
            
            logger.info(
                "Arrr! Grid search optimization completed",
                context={
                    "optimized_params": optimized_params,
                    "grid_search_time": f"{grid_search_time:.2f}s",
                    "expected_roi": optimized_params.get('expected_roi', 0)
                }
            )
            
            # Use optimized parameters for generation
            main_algo_name = optimized_params['main_algo']
            strong_algo_name = optimized_params['strong_algo']
            top_n = optimized_params['top_n']
            num_to_recommend = optimized_params['num_to_recommend']
            test_count = optimized_params['test_count']
            
            # Split data using optimized test_count
            train_draws = draws[:-test_count]
            train_start = train_draws[0].date
            train_end = train_draws[-1].date
            
            # Generate combinations using optimized parameters
            combos, strong_number, generation_time = generate_combinations(
                db=db,
                main_algo_name=main_algo_name,
                strong_algo_name=strong_algo_name,
                draws=draws,
                top_n=top_n,
                num_to_recommend=num_to_recommend,
                version="optimized_weekly_generation",
                cron_job=cron_job,
                start_time=start_time
            )
            
            # Validate algorithm result
            error_msg = validate_combos_result(combos, main_algo_name, "optimized_weekly_generation", cron_job, start_time, optimized_params)
            if error_msg:
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            logger.info(
                "Arrr! Generated optimized combinations",
                context={
                    "generation_time": f"{generation_time:.2f}s",
                    "num_combinations": len(combos),
                    "optimized_params": optimized_params
                }
            )
            
            now = datetime.utcnow()
            
            # Create a new Prediction row for this generation event
            db_start = time.time()
            
            # Get model IDs with proper error handling
            main_model, strong_model = get_model_objects(db, main_algo_name, strong_algo_name)
            
            if not main_model or not strong_model:
                error_msg = f"Models not found: main={main_algo_name}, strong={strong_algo_name}"
                logger.error(
                    "Arrr! Models not found in database!",
                    context={
                        "main_algo_name": main_algo_name,
                        "strong_algo_name": strong_algo_name,
                        "main_model_found": main_model is not None,
                        "strong_model_found": strong_model is not None
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            new_prediction = Prediction(
                model_id=main_model.id,
                strong_model_id=strong_model.id,
                run_time=now,
                roi=optimized_params.get('expected_roi', 0),
                total_prize=0,  # Will be calculated when results are known
                total_cost=num_to_recommend * 2,  # Approximate cost
                test_count=test_count,
                notes=f"OPTIMIZED Weekly combination generation at {now.isoformat()} | Grid Search ROI: {optimized_params.get('expected_roi', 0):.4f} | Params: {optimized_params}",
                train_start_date=train_start,
                train_end_date=train_end,
                num_test_draws=test_count,
                main_model_params={
                    "top_n": top_n, 
                    "num_to_recommend": num_to_recommend,
                    "optimization_method": "grid_search"
                },
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
                version="optimized_weekly_generation",
                now=now
            )
            
            # Check if we processed any valid combos
            if valid_combos_processed == 0:
                error_msg = f"No valid combinations found from optimized algorithm {main_algo_name}"
                logger.error(
                    "Arrr! No valid combinations processed in optimized mode!",
                    context={
                        "algorithm": main_algo_name,
                        "total_combos_received": len(combos),
                        "valid_combos_processed": valid_combos_processed,
                        "optimized_params": optimized_params
                    }
                )
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            db.commit()
            db_time = time.time() - db_start
            
            total_time = time.time() - start_time
            
            # Mark job as completed
            if cron_job:
                tracker.complete_job(cron_job, total_time)
            
            logger.info(
                f"Arrr! Generated {valid_combos_processed} OPTIMIZED weekly combinations using grid search",
                context={
                    "main_algo": main_algo_name,
                    "strong_algo": strong_algo_name,
                    "expected_roi": optimized_params.get('expected_roi', 0),
                    "num_combinations": valid_combos_processed,
                    "prediction_id": new_prediction.id,
                    "total_time": f"{total_time:.2f}s",
                    "breakdown": {
                        "draws_load": f"{draws_time:.2f}s",
                        "grid_search": f"{grid_search_time:.2f}s",
                        "generation": f"{generation_time:.2f}s",
                        "database": f"{db_time:.2f}s"
                    },
                    "optimized_params": optimized_params
                }
            )
            
            return {
                "status": "success", 
                "message": f"OPTIMIZED Weekly combinations generated successfully using grid search",
                "num_combinations": valid_combos_processed,
                "prediction_id": new_prediction.id,
                "total_time": f"{total_time:.2f}s",
                "optimized_parameters": optimized_params,
                "performance_breakdown": {
                    "draws_load": f"{draws_time:.2f}s",
                    "grid_search": f"{grid_search_time:.2f}s",
                    "generation": f"{generation_time:.2f}s",
                    "database": f"{db_time:.2f}s"
                }
            }
            
        except Exception as e:
            error_msg = f"Error in OPTIMIZED weekly combination generation: {str(e)}"
            logger.error(
                "Arrr! Error in OPTIMIZED weekly combination generation!",
                context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
            )
            if cron_job:
                tracker.fail_job(cron_job, error_msg, time.time() - start_time)
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Error in OPTIMIZED weekly combination generation endpoint: {str(e)}"
        logger.error(
            "Arrr! Error in OPTIMIZED weekly combination generation endpoint!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))

