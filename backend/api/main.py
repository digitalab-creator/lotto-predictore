from fastapi import FastAPI, Depends, Query, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from logger import logger
from algorithms import register_algorithms, get_registered_algorithms
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import date, datetime, timedelta
from services.simulation_engine import SimulationEngine
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy import desc, text
from models import Draw
from config import NUM_COMBINATIONS_TO_RECOMMEND
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from models.prediction import Prediction
from models.model import Model
import math
from collections import defaultdict
import json
from models.generated_combination import GeneratedCombination
from models.weekly_winning_combination import WeeklyWinningCombination
import sys
from pathlib import Path
import os
import torch
import torch.nn as nn
from algorithms.dl.sequence_classifier import LottoLSTM
import shutil
import time

# Initialize FastAPI app
app = FastAPI(title="Lotto Predictor Backend")

# Log startup
logger.info("Arrr! FastAPI backend be startin' up, praisin' the FSM!", context={"service": "backend"})

# Register algorithms
register_algorithms()
logger.info("Arrr! Registered algorithms at startup", context={"algorithms": get_registered_algorithms()})

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Ahoy! The backend be runnin', praisin' the FSM!"}

@app.get("/simulate")
def simulate(
    train_start: date = Query(..., description="Start date for training data (YYYY-MM-DD)"),
    train_end: date = Query(..., description="End date for training data (YYYY-MM-DD)"),
    test_count: int = Query(4, description="How many draws to test after train_end"),
    top_n: int = Query(3, description="Top N frequent numbers per position (for position-based algorithms). For 'top_6_overall_frequent_v2', top_n must be at least 6 (recommended 10)."),
    algorithms: str = Query(None, description="Comma-separated list of algorithm names to run (default: all)"),
    strong_algorithms: str = Query(None, description="Comma-separated list of strong number algorithm names to run (default: all)"),
    db: Session = Depends(get_db)
):
    engine = SimulationEngine(db)
    algo_names = [a.strip() for a in algorithms.split(",")] if algorithms else None
    strong_algo_names = [a.strip() for a in strong_algorithms.split(",")] if strong_algorithms else None
    results = engine.run_comparison(train_start, train_end, test_count, top_n, algo_names=algo_names, strong_algo_names=strong_algo_names)
    return results

@app.get("/simulate/table", response_class=PlainTextResponse)
def simulate_table(
    train_start: date = Query(None, description="Start date for training data (YYYY-MM-DD), optional - will be determined automatically if not provided"),
    train_end: date = Query(None, description="End date for training data (YYYY-MM-DD), optional - will be determined automatically if not provided"),
    test_count: int = Query(4, description="How many draws to test after train_end"),
    top_n: int = Query(3, description="Top N frequent numbers per position (for position-based algorithms). For 'top_6_overall_frequent_v2', top_n must be at least 6 (recommended 10)."),
    algorithms: str = Query(None, description="Comma-separated list of algorithm names to run (default: all)"),
    strong_algorithms: str = Query(None, description="Comma-separated list of strong number algorithm names to run (default: all)"),
    use_cache: bool = Query(True, description="Whether to use cached results (default: true)"),
    db: Session = Depends(get_db)
):
    # Arrr! If train_start or train_end be None, calculate 'em from draws and test_count, praisin' the FSM!
    draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
    filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
    logger.info(
        "Arrr! Filtered out draws with strong_number == 8, praisin' the FSM!",
        context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
    )
    if train_start is None or train_end is None:
        if len(draws) <= test_count:
            logger.error(
                "Arrr! Not enough draws to split into train and test! Praisin' the FSM for catchin' this!",
                context={"draw_count": len(draws), "test_count": test_count}
            )
            return PlainTextResponse(
                f"Arrr! Not enough draws to split into train and test! draw_count={len(draws)}, test_count={test_count}",
                status_code=400
            )
        train_start_calc = draws[0].date
        train_end_calc = draws[-test_count-1].date
        logger.info(
            "Arrr! Calculated train_start and train_end from draws and test_count, praisin' the FSM!",
            context={
                "train_start": str(train_start_calc),
                "train_end": str(train_end_calc),
                "test_count": test_count,
                "draw_count": len(draws)
            }
        )
        train_start = train_start or train_start_calc
        train_end = train_end or train_end_calc
    engine = SimulationEngine(db)
    algo_names = [a.strip() for a in algorithms.split(",")] if algorithms else None
    strong_algo_names = [a.strip() for a in strong_algorithms.split(",")] if strong_algorithms else None
    results = engine.run_comparison(train_start, train_end, test_count, top_n, algo_names=algo_names, strong_algo_names=strong_algo_names, use_cache=use_cache)
    # Generate markdown table
    try:
        from tabulate import tabulate
        use_tabulate = True
    except ImportError:
        use_tabulate = False
    output = []
    for (main_version, strong_version), res in results.items():
        output.append(f"\nAlgorithm: {main_version} | Strong: {strong_version}")
        headers = ["Date", "Actual Numbers", "Actual Strong", "Max Hits", "Any Strong Hit", "Total Prize", "Total"]
        table = []
        for d in res["dates"]:
            # Calculate 'Total' for each combo (hits + strong_hit)
            totals = [c["hits"] + (1 if c["strong_hit"] else 0) for c in d["combos"]]
            max_total = max(totals) if totals else 0
            table.append([
                d["test_draw_date"],
                d["actual_numbers"],
                d["actual_strong"],
                d["max_hits"],
                d["any_strong_hit"],
                d["total_prize"],
                max_total
            ])
        if use_tabulate:
            output.append(tabulate(table, headers=headers, tablefmt="github"))
        else:
            output.append(" | ".join(headers))
            for row in table:
                output.append(" | ".join(str(x) for x in row))
        output.append(f"Total Prize: {res['total_prize']}, Total Cost: {res['total_cost']}, ROI: {res['roi']}")
    # Add combo index insights
    output.append("\n=== Combo Index Insights (Average Hits per Combo Index) ===")
    for (main_version, strong_version), res in results.items():
        combo_hit_stats = [[] for _ in range(8)]
        for date in res["dates"]:
            for idx, combo_result in enumerate(date["combos"]):
                if idx < 8:
                    combo_hit_stats[idx].append(combo_result["hits"])
        output.append(f"Algorithm: {main_version} | Strong: {strong_version}")
        for idx, hits in enumerate(combo_hit_stats):
            avg_hits = sum(hits) / len(hits) if hits else 0
            output.append(f"  Combo #{idx+1}: Avg Hits = {avg_hits:.2f} (n={len(hits)})")
    return "\n".join(output)

@app.get("/generate-combinations", response_class=JSONResponse)
def generate_combinations(db: Session = Depends(get_db)):
    """
    Generate lottery combinations using the best performing algorithm based on recent simulations.
    This endpoint uses the same logic as the weekly combinations generation.
    """
    logger.info("Arrr! Starting combination generation, praisin' the FSM!")
    
    try:
        # Get all draws, filtering out strong_number == 8
        draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
        filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
        
        logger.info(
            "Arrr! Filtered out draws with strong_number == 8 for generation, praisin' the FSM!",
            context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
        )
        
        if len(draws) < 20:
            logger.error("Not enough draws in database for recommendation.")
            return JSONResponse(content={"error": "Not enough draws in database for recommendation."}, status_code=400)
        
        # Use last 12 draws as test set, rest as training
        train_draws = draws[:-12]
        test_draws = draws[-12:]
        train_start = train_draws[0].date
        train_end = train_draws[-1].date
        test_count = 12
        
        # Find best algorithm pair by ROI using SimulationEngine
        engine = SimulationEngine(db)
        results = {}
        best_pair = None
        best_roi = float('-inf')
        
        for algo_name, algo_cls in ALGORITHM_REGISTRY.items():
            # Set top_n according to algorithm requirements
            if algo_name == 'top_6_overall_frequent_v2':
                top_n = 10
            else:
                top_n = 3
                
            logger.info(f"Running {algo_name} with top_n={top_n}")
            
            try:
                res = engine.run_comparison(train_start, train_end, test_count, top_n, algo_names=[algo_name])
                for (main_algo, strong_algo), r in res.items():
                    results[(main_algo, strong_algo)] = r
                    if r["roi"] > best_roi:
                        best_pair = (main_algo, strong_algo)
                        best_roi = r["roi"]
            except Exception as e:
                logger.error(
                    f"Skipping {algo_name} due to error: {e}",
                    context={"algo_name": algo_name, "error": str(e)}
                )
                continue
        
        if not best_pair:
            logger.error("No algorithm produced results.")
            return JSONResponse(content={"error": "No algorithm produced results."}, status_code=400)
        
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
        
        now = datetime.utcnow()
        
        # Create a new Prediction row for this generation event
        new_prediction = Prediction(
            model_id=db.query(Model).filter(Model.name == main_algo_name).first().id,
            strong_model_id=db.query(Model).filter(Model.name == strong_algo_name).first().id,
            run_time=now,
            roi=best_roi,
            total_prize=results[best_pair]["total_prize"],
            total_cost=results[best_pair]["total_cost"],
            test_count=test_count,
            notes=f"Combination generation at {now.isoformat()} | Best ROI: {best_roi:.4f}",
            train_start_date=train_start,
            train_end_date=train_end,
            num_test_draws=test_count,
            main_model_params={"top_n": top_n, "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND},
            strong_model_params={"strong_algo": strong_algo_name}
        )
        db.add(new_prediction)
        db.flush()  # Get the new prediction.id
        
        # Store each combo in DB
        stored_combos = []
        for idx, combo in enumerate(combos):
            generated = GeneratedCombination(
                prediction_id=new_prediction.id,
                numbers=combo["numbers"],
                strong_number=strong_number,
                position=idx+1,
                generated_at=now
            )
            db.add(generated)
            
            stored_combos.append({
                "numbers": combo["numbers"],
                "strong": strong_number,
                "position": idx+1
            })
            
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
        
        logger.info(
            f"Arrr! Generated {len(combos)} combinations using {main_algo_name} + {strong_algo_name}",
            context={
                "main_algo": main_algo_name,
                "strong_algo": strong_algo_name,
                "best_roi": best_roi,
                "num_combinations": len(combos),
                "prediction_id": new_prediction.id
            }
        )
        
        return {
            "algorithm": main_algo_name,
            "strong_algorithm": strong_algo_name,
            "roi": best_roi,
            "total_prize": results[best_pair]["total_prize"],
            "total_cost": results[best_pair]["total_cost"],
            "num_test_draws": test_count,
            "combinations": stored_combos,
            "prediction_id": new_prediction.id,
            "train_start": train_start.isoformat(),
            "train_end": train_end.isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Error in combination generation!",
            context={"error": str(e)}
        )
        db.rollback()
        return JSONResponse(content={"error": f"Error generating combinations: {str(e)}"}, status_code=500)

@app.get("/weekly-winning-combinations", response_class=JSONResponse)
def get_weekly_winning_combinations(db: Session = Depends(get_db)):
    """
    Get the top 5 winning combinations for the current week.
    """
    logger.info("Arrr! Fetching weekly winning combinations! Praisin' the FSM!")
    
    # Calculate current week's date range
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    combinations = db.query(WeeklyWinningCombination).filter(
        WeeklyWinningCombination.week_start_date == week_start,
        WeeklyWinningCombination.week_end_date == week_end
    ).order_by(WeeklyWinningCombination.total_roi.desc()).all()
    
    if not combinations:
        logger.warning(
            "Arrr! No winning combinations found for current week!",
            context={"week_start": week_start, "week_end": week_end}
        )
        return JSONResponse(
            content={"error": "No winning combinations found for current week"},
            status_code=404
        )
    
    result = []
    for combo in combinations:
        result.append({
            "model_id": combo.model_id,
            "strong_model_id": combo.strong_model_id,
            "main_model_params": combo.main_model_params,
            "strong_model_params": combo.strong_model_params,
            "total_roi": combo.total_roi,
            "num_prediction_runs": combo.num_prediction_runs,
            "num_tickets": combo.num_tickets,
            "total_cost": combo.total_cost,
            "total_prize": combo.total_prize,
            "week_start_date": combo.week_start_date.isoformat(),
            "week_end_date": combo.week_end_date.isoformat(),
            "created_at": combo.created_at.isoformat()
        })
    
    logger.info(
        f"Arrr! Found {len(result)} winning combinations!",
        context={"week_start": week_start, "week_end": week_end, "num_combinations": len(result)}
    )
    
    return JSONResponse(content={"combinations": result}) 

@router.post("/cron/generate-weekly-combinations")
async def generate_weekly_combinations():
    """Generate weekly combinations - called by cron service"""
    start_time = time.time()
    logger.info("Arrr! Starting weekly combination generation, praisin' the FSM!", context={"start_time": start_time})
    
    try:
        # Use the same logic as the /generate-combinations endpoint
        from services.simulation_engine import SimulationEngine
        
        db = next(get_db())
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
                logger.error("Not enough draws in database for recommendation.")
                return {"status": "error", "message": "Not enough draws in database for recommendation."}
            
            # Use last 12 draws as test set, rest as training
            train_draws = draws[:-12]
            test_draws = draws[-12:]
            train_start = train_draws[0].date
            train_end = train_draws[-1].date
            test_count = 12
            
            # Find best algorithm pair by ROI using SimulationEngine
            engine_start = time.time()
            engine = SimulationEngine(db)
            results = {}
            best_pair = None
            best_roi = float('-inf')
            
            # Get all algorithm names for progress tracking
            all_algorithms = list(ALGORITHM_REGISTRY.keys())
            total_algorithms = len(all_algorithms)
            
            logger.info(
                f"Arrr! Starting algorithm evaluation for {total_algorithms} algorithms",
                context={
                    "total_algorithms": total_algorithms,
                    "algorithms": all_algorithms
                }
            )
            
            for idx, (algo_name, algo_cls) in enumerate(ALGORITHM_REGISTRY.items(), 1):
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
                logger.error("No algorithm produced results.")
                return {"status": "error", "message": "No algorithm produced results."}
            
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
            logger.error(
                "Arrr! Error in weekly combination generation!",
                context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
            )
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(
            "Arrr! Error in weekly combination generation endpoint!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron/fetch-latest-draw")
async def fetch_latest_draw():
    """Fetch latest draw - called by cron service"""
    try:
        # Import and run the script
        from services.fetch_latest_draw import main as fetch_draw
        fetch_draw()
        return {"status": "success", "message": "Latest draw fetched successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron/generate-weekly-tables")
async def generate_weekly_tables():
    """Generate weekly tables - called by cron service"""
    try:
        # Import and run the script
        from scripts.generate_weekly_tables import main as generate_tables
        generate_tables()
        return {"status": "success", "message": "Weekly tables generated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron/update-weekly-winning-combinations")
async def update_weekly_winning_combinations():
    """Update weekly winning combinations - called by cron service"""
    try:
        # Import and run the script
        from scripts.update_weekly_winning_combinations import update_weekly_winning_combinations
        update_weekly_winning_combinations()
        return {"status": "success", "message": "Weekly winning combinations updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron/generate-best-model-tables")
async def generate_best_model_tables():
    """Generate tables using the best performing model (ROI > 1) - called by cron service"""
    try:
        # Import and run the script
        from scripts.generate_best_model_tables import generate_best_model_tables
        result = generate_best_model_tables()
        return {"status": "success", "message": "Best model tables generated successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron/send-best-model-email")
async def send_best_model_email():
    """Send email with best model tables - called by cron service"""
    try:
        # Import and run the script
        from scripts.send_best_model_email import send_best_model_email
        result = send_best_model_email()
        return {"status": "success", "message": "Best model email sent successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(router)

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that verifies both FastAPI and database connection"""
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "services": {
                "fastapi": "up",
                "database": "up"
            }
        }
    except Exception as e:
        logger.error("Health check failed", context={'error': str(e)})
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "services": {
                    "fastapi": "up",
                    "database": "down",
                    "error": str(e)
                }
            }
        )

@app.post("/api/check-model-files")
async def check_model_files_endpoint(db: Session = Depends(get_db)):
    """
    Endpoint to check all PyTorch model files for corruption.
    Does a thorough check by trying to use the model, not just load it.
    If loading fails, tries different model architectures to find the correct one.
    Returns detailed report of model file health status.
    """
    try:
        import torch
        import torch.nn as nn
        from pathlib import Path
        import shutil
        from datetime import datetime
        import re
        
        models_dir = Path("/app/algorithms/dl/models")
        corrupted_files = []
        healthy_files = []
        
        # Get all models from database
        db_models = db.query(Model).all()
        model_paths = {m.model_path for m in db_models if m.model_path}
        
        # Model class definitions for thorough testing
        class LottoLSTMPosition(nn.Module):
            def __init__(self, num_numbers=37, seq_len=10, hidden_size=64, num_layers=2, num_positions=6):
                super().__init__()
                self.num_numbers = num_numbers
                self.seq_len = seq_len
                self.num_positions = num_positions
                self.lstm = nn.LSTM(input_size=num_numbers, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, num_numbers * num_positions)
                self.softmax = nn.Softmax(dim=2)

            def forward(self, x):
                out, _ = self.lstm(x)
                out = out[:, -1, :]  # Take last output
                out = self.fc(out)
                out = out.view(-1, self.num_positions, self.num_numbers)
                out = self.softmax(out)
                return out

        def try_load_model(fname, is_position_model, state_dict):
            """Try loading the model with different architectures until one works."""
            # Try architectures in order of likelihood
            hidden_sizes = [64, 128, 256, 32]  # Most common first
            num_layers_options = [2, 1, 3]      # Most common first
            
            # First try the architecture from filename
            hidden_size = 64  # default
            num_layers = 2    # default
            if "h128" in fname.name:
                hidden_size = 128
            elif "h256" in fname.name:
                hidden_size = 256
            elif "h32" in fname.name:
                hidden_size = 32
            if "l1" in fname.name:
                num_layers = 1
            elif "l3" in fname.name:
                num_layers = 3
            
            # Try the architecture from filename first
            try:
                if is_position_model:
                    model = LottoLSTMPosition(hidden_size=hidden_size, num_layers=num_layers)
                else:
                    model = LottoLSTM(hidden_size=hidden_size, num_layers=num_layers)
                model.load_state_dict(state_dict)
                return model, hidden_size, num_layers
            except Exception as e:
                logger.warning(
                    f"Arrr! Failed to load {fname.name} with architecture from filename, trying others...",
                    context={
                        "file": fname.name,
                        "error": str(e),
                        "tried_hidden_size": hidden_size,
                        "tried_num_layers": num_layers
                    }
                )
            
            # Try other architectures
            for h in hidden_sizes:
                for l in num_layers_options:
                    if h == hidden_size and l == num_layers:
                        continue  # Skip the one we already tried
                    try:
                        if is_position_model:
                            model = LottoLSTMPosition(hidden_size=h, num_layers=l)
                        else:
                            model = LottoLSTM(hidden_size=h, num_layers=l)
                        model.load_state_dict(state_dict)
                        logger.info(
                            f"Arrr! Found correct architecture for {fname.name}!",
                            context={
                                "file": fname.name,
                                "actual_hidden_size": h,
                                "actual_num_layers": l,
                                "filename_hidden_size": hidden_size,
                                "filename_num_layers": num_layers
                            }
                        )
                        return model, h, l
                    except Exception:
                        continue
            
            raise Exception("Could not find a working architecture for this model")
        
        # Check each .pt file
        for fname in models_dir.glob("*.pt"):
            try:
                # First try loading the state dict
                state_dict = torch.load(str(fname))
                
                # Determine model type from filename
                is_position_model = "position" in fname.name
                
                # Try to load the model with different architectures
                model, actual_hidden_size, actual_num_layers = try_load_model(fname, is_position_model, state_dict)
                
                # Try to use the model
                model.eval()
                with torch.no_grad():
                    # Create dummy input
                    if is_position_model:
                        dummy_input = torch.zeros((1, model.seq_len, 37))
                        output = model(dummy_input)
                        # Check output shape
                        assert output.shape == (1, model.num_positions, 37), f"Invalid output shape: {output.shape}"
                    else:
                        dummy_input = torch.zeros((1, model.seq_len, 37))
                        output = model(dummy_input)
                        # Check output shape
                        assert output.shape == (1, 37), f"Invalid output shape: {output.shape}"
                
                # Get architecture from filename for comparison
                filename_hidden_size = 64  # default
                filename_num_layers = 2    # default
                if "h128" in fname.name:
                    filename_hidden_size = 128
                elif "h256" in fname.name:
                    filename_hidden_size = 256
                elif "h32" in fname.name:
                    filename_hidden_size = 32
                if "l1" in fname.name:
                    filename_num_layers = 1
                elif "l3" in fname.name:
                    filename_num_layers = 3
                
                file_info = {
                    "file": fname.name,
                    "size": fname.stat().st_size,
                    "last_modified": datetime.fromtimestamp(fname.stat().st_mtime).isoformat(),
                    "in_db": str(fname) in model_paths,
                    "model_type": "position" if is_position_model else "sequence",
                    "filename_hidden_size": filename_hidden_size,
                    "filename_num_layers": filename_num_layers,
                    "actual_hidden_size": actual_hidden_size,
                    "actual_num_layers": actual_num_layers,
                    "architecture_mismatch": filename_hidden_size != actual_hidden_size or filename_num_layers != actual_num_layers
                }
                healthy_files.append(file_info)
                logger.info(
                    f"Arrr! Model file {fname.name} be healthy!",
                    context={
                        "file": fname.name,
                        "in_db": file_info["in_db"],
                        "model_type": file_info["model_type"],
                        "filename_hidden_size": filename_hidden_size,
                        "filename_num_layers": filename_num_layers,
                        "actual_hidden_size": actual_hidden_size,
                        "actual_num_layers": actual_num_layers,
                        "architecture_mismatch": file_info["architecture_mismatch"]
                    }
                )
            except Exception as e:
                file_info = {
                    "file": fname.name,
                    "error": str(e),
                    "size": fname.stat().st_size,
                    "last_modified": datetime.fromtimestamp(fname.stat().st_mtime).isoformat(),
                    "in_db": str(fname) in model_paths,
                    "model_type": "position" if "position" in fname.name else "sequence"
                }
                corrupted_files.append(file_info)
                logger.error(
                    f"Arrr! Found corrupted model file: {fname.name}!",
                    context={
                        "file": fname.name,
                        "error": str(e),
                        "in_db": file_info["in_db"],
                        "model_type": file_info["model_type"]
                    }
                )
                # Move corrupted file to backup directory
                backup_dir = models_dir / "corrupted_backups"
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"{fname.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{fname.suffix}"
                shutil.move(str(fname), str(backup_path))
                logger.info(
                    f"Arrr! Moved corrupted file {fname.name} to backup: {backup_path.name}",
                    context={
                        "original_file": fname.name,
                        "backup_file": backup_path.name
                    }
                )
                
                # Update database if model was registered
                if str(fname) in model_paths:
                    db_model = next((m for m in db_models if m.model_path == str(fname)), None)
                    if db_model:
                        db_model.model_path = None  # Clear the path since file is corrupted
                        db.add(db_model)
                        logger.warning(
                            f"Arrr! Cleared model_path for corrupted model in DB: {db_model.name} v{db_model.version}",
                            context={
                                "model_id": db_model.id,
                                "model_name": db_model.name,
                                "model_version": db_model.version
                            }
                        )
        
        # Commit any database changes
        if corrupted_files:
            db.commit()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checked": len(healthy_files) + len(corrupted_files),
                "healthy_files": len(healthy_files),
                "corrupted_files": len(corrupted_files),
                "files_in_db": len(model_paths),
                "files_with_architecture_mismatch": sum(1 for f in healthy_files if f.get("architecture_mismatch", False))
            },
            "healthy_files": healthy_files,
            "corrupted_files": corrupted_files
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Error during model file check!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check model files: {str(e)}"
        ) 