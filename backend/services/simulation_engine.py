from sqlalchemy.orm import Session
from typing import Any
from models import Draw
from algorithms.base import ALGORITHM_REGISTRY
from config import TICKET_COST_PER_TABLE, PRIZE_TABLE, NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND
import time

class SimulationEngine:
    def __init__(self, db: Session):
        self.db = db

    def run_comparison(self, train_start, train_end, test_count=12, top_n=3):
        """
        For each algorithm version:
        - Use draws from train_start to train_end (inclusive) as training data
        - Predict for the next test_count draws
        - Compare predictions to actual draws
        - Return summary per algorithm version
        """
        # Get training draws
        draws = self.db.query(Draw).filter(Draw.date >= train_start, Draw.date <= train_end).order_by(Draw.date).all()
        # Get test draws (the next N after train_end)
        test_draws = self.db.query(Draw).filter(Draw.date > train_end).order_by(Draw.date).limit(test_count).all()
        results = {}
        for version, algo_cls in ALGORITHM_REGISTRY.items():
            print(f"[FSM DEBUG] Running {version}...")
            t0 = time.time()
            algo = algo_cls()
            date_summaries = []
            all_prizes = 0
            total_tickets = 0
            for i, test_draw in enumerate(test_draws):
                print(f"[FSM DEBUG]   Test draw {i+1}/{len(test_draws)}: {test_draw.date}")
                # Use only draws up to (but not including) this test draw
                available_draws = [d for d in draws if d.date < test_draw.date]
                combos = algo.run(
                    available_draws,
                    top_n=top_n,
                    num_for_analysis=NUM_COMBINATIONS_FOR_ANALYSIS,
                    num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND
                )
                combo_results = []
                for combo in combos:
                    hits = sum([n in test_draw.numbers for n in combo["numbers"]])
                    strong_hit = (combo["strong"] == test_draw.strong_number)
                    prize = self._calculate_prize(hits, strong_hit)
                    combo_results.append({
                        "combo": combo,
                        "hits": hits,
                        "strong_hit": strong_hit,
                        "prize": prize
                    })
                max_hits = max((c["hits"] for c in combo_results), default=0)
                any_strong_hit = any(c["strong_hit"] for c in combo_results)
                total_prize = sum(c["prize"] for c in combo_results)
                date_summaries.append({
                    "test_draw_date": test_draw.date,
                    "actual_numbers": test_draw.numbers,
                    "actual_strong": test_draw.strong_number,
                    "combos": combo_results,
                    "max_hits": max_hits,
                    "any_strong_hit": any_strong_hit,
                    "total_prize": total_prize
                })
                all_prizes += total_prize
                total_tickets += len(combos)
            total_cost = total_tickets * TICKET_COST_PER_TABLE
            roi = (all_prizes - total_cost) / total_cost if total_cost else 0
            print(f"[FSM DEBUG] {version} took {time.time() - t0:.2f} seconds")
            results[version] = {
                "dates": date_summaries,
                "total_prize": all_prizes,
                "total_cost": total_cost,
                "roi": roi
            }
        return results

    def _calculate_prize(self, hits, strong_hit):
        # Use the prize table from config, fallback to 0 if not found
        return PRIZE_TABLE.get((hits, strong_hit), 0)

    def print_combo_index_insights(self, results):
        print("\n=== Combo Index Insights (Average Hits per Combo Index) ===")
        for algo_version, res in results.items():
            combo_hit_stats = [[] for _ in range(8)]
            for date in res["dates"]:
                for idx, combo_result in enumerate(date["combos"]):
                    if idx < 8:
                        combo_hit_stats[idx].append(combo_result["hits"])
            print(f"Algorithm: {algo_version}")
            for idx, hits in enumerate(combo_hit_stats):
                avg_hits = sum(hits) / len(hits) if hits else 0
                print(f"  Combo #{idx+1}: Avg Hits = {avg_hits:.2f} (n={len(hits)})")

    def print_table_summary(self, results):
        try:
            from tabulate import tabulate
            use_tabulate = True
        except ImportError:
            use_tabulate = False
        for version, res in results.items():
            print(f"\nAlgorithm: {version}")
            headers = ["Date", "Actual Numbers", "Actual Strong", "Max Hits", "Any Strong Hit", "Total Prize"]
            table = []
            for d in res["dates"]:
                table.append([
                    d["test_draw_date"],
                    d["actual_numbers"],
                    d["actual_strong"],
                    d["max_hits"],
                    d["any_strong_hit"],
                    d["total_prize"]
                ])
            if use_tabulate:
                print(tabulate(table, headers=headers, tablefmt="github"))
            else:
                print(" | ".join(headers))
                for row in table:
                    print(" | ".join(str(x) for x in row))
            print(f"Total Prize: {res['total_prize']}, Total Cost: {res['total_cost']}, ROI: {res['roi']}")
            self.print_combo_index_insights(results) 