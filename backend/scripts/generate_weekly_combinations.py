import sys
import os
import datetime
from sqlalchemy.orm import Session
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.base import SessionLocal
from models import Draw, GeneratedCombination, Prediction
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import NUM_COMBINATIONS_TO_RECOMMEND
from services.logger import dh_log

def main():
    dh_log("Arrr! Starting weekly combination generation, praisin' the FSM!", level="INFO")
    db = SessionLocal()
    try:
        draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
        filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
        dh_log(
            "Arrr! Filtered out draws with strong_number == 8 for weekly generation, praisin' the FSM!",
            level="INFO",
            context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
        )
        if len(draws) < 20:
            dh_log("Not enough draws in database for recommendation.", level="ERROR")
            return
        train_draws = draws[:-12]
        test_draws = draws[-12:]
        train_start = train_draws[0].date
        train_end = train_draws[-1].date
        test_count = 12
        # Find best algorithm pair by ROI
        from services.simulation_engine import SimulationEngine
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
            dh_log(f"Running {algo_name} with top_n={top_n}", level="INFO")
            try:
                res = engine.run_comparison(train_start, train_end, test_count, top_n, algo_names=[algo_name])
                for (main_algo, strong_algo), r in res.items():
                    results[(main_algo, strong_algo)] = r
                    if r["roi"] > best_roi:
                        best_pair = (main_algo, strong_algo)
                        best_roi = r["roi"]
            except Exception as e:
                dh_log(f"[FSM ERROR] Skipping {algo_name} due to error: {e}", level="ERROR")
        if not best_pair:
            dh_log("No algorithm produced results.", level="ERROR")
            return
        main_algo_cls = ALGORITHM_REGISTRY[best_pair[0]]
        # Use correct top_n for the best algorithm
        if best_pair[0] == 'top_6_overall_frequent_v2':
            top_n = 10
        else:
            top_n = 3
        strong_algo_cls = STRONG_NUMBER_REGISTRY[best_pair[1]]
        all_draws = draws
        combos = main_algo_cls().run(all_draws, top_n=top_n, num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND)
        strong_algo = strong_algo_cls()
        strong_number = strong_algo.predict(all_draws)
        now = datetime.datetime.utcnow()
        # Store in DB
        for idx, combo in enumerate(combos):
            generated = GeneratedCombination(
                prediction_id=None,  # If you want to link to a prediction, set it here
                numbers=combo["numbers"],
                strong_number=strong_number,
                position=idx+1,
                created_at=now
            )
            db.add(generated)
            dh_log(f"Stored combo {idx+1}: {combo['numbers']} + {strong_number}", level="INFO")
        db.commit()
        dh_log(f"Arrr! Stored {len(combos)} combinations for the next draw, praisin' the FSM!", level="INFO")
    except Exception as e:
        dh_log(f"[FSM ERROR] Exception in weekly generation: {e}", level="ERROR")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 