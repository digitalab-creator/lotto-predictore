from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import date
from services.simulation_engine import SimulationEngine
from models import Draw
from logger import logger

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/simulate")
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

@router.get("/simulate/table", response_class=PlainTextResponse)
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