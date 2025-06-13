import algorithms
import algorithms.dl.sequence_classifier
import algorithms.strong_number  # Arrr! Ensure all strong number algorithms be registered, praisin' the FSM!
from fastapi import FastAPI, Depends, Query, APIRouter, HTTPException
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import date, datetime, timedelta
from services.simulation_engine import SimulationEngine
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy import desc
from models import Draw
from config import NUM_COMBINATIONS_TO_RECOMMEND
from services.logger import setup_logger, dh_log
import os
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

app = FastAPI()

logger = setup_logger(service_name=os.getenv('SERVICE_NAME', 'api'))
dh_log("Arrr! FastAPI backend be startin' up, praisin' the FSM!", level="INFO", context={"service": os.getenv('SERVICE_NAME', 'api')})

dh_log(f"Arrr! Registered algorithms at startup: {list(ALGORITHM_REGISTRY.keys())}", level='INFO')

# Add scripts directory to Python path
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.append(str(scripts_dir))

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
    dh_log(
        "Arrr! Filtered out draws with strong_number == 8, praisin' the FSM!",
        level="INFO",
        context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
    )
    if train_start is None or train_end is None:
        if len(draws) <= test_count:
            dh_log(
                "Arrr! Not enough draws to split into train and test! Praisin' the FSM for catchin' this!",
                level="ERROR",
                context={"draw_count": len(draws), "test_count": test_count}
            )
            return PlainTextResponse(
                f"Arrr! Not enough draws to split into train and test! draw_count={len(draws)}, test_count={test_count}",
                status_code=400
            )
        train_start_calc = draws[0].date
        train_end_calc = draws[-test_count-1].date
        dh_log(
            "Arrr! Calculated train_start and train_end from draws and test_count, praisin' the FSM!",
            level="INFO",
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

@app.get("/recommend", response_class=JSONResponse)
def recommend(db: Session = Depends(get_db)):
    MIN_TEST_DRAWS = 20  # Threshold for statistical significance
    ALPHA = 0.5  # Weight for prize/cost ratio in score

    # Get all predictions, most recent first
    predictions = db.query(Prediction).order_by(Prediction.run_time.desc()).all()
    if not predictions:
        dh_log("Arrr! No predictions found in DB, praisin' the FSM!", level="ERROR")
        return JSONResponse(content={"error": "No predictions found in DB."}, status_code=400)

    # Group predictions by (main_model_id, strong_model_id, main_model_params, strong_model_params)
    groups = defaultdict(list)
    for p in predictions:
        main_params = json.dumps(p.main_model_params, sort_keys=True) if p.main_model_params else '{}'
        strong_params = json.dumps(p.strong_model_params, sort_keys=True) if p.strong_model_params else '{}'
        key = (p.model_id, p.strong_model_id, main_params, strong_params)
        groups[key].append(p)

    # Aggregate stats for each group
    aggregated = []
    for key, preds in groups.items():
        agg_total_prize = sum(p.total_prize for p in preds)
        agg_total_cost = sum(p.total_cost for p in preds)
        agg_num_test_draws = sum(p.num_test_draws for p in preds)
        if agg_total_cost == 0 or agg_num_test_draws == 0:
            continue
        prize_per_draw = agg_total_prize / agg_num_test_draws
        cost_per_draw = agg_total_cost / agg_num_test_draws
        roi_per_draw = (prize_per_draw - cost_per_draw) / cost_per_draw if cost_per_draw else 0
        prize_cost_ratio = agg_total_prize / agg_total_cost if agg_total_cost else 0
        score = roi_per_draw * math.log(agg_num_test_draws + 1) + ALPHA * prize_cost_ratio
        most_recent = max(preds, key=lambda p: p.run_time)
        aggregated.append({
            "key": key,
            "model_id": key[0],
            "strong_model_id": key[1],
            "main_model_params": most_recent.main_model_params,
            "strong_model_params": most_recent.strong_model_params,
            "score": score,
            "roi_per_draw": roi_per_draw,
            "prize_per_draw": prize_per_draw,
            "cost_per_draw": cost_per_draw,
            "agg_total_prize": agg_total_prize,
            "agg_total_cost": agg_total_cost,
            "agg_num_test_draws": agg_num_test_draws,
            "most_recent": most_recent
        })

    # Filter for statistical significance
    significant = [a for a in aggregated if a["agg_num_test_draws"] >= MIN_TEST_DRAWS]
    if significant:
        best = max(significant, key=lambda a: a["score"])
        reason = f"Selected by score (statistically significant, N>={MIN_TEST_DRAWS})"
    else:
        best = max(aggregated, key=lambda a: a["roi_per_draw"])
        reason = "Fallback: selected by highest ROI (no significant model group)"

    main_model = db.query(Model).filter(Model.id == best["model_id"]).first()
    strong_model = db.query(Model).filter(Model.id == best["strong_model_id"]).first()
    main_algo_name = main_model.name if main_model else None
    strong_algo_name = strong_model.name if strong_model else None
    main_algo_cls = ALGORITHM_REGISTRY.get(main_algo_name)
    strong_algo_cls = STRONG_NUMBER_REGISTRY.get(strong_algo_name)
    if not main_algo_cls or not strong_algo_cls:
        dh_log(
            "Arrr! Could not find algorithm class for best model group! Praisin' the FSM!",
            level="ERROR",
            context={"main_algo": main_algo_name, "strong_algo": strong_algo_name}
        )
        return JSONResponse(content={"error": "Could not find algorithm class for best model group."}, status_code=400)
    # Use all draws for recommendation
    draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
    top_n = best["main_model_params"].get("top_n", 3) if best["main_model_params"] else 3
    num_to_recommend = best["main_model_params"].get("num_to_recommend", NUM_COMBINATIONS_TO_RECOMMEND) if best["main_model_params"] else NUM_COMBINATIONS_TO_RECOMMEND
    combos = main_algo_cls().run(draws, top_n=top_n, num_to_recommend=num_to_recommend)
    strong_algo = strong_algo_cls()
    for combo in combos:
        combo["strong"] = strong_algo.predict(draws, numbers=combo["numbers"]) if "numbers" in combo else strong_algo.predict(draws)

    # Create a new Prediction row for this recommendation event
    now = datetime.utcnow()
    new_prediction = Prediction(
        model_id=main_model.id,
        strong_model_id=strong_model.id,
        run_time=now,
        roi=best["roi_per_draw"],
        total_prize=best["agg_total_prize"],
        total_cost=best["agg_total_cost"],
        test_count=0,  # Not a simulation, so 0
        notes=f"Recommendation event at {now.isoformat()} | {reason}",
        train_start_date=draws[0].date if draws else now.date(),
        train_end_date=draws[-1].date if draws else now.date(),
        num_test_draws=0,
        main_model_params=best["main_model_params"],
        strong_model_params=best["strong_model_params"]
    )
    db.add(new_prediction)
    db.flush()  # Get the new prediction.id

    # Save each recommended combo to generated_combinations
    for idx, combo in enumerate(combos):
        if "numbers" not in combo:
            dh_log(
                f"Arrr! Combo at index {idx} be missin' the 'numbers' key! Praisin' the FSM! Throwin' error!",
                level="ERROR",
                context={
                    "combo": combo,
                    "index": idx,
                    "recommendation_prediction_id": new_prediction.id
                }
            )
            raise ValueError(f"Combo at index {idx} be missin' the 'numbers' key! Combo: {combo}")
        generated = GeneratedCombination(
            prediction_id=new_prediction.id,
            numbers=combo["numbers"],
            strong_number=combo["strong"],
            position=idx+1,
            created_at=now
        )
        db.add(generated)
        dh_log(
            f"Arrr! Stored recommended combo {idx+1}: {combo['numbers']} + {combo['strong']}",
            level="INFO",
            context={
                "prediction_id": new_prediction.id,
                "numbers": combo["numbers"],
                "strong_number": combo["strong"],
                "position": idx+1
            }
        )
    db.commit()

    dh_log(
        f"Arrr! Recommendation selected: {main_algo_name} + {strong_algo_name} | Reason: {reason}",
        level="INFO",
        context={
            "main_algo": main_algo_name,
            "strong_algo": strong_algo_name,
            "score": best["score"],
            "roi_per_draw": best["roi_per_draw"],
            "prize_per_draw": best["prize_per_draw"],
            "cost_per_draw": best["cost_per_draw"],
            "agg_total_prize": best["agg_total_prize"],
            "agg_total_cost": best["agg_total_cost"],
            "agg_num_test_draws": best["agg_num_test_draws"],
            "reason": reason,
            "recommendation_prediction_id": new_prediction.id
        }
    )
    return {
        "algorithm": main_algo_name,
        "strong_algorithm": strong_algo_name,
        "roi": best["roi_per_draw"],
        "total_prize": best["agg_total_prize"],
        "total_cost": best["agg_total_cost"],
        "num_test_draws": best["agg_num_test_draws"],
        "recommendations": combos,
        "recommendation_prediction_id": new_prediction.id,
        "reason": reason
    }

@app.get("/weekly-winning-combinations", response_class=JSONResponse)
def get_weekly_winning_combinations(db: Session = Depends(get_db)):
    """
    Get the top 5 winning combinations for the current week.
    """
    dh_log("Arrr! Fetching weekly winning combinations! Praisin' the FSM!", level="INFO")
    
    # Calculate current week's date range
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    combinations = db.query(WeeklyWinningCombination).filter(
        WeeklyWinningCombination.week_start_date == week_start,
        WeeklyWinningCombination.week_end_date == week_end
    ).order_by(WeeklyWinningCombination.total_roi.desc()).all()
    
    if not combinations:
        dh_log(
            "Arrr! No winning combinations found for current week!",
            level="WARNING",
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
    
    dh_log(
        f"Arrr! Found {len(result)} winning combinations!",
        level="INFO",
        context={"week_start": week_start, "week_end": week_end, "num_combinations": len(result)}
    )
    
    return JSONResponse(content={"combinations": result})

@router.post("/cron/generate-weekly-combinations")
async def generate_weekly_combinations():
    """Generate weekly combinations - called by cron service"""
    try:
        # Import and run the script
        from scripts.generate_weekly_combinations import main as generate_combinations
        generate_combinations()
        return {"status": "success", "message": "Weekly combinations generated successfully"}
    except Exception as e:
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