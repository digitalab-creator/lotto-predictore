from fastapi import FastAPI, Depends, Query, APIRouter, HTTPException
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
    return {
        "evidence_valid": False,
        "evidence_reason": "This comparison reuses one portfolio on later draws. It is not the sealed go/no-go test. Read /validation/report.",
        "comparison": results,
    }

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
    from services.pais_draw_rules import CURRENT_REGIME_START

    draws = db.query(Draw).filter(Draw.date >= CURRENT_REGIME_START).order_by(Draw.date).all()
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
    output = [
        "EVIDENCE INVALID: reused portfolio, not a sealed test. See /validation/report."
    ]
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
    Generate the production next-draw pack from the exact coverage wheel.
    """
    from services.prediction_service import PredictionService

    logger.info("Arrr! generate-combinations → generate_next_draw, praisin' the FSM!")
    try:
        result = PredictionService(db).generate_next_draw()
        if not result.get("success"):
            return JSONResponse(
                content={"error": result.get("message", "Generation failed")},
                status_code=400,
            )
        return {
            "algorithm": result["algorithm"],
            "strong_algorithm": result["strong_algorithm"],
            "strategy_source": result["model_info"]["strategy_source"],
            "training_cutoff": result["as_of_date"],
            "target_draw_number": result["target_draw_number"],
            "combinations": result["combinations"],
            "prediction_id": result["prediction_id"],
            "planned_cost_ils": result["model_info"]["planned_cost_ils"],
        }
    except Exception as e:
        logger.error(
            "Arrr! Error in combination generation!",
            context={"error": str(e)},
        )
        db.rollback()
        return JSONResponse(
            content={"error": f"Error generating combinations: {str(e)}"},
            status_code=500,
        )

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
    """Generate weekly combinations — same path as /generate-combinations."""
    from services.weekly_jobs_gate import skipped_weekly_jobs_payload, weekly_email_and_jobs_enabled

    if not weekly_email_and_jobs_enabled():
        return skipped_weekly_jobs_payload(job="generate-weekly-combinations")
    from services.prediction_service import PredictionService

    logger.info("Arrr! cron generate-weekly-combinations → generate_next_draw")
    db = next(get_db())
    try:
        result = PredictionService(db).generate_next_draw()
        if not result.get("success"):
            return {"status": "error", "message": result.get("message")}
        return {
            "status": "success",
            "message": (
                f"Weekly combinations generated using {result['algorithm']} + "
                f"{result['strong_algorithm']}"
            ),
            "num_combinations": len(result["combinations"]),
            "prediction_id": result["prediction_id"],
            "target_draw_number": result.get("target_draw_number"),
        }
    except Exception as e:
        logger.error(
            "Arrr! Error in weekly combination generation!",
            context={"error": str(e)},
        )
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        db.close()

@router.post("/cron/fetch-latest-draw")
async def fetch_latest_draw():
    """Fetch latest draws, backfill Pais prizes, fill gaps — called by cron service"""
    try:
        from db import SessionLocal
        from services.sync_draws import sync_draws_incremental

        db = SessionLocal()
        try:
            outcome = sync_draws_incremental(db)
        finally:
            db.close()
        status = "success" if not outcome.errors else "partial"
        return {
            "status": status,
            "message": "Draw sync completed",
            "data": outcome.to_dict(),
        }
    except Exception as e:
        logger.error("Draw sync failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cron/post-draw-chain")
async def post_draw_chain(allow_magayo: bool = Query(False)):
    """Ingest the official CSV; on a new result settle, score, pack, and notify."""
    try:
        from db import SessionLocal
        from services.post_draw_chain import PostDrawChainService

        db = SessionLocal()
        try:
            outcome = PostDrawChainService(db).run_full(allow_magayo=allow_magayo)
        finally:
            db.close()
        status = "success" if not outcome.get("error") else "partial"
        return {"status": status, "data": outcome}
    except Exception as e:
        logger.error("Post-draw chain failed", context={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cron/reconcile-draws")
async def reconcile_draws():
    """Sunday check: the last stored draws must match the official CSV."""
    try:
        from db import SessionLocal
        from services.pais_official_sync import reconcile_last_draws

        db = SessionLocal()
        try:
            outcome = reconcile_last_draws(db)
        finally:
            db.close()
        return {"status": "success", "data": outcome}
    except Exception as e:
        logger.error("Draw reconcile failed", context={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/cron/generate-weekly-tables")
async def generate_weekly_tables():
    """Generate weekly tables - called by cron service"""
    from services.weekly_jobs_gate import skipped_weekly_jobs_payload, weekly_email_and_jobs_enabled

    if not weekly_email_and_jobs_enabled():
        return skipped_weekly_jobs_payload(job="generate-weekly-tables")
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
    from services.weekly_jobs_gate import skipped_weekly_jobs_payload, weekly_email_and_jobs_enabled

    if not weekly_email_and_jobs_enabled():
        return skipped_weekly_jobs_payload(job="update-weekly-winning-combinations")
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
    from services.weekly_jobs_gate import skipped_weekly_jobs_payload, weekly_email_and_jobs_enabled

    if not weekly_email_and_jobs_enabled():
        return skipped_weekly_jobs_payload(job="generate-best-model-tables")
    try:
        # Import and run the script
        from scripts.generate_best_model_tables import generate_best_model_tables
        result = generate_best_model_tables()
        return {"status": "success", "message": "Best model tables generated successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/walk-forward/summaries")
def walk_forward_summaries(db: Session = Depends(get_db)):
    """Walk-forward scoreboard rows (Phase 4 — not legacy predictions ROI)."""
    from models.evaluation import StrategySummary

    rows = (
        db.query(StrategySummary)
        .order_by(StrategySummary.random_percentile.desc())
        .all()
    )
    return {
        "count": len(rows),
        "summaries": [
            {
                "strategy_id": r.strategy_id,
                "roi": float(r.roi) if r.roi is not None else None,
                "random_percentile": float(r.random_percentile)
                if r.random_percentile is not None
                else None,
                "independent_draw_count": r.independent_draw_count,
                "has_predictive_edge": r.has_predictive_edge,
                "random_baseline_median_roi": float(r.random_baseline_median_roi)
                if r.random_baseline_median_roi is not None
                else None,
            }
            for r in rows
        ],
    }


@router.post("/walk-forward/refresh")
def walk_forward_refresh(
    min_training: int | None = Query(None),
    skip_dl: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Rebuild evaluation_tickets and strategy_summaries (long-running)."""
    from services.walk_forward_evaluation import WalkForwardEvaluationService

    service = WalkForwardEvaluationService(db)
    return service.refresh_all(min_training=min_training, include_dl=not skip_dl)


@router.post("/cron/send-best-model-email")
async def send_best_model_email():
    """Send email with best model tables - called by cron service"""
    from services.weekly_jobs_gate import skipped_weekly_jobs_payload, weekly_email_and_jobs_enabled

    if not weekly_email_and_jobs_enabled():
        return skipped_weekly_jobs_payload(job="send-best-model-email")
    try:
        # Import and run the script
        from scripts.send_best_model_email import send_best_model_email
        result = send_best_model_email()
        if not result.get("success"):
            raise HTTPException(
                status_code=502,
                detail=result.get("message", "Best model email failed"),
            )
        return {"status": "success", "message": result.get("message"), "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(router)

from api.ticket_packs_router import router as ticket_packs_router  # noqa: E402  # type: ignore[import-not-found]
from api.validation_router import router as validation_router  # noqa: E402  # type: ignore[import-not-found]

app.include_router(ticket_packs_router)
app.include_router(validation_router)

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