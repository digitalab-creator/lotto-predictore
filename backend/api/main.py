from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import date
from services.simulation_engine import SimulationEngine
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy import desc
from models import Draw
from config import NUM_COMBINATIONS_TO_RECOMMEND

app = FastAPI()

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
    top_n: int = Query(3, description="Top N frequent numbers per position"),
    db: Session = Depends(get_db)
):
    engine = SimulationEngine(db)
    results = engine.run_comparison(train_start, train_end, test_count, top_n)
    return results 

@app.get("/simulate/table", response_class=PlainTextResponse)
def simulate_table(
    train_start: date = Query(..., description="Start date for training data (YYYY-MM-DD)"),
    train_end: date = Query(..., description="End date for training data (YYYY-MM-DD)"),
    test_count: int = Query(4, description="How many draws to test after train_end"),
    top_n: int = Query(3, description="Top N frequent numbers per position"),
    db: Session = Depends(get_db)
):
    engine = SimulationEngine(db)
    results = engine.run_comparison(train_start, train_end, test_count, top_n)
    # Generate markdown table
    try:
        from tabulate import tabulate
        use_tabulate = True
    except ImportError:
        use_tabulate = False
    output = []
    for version, res in results.items():
        output.append(f"\nAlgorithm: {version}")
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
    for algo_version, res in results.items():
        combo_hit_stats = [[] for _ in range(8)]
        for date in res["dates"]:
            for idx, combo_result in enumerate(date["combos"]):
                if idx < 8:
                    combo_hit_stats[idx].append(combo_result["hits"])
        output.append(f"Algorithm: {algo_version}")
        for idx, hits in enumerate(combo_hit_stats):
            avg_hits = sum(hits) / len(hits) if hits else 0
            output.append(f"  Combo #{idx+1}: Avg Hits = {avg_hits:.2f} (n={len(hits)})")
    return "\n".join(output) 

@app.get("/recommend", response_class=JSONResponse)
def recommend(db: Session = Depends(get_db)):
    # Get all draws, sorted by date
    draws = db.query(Draw).order_by(Draw.date).all()
    if len(draws) < 20:
        return JSONResponse(content={"error": "Not enough draws in database for recommendation."}, status_code=400)
    # Split into train and test
    train_draws = draws[:-12]
    test_draws = draws[-12:]
    train_start = train_draws[0].date
    train_end = train_draws[-1].date
    test_count = 12
    top_n = 3
    engine = SimulationEngine(db)
    results = engine.run_comparison(train_start, train_end, test_count, top_n)
    # Find the algorithm with the highest ROI
    best_algo = None
    best_roi = float('-inf')
    for algo, res in results.items():
        if res["roi"] > best_roi:
            best_algo = algo
            best_roi = res["roi"]
    if not best_algo:
        return JSONResponse(content={"error": "No algorithm produced results."}, status_code=400)
    # Re-run the best algorithm on all data to get the 8 combos for the next draw
    from algorithms import ALGORITHM_REGISTRY
    algo_cls = ALGORITHM_REGISTRY[best_algo]
    all_draws = draws
    combos = algo_cls().run(all_draws, top_n=top_n, num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND)
    return {"algorithm": best_algo, "roi": best_roi, "recommendations": combos} 