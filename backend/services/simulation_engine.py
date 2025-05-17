from sqlalchemy.orm import Session
from typing import Any
from models import Draw, Model, ModelType, Prediction, GeneratedCombination
from algorithms.base import ALGORITHM_REGISTRY
from config import TICKET_COST_PER_TABLE, PRIZE_TABLE, NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from services.logger import dh_log
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from sqlalchemy.exc import NoResultFound

def calculate_roi_with_tax(prizes, total_cost):
    """
    Calculate ROI with tax applied to prizes over 30,000.
    Args:
        prizes (list of float): List of individual prize amounts.
        total_cost (float): Total cost spent.
    Returns:
        float: ROI value.
    """
    taxed_prizes = []
    for prize in prizes:
        if prize > 30000:
            taxed_prizes.append(prize * 0.65)  # 35% tax
        else:
            taxed_prizes.append(prize)
    all_prizes = sum(taxed_prizes)
    if total_cost == 0:
        return 0
    return (all_prizes - total_cost) / total_cost

class SimulationEngine:
    def __init__(self, db: Session):
        self.db = db

    def run_comparison(self, train_start, train_end, test_count=12, top_n=3, algo_names=None, strong_algo_names=None):
        """
        For each algorithm version and each strong number model:
        - Use draws from train_start to train_end (inclusive) as training data
        - Predict for the next test_count draws
        - Compare predictions to actual draws
        - Return summary per (main, strong) algorithm pair
        """
        logger = logging.getLogger("simulation_engine")
        logger.info(f"[FSM DEBUG] Starting run_comparison: train_start={train_start}, train_end={train_end}, test_count={test_count}, top_n={top_n}, algo_names={algo_names}, strong_algo_names={strong_algo_names}")
        t_start = time.time()

        # --- FSM DEBUG: List all available algorithms ---
        dh_log(f"Arrr! Available algorithms in registry: {list(ALGORITHM_REGISTRY.keys())}", level="INFO")
        dh_log(f"Arrr! Available strong number algorithms: {list(STRONG_NUMBER_REGISTRY.keys())}", level="INFO")
        # --- Simple in-memory cache (per process) ---
        if not hasattr(self, '_cache'):
            self._cache = {}
        cache_key = (str(train_start), str(train_end), test_count, top_n, tuple(sorted(algo_names)) if algo_names else None, tuple(sorted(strong_algo_names)) if strong_algo_names else None)
        if cache_key in self._cache:
            dh_log(f"[FSM DEBUG] Returning cached result for key: {cache_key}", level="INFO")
            return self._cache[cache_key]
        # --- End cache block ---

        draws = self.db.query(Draw).filter(Draw.date >= train_start, Draw.date <= train_end).order_by(Draw.date).all()
        dh_log(f"[FSM DEBUG] Loaded {len(draws)} training draws in {time.time() - t_start:.2f}s", level="INFO")
        t_test = time.time()
        test_draws = self.db.query(Draw).filter(Draw.date > train_end).order_by(Draw.date).limit(test_count).all()
        dh_log(f"[FSM DEBUG] Loaded {len(test_draws)} test draws in {time.time() - t_test:.2f}s", level="INFO")
        results = {}
        algos_to_run = ALGORITHM_REGISTRY.items() if not algo_names else [
            (k, v) for k, v in ALGORITHM_REGISTRY.items() if k in algo_names
        ]
        strong_algos_to_run = STRONG_NUMBER_REGISTRY.items() if not strong_algo_names else [
            (k, v) for k, v in STRONG_NUMBER_REGISTRY.items() if k in strong_algo_names
        ]

        def get_or_create_model(session, name, version, type_, params, model_path=None):
            try:
                return session.query(Model).filter_by(name=name, version=version, type=type_).one()
            except NoResultFound:
                model = Model(name=name, version=version, type=type_, params=params, model_path=model_path)
                session.add(model)
                session.commit()
                return model

        def run_algo_pair(main_version, algo_cls, strong_version, strong_cls):
            dh_log(f"[FSM DEBUG] Running algorithm: {main_version} + strong: {strong_version}", level="INFO")
            t_algo = time.time()
            algo = algo_cls()
            strong_algo = strong_cls()
            date_summaries = []
            all_prizes = 0
            total_tickets = 0
            for i, test_draw in enumerate(test_draws):
                t_draw = time.time()
                dh_log(f"[FSM DEBUG]   Test draw {i+1}/{len(test_draws)}: {test_draw.date}", level="INFO")
                available_draws = [d for d in draws if d.date < test_draw.date]
                dh_log(f"[FSM DEBUG]   Available draws for test draw: {len(available_draws)}", level="INFO")
                t_run = time.time()
                combos = algo.run(
                    available_draws,
                    top_n=top_n,
                    num_for_analysis=NUM_COMBINATIONS_FOR_ANALYSIS,
                    num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND
                )
                # Inject strong number using the selected model, avoiding duplicates
                for combo in combos:
                    combo["strong_number"] = strong_algo.predict(available_draws, numbers=combo["numbers"])
                dh_log(f"[FSM DEBUG]   Algorithm run() for main='{main_version}', strong='{strong_version}' took {time.time() - t_run:.2f}s and returned {len(combos)} combos", level="INFO")
                combo_results = []
                for combo in combos:
                    hits = sum([n in test_draw.numbers for n in combo["numbers"]])
                    strong_hit = (combo["strong_number"] == test_draw.strong_number)
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
                dh_log(f"[FSM DEBUG]   Test draw {i+1} for main='{main_version}', strong='{strong_version}' processed in {time.time() - t_draw:.2f}s", level="INFO")
            total_cost = total_tickets * TICKET_COST_PER_TABLE
            roi = calculate_roi_with_tax([total_prize], total_cost)
            dh_log(f"[FSM DEBUG] Algorithm {main_version} + strong {strong_version} finished in {time.time() - t_algo:.2f}s. Total prize: {all_prizes}, Total cost: {total_cost}, ROI: {roi}", level="INFO")
            # --- Prediction logging ---
            prediction = Prediction(
                model_id=get_or_create_model(self.db, main_version, getattr(algo, 'version', 'v1'), ModelType.main, getattr(algo, 'params', {})).id,
                strong_model_id=get_or_create_model(self.db, strong_version, getattr(strong_algo, 'version', 'v1'), ModelType.strong, getattr(strong_algo, 'params', {})).id,
                roi=roi,
                total_prize=all_prizes,
                total_cost=total_cost,
                test_count=len(test_draws),
                notes=f"Sim run for {main_version} + {strong_version}",
                train_start_date=train_start,
                train_end_date=train_end,
                num_test_draws=test_count,
                top_n_per_position=top_n
            )
            self.db.add(prediction)
            self.db.commit()
            # --- GeneratedCombination logging ---
            for d in date_summaries:
                for idx, combo_result in enumerate(d["combos"]):
                    combo = combo_result["combo"]
                    gen_combo = GeneratedCombination(
                        prediction_id=prediction.id,
                        numbers=combo["numbers"],
                        strong_number=combo["strong_number"],
                        position=idx + 1  # 1-based index for position
                    )
                    self.db.add(gen_combo)
            self.db.commit()
            return (main_version, strong_version), {
                "dates": date_summaries,
                "total_prize": all_prizes,
                "total_cost": total_cost,
                "roi": roi
            }

        # Run all pairs in parallel
        with ThreadPoolExecutor() as executor:
            future_to_pair = {
                executor.submit(run_algo_pair, main_version, algo_cls, strong_version, strong_cls): (main_version, strong_version)
                for main_version, algo_cls in algos_to_run
                for strong_version, strong_cls in strong_algos_to_run
            }
            for future in as_completed(future_to_pair):
                pair, result = future.result()
                results[pair] = result

        logger.info(f"[FSM DEBUG] run_comparison finished in {time.time() - t_start:.2f}s")
        self._cache[cache_key] = results
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

    def run_strong_number_comparison(self, train_start, train_end, test_count=12, algo_names=None):
        """
        Compare all strong number algorithms:
        - Use draws from train_start to train_end (inclusive) as training data
        - Predict strong number for the next test_count draws
        - Compare predictions to actual strong numbers
        - Return summary per algorithm version
        """
        logger = logging.getLogger("simulation_engine")
        logger.info(f"[FSM DEBUG] Starting run_strong_number_comparison: train_start={train_start}, train_end={train_end}, test_count={test_count}, algo_names={algo_names}")
        t_start = time.time()
        draws = self.db.query(Draw).filter(Draw.date >= train_start, Draw.date <= train_end).order_by(Draw.date).all()
        test_draws = self.db.query(Draw).filter(Draw.date > train_end).order_by(Draw.date).limit(test_count).all()
        results = {}
        algos_to_run = STRONG_NUMBER_REGISTRY.items() if not algo_names else [
            (k, v) for k, v in STRONG_NUMBER_REGISTRY.items() if k in algo_names
        ]
        for version, algo_cls in algos_to_run:
            logger.info(f"[FSM DEBUG] Running strong number algorithm: {version}")
            algo = algo_cls()
            correct = 0
            total = 0
            predictions = []
            for test_draw in test_draws:
                available_draws = [d for d in draws if d.date < test_draw.date]
                pred = algo.predict(available_draws)
                predictions.append({
                    "date": test_draw.date,
                    "predicted": pred,
                    "actual": test_draw.strong_number,
                    "correct": pred == test_draw.strong_number
                })
                if pred == test_draw.strong_number:
                    correct += 1
                total += 1
            accuracy = correct / total if total else 0
            results[version] = {
                "accuracy": accuracy,
                "predictions": predictions,
                "total": total,
                "correct": correct
            }
            logger.info(f"[FSM DEBUG] Strong number algorithm {version} accuracy: {accuracy:.3f} ({correct}/{total})")
        logger.info(f"[FSM DEBUG] run_strong_number_comparison finished in {time.time() - t_start:.2f}s")
        return results 