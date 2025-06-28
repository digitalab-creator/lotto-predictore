from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.base import SessionLocal
from datetime import datetime
from services.cron_tracker import CronTracker
from services.simulation_engine import SimulationEngine
from models import Draw, Prediction, Model, GeneratedCombination
from config import NUM_COMBINATIONS_TO_RECOMMEND
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from logger import logger
import time

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_model_prediction_details_count(db: Session):
    """Get the current count of prediction details for each model combination"""
    query = """
    SELECT 
        mm.name AS main_model_name,
        sm.name AS strong_model_name,
        COUNT(pd.id) AS prediction_details_count
    FROM models mm
    CROSS JOIN models sm
    LEFT JOIN predictions p ON p.model_id = mm.id AND p.strong_model_id = sm.id
    LEFT JOIN prediction_details pd ON pd.prediction_id = p.id
    WHERE mm.type = 'main' AND sm.type = 'strong'
    GROUP BY mm.name, sm.name
    ORDER BY prediction_details_count ASC
    """
    
    result = db.execute(text(query))
    return {f"{row.main_model_name}_{row.strong_model_name}": row.prediction_details_count for row in result}

def get_balanced_algorithm_list(db: Session, target_details_per_model: int = 100):
    """Get a balanced list of algorithms to run, prioritizing those with fewer prediction details"""
    current_counts = get_model_prediction_details_count(db)
    
    # Get all algorithm combinations
    all_combinations = []
    for main_algo in ALGORITHM_REGISTRY.keys():
        for strong_algo in STRONG_NUMBER_REGISTRY.keys():
            key = f"{main_algo}_{strong_algo}"
            current_count = current_counts.get(key, 0)
            all_combinations.append({
                'main_algo': main_algo,
                'strong_algo': strong_algo,
                'current_details': current_count,
                'priority_score': max(0, target_details_per_model - current_count)
            })
    
    # Sort by priority score (highest first) and then by current count (lowest first)
    all_combinations.sort(key=lambda x: (-x['priority_score'], x['current_details']))
    
    # Return the top algorithms that need more data
    return [combo for combo in all_combinations if combo['priority_score'] > 0]

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
            balanced_algorithms = get_balanced_algorithm_list(db, target_details_per_model=100)
            
            if not balanced_algorithms:
                logger.info("Arrr! All models have sufficient prediction details, running all algorithms")
                # If all models are balanced, run all algorithms
                all_algorithms = list(ALGORITHM_REGISTRY.keys())
                total_algorithms = len(all_algorithms)
            else:
                # Use the top algorithms that need more data
                top_algorithms = balanced_algorithms[:10]  # Limit to top 10 to avoid too long runs
                all_algorithms = list(set([combo['main_algo'] for combo in top_algorithms]))
                total_algorithms = len(all_algorithms)
                
                logger.info(
                    f"Arrr! Selected {total_algorithms} algorithms based on prediction details balance",
                    context={
                        "selected_algorithms": all_algorithms,
                        "balance_info": [{"algo": combo['main_algo'], "current_details": combo['current_details'], "priority": combo['priority_score']} for combo in top_algorithms[:5]]
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
                    "algorithms": all_algorithms
                }
            )
            
            for idx, algo_name in enumerate(all_algorithms, 1):
                algo_start = time.time()
                
                # Set top_n according to algorithm requirements
                if algo_name == 'top_6_overall_frequent_v2':
                    top_n = 10
                else:
                    top_n = 3
                    
                logger.info(
                    f"Arrr! Running algorithm {idx}/{total_algorithms}: {algo_name}",
                    context={
                        "algorithm": algo_name,
                        "progress": f"{idx}/{total_algorithms}",
                        "top_n": top_n,
                        "elapsed_time": f"{time.time() - start_time:.2f}s"
                    }
                )
                
                try:
                    res = engine.run_comparison(train_start, train_end, test_count, top_n, algo_names=[algo_name])
                    for (main_algo, strong_algo), r in res.items():
                        results[(main_algo, strong_algo)] = r
                        if r["roi"] > best_roi:
                            best_pair = (main_algo, strong_algo)
                            best_roi = r["roi"]
                            
                    algo_time = time.time() - algo_start
                    logger.info(
                        f"Arrr! Completed algorithm {algo_name}",
                        context={
                            "algorithm": algo_name,
                            "algorithm_time": f"{algo_time:.2f}s",
                            "best_roi_so_far": best_roi,
                            "total_elapsed": f"{time.time() - start_time:.2f}s"
                        }
                    )
                    
                except Exception as e:
                    algo_time = time.time() - algo_start
                    logger.error(
                        f"Arrr! Skipping {algo_name} due to error",
                        context={
                            "algorithm": algo_name,
                            "error": str(e),
                            "algorithm_time": f"{algo_time:.2f}s"
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
            
            # Use correct top_n for the best algorithm
            if main_algo_name == 'top_6_overall_frequent_v2':
                top_n = 10
            else:
                top_n = 3
            
            # Generate combinations using all draws
            all_draws = draws
            combos = main_algo_cls().run(all_draws, top_n=top_n, num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND)
            strong_algo = strong_algo_cls()
            strong_number = strong_algo.predict(all_draws)
            
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
            new_prediction = Prediction(
                model_id=db.query(Model).filter(Model.name == main_algo_name).first().id,
                strong_model_id=db.query(Model).filter(Model.name == strong_algo_name).first().id,
                run_time=now,
                roi=best_roi,
                total_prize=results[best_pair]["total_prize"],
                total_cost=results[best_pair]["total_cost"],
                test_count=test_count,
                notes=f"Weekly combination generation at {now.isoformat()} | Best ROI: {best_roi:.4f}",
                train_start_date=train_start,
                train_end_date=train_end,
                num_test_draws=test_count,
                main_model_params={"top_n": top_n, "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND},
                strong_model_params={"strong_algo": strong_algo_name}
            )
            db.add(new_prediction)
            db.flush()  # Get the new prediction.id
            
            # Store each combo in DB
            for idx, combo in enumerate(combos):
                generated = GeneratedCombination(
                    prediction_id=new_prediction.id,
                    numbers=combo["numbers"],
                    strong_number=strong_number,
                    position=idx+1,
                    generated_at=now
                )
                db.add(generated)
                
                logger.info(
                    f"Stored combo {idx+1}: {combo['numbers']} + {strong_number}",
                    context={
                        "prediction_id": new_prediction.id,
                        "numbers": combo["numbers"],
                        "strong_number": strong_number,
                        "position": idx+1
                    }
                )
            
            db.commit()
            db_time = time.time() - db_start
            
            total_time = time.time() - start_time
            
            # Mark job as completed
            if cron_job:
                tracker.complete_job(cron_job, total_time)
            
            logger.info(
                f"Arrr! Generated {len(combos)} weekly combinations using {main_algo_name} + {strong_algo_name}",
                context={
                    "main_algo": main_algo_name,
                    "strong_algo": strong_algo_name,
                    "best_roi": best_roi,
                    "num_combinations": len(combos),
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
                "num_combinations": len(combos),
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

@router.post("/cron/fetch-latest-draw")
async def fetch_latest_draw():
    """Fetch latest draw - called by cron service"""
    start_time = time.time()
    
    # Initialize cron tracking
    db = next(get_db())
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="fetch-latest-draw",
            job_type="scheduled",
            metadata={"start_time": start_time}
        )
        
        # Import and run the script
        from services.fetch_latest_draw import main as fetch_draw
        fetch_draw()
        
        total_time = time.time() - start_time
        
        # Mark job as completed
        if cron_job:
            tracker.complete_job(cron_job, total_time)
        
        logger.info(
            "Arrr! Latest draw fetched successfully!",
            context={
                "total_time": f"{total_time:.2f}s",
                "job_id": cron_job.id if cron_job else None
            }
        )
        
        return {"status": "success", "message": "Latest draw fetched successfully"}
        
    except Exception as e:
        error_msg = f"Error fetching latest draw: {str(e)}"
        logger.error(
            "Arrr! Error fetching latest draw!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/cron/generate-best-model-tables")
async def generate_best_model_tables():
    """Generate tables using the best performing model (ROI > 1) - called by cron service"""
    start_time = time.time()
    
    # Initialize cron tracking
    db = next(get_db())
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="generate-best-model-tables",
            job_type="scheduled",
            metadata={"start_time": start_time}
        )
        
        # Import and run the script
        from scripts.generate_best_model_tables import generate_best_model_tables
        result = generate_best_model_tables()
        
        total_time = time.time() - start_time
        
        # Mark job as completed
        if cron_job:
            tracker.complete_job(cron_job, total_time)
        
        logger.info(
            "Arrr! Best model tables generated successfully!",
            context={
                "total_time": f"{total_time:.2f}s",
                "job_id": cron_job.id if cron_job else None
            }
        )
        
        return {"status": "success", "message": "Best model tables generated successfully", "data": result}
        
    except Exception as e:
        error_msg = f"Error generating best model tables: {str(e)}"
        logger.error(
            "Arrr! Error generating best model tables!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/cron/prediction-balance-status")
async def get_prediction_balance_status(db: Session = Depends(get_db)):
    """Get the current balance status of prediction details across all models"""
    try:
        current_counts = get_model_prediction_details_count(db)
        balanced_algorithms = get_balanced_algorithm_list(db, target_details_per_model=100)
        
        # Calculate statistics
        all_counts = list(current_counts.values())
        min_count = min(all_counts) if all_counts else 0
        max_count = max(all_counts) if all_counts else 0
        avg_count = sum(all_counts) / len(all_counts) if all_counts else 0
        
        # Group by main algorithm
        main_algo_stats = {}
        for key, count in current_counts.items():
            main_algo = key.split('_')[0]  # Extract main algorithm name
            if main_algo not in main_algo_stats:
                main_algo_stats[main_algo] = []
            main_algo_stats[main_algo].append(count)
        
        # Calculate average per main algorithm
        main_algo_averages = {
            algo: sum(counts) / len(counts) 
            for algo, counts in main_algo_stats.items()
        }
        
        return {
            "status": "success",
            "balance_summary": {
                "total_model_combinations": len(current_counts),
                "min_prediction_details": min_count,
                "max_prediction_details": max_count,
                "average_prediction_details": round(avg_count, 2),
                "models_needing_data": len(balanced_algorithms),
                "target_details_per_model": 100
            },
            "top_models_needing_data": [
                {
                    "main_algo": combo['main_algo'],
                    "strong_algo": combo['strong_algo'],
                    "current_details": combo['current_details'],
                    "priority_score": combo['priority_score']
                }
                for combo in balanced_algorithms[:10]
            ],
            "main_algorithm_averages": {
                algo: round(avg, 2) for algo, avg in main_algo_averages.items()
            },
            "all_model_details": current_counts
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Error getting prediction balance status!",
            context={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cron/status")
async def get_cron_status(db: Session = Depends(get_db)):
    """Get detailed status of all cron jobs from the database"""
    try:
        tracker = CronTracker(db)
        job_summary = tracker.get_job_status_summary()
        
        return {
            "status": "success",
            "jobs": job_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(
            "Arrr! Failed to get cron status!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to get cron status: {str(e)}"
            }
        ) 