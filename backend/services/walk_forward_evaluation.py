"""Expanding-window walk-forward evaluation — writes evaluation_tickets and strategy_summaries."""

from __future__ import annotations

import datetime
import random
from typing import Any, Iterable

from sqlalchemy.orm import Session

from algorithms import register_algorithms
from algorithms.base import ALGORITHM_REGISTRY
from config import (
    BACKEND_DIR,
    LINES_PER_DRAW,
    WALK_FORWARD_DEFAULT_STRONG,
    WALK_FORWARD_MIN_TRAINING_DRAWS,
    WALK_FORWARD_RANDOM_BOOTSTRAP_SAMPLES,
    WALK_FORWARD_MIN_DRAWS_FOR_EDGE,
    WALK_FORWARD_RANDOM_PERCENTILE_HIGH,
    WALK_FORWARD_RANDOM_PERCENTILE_LOW,
)
from logger import logger
from models import Draw
from services.pais_draw_rules import CURRENT_REGIME_START
from models.evaluation import EvaluationTicket, StrategySummary
from services.algorithm_runner import run_strategy_on_draws
from services.draw_prize import calculate_prize, draw_has_prize_data, draw_ticket_cost
from services.ticket_validator import TicketValidationError, count_hits
from services.walk_forward_stats import (
    bootstrap_roi_from_steps,
    has_predictive_edge,
    make_strategy_id,
    percentile_rank,
    quantile,
    summarize_draw_series,
)

register_algorithms()

DL_PREFIX = "sequence_lstm"


def get_git_sha() -> str:
    from services.git_sha import get_git_sha as _sha

    return _sha()


def iter_strategy_pairs(include_dl: bool = True) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for main in sorted(ALGORITHM_REGISTRY.keys()):
        if not include_dl and main.startswith(DL_PREFIX):
            continue
        pairs.append((main, WALK_FORWARD_DEFAULT_STRONG))
    pairs.append(("uniform_random", "random"))
    return pairs


class WalkForwardEvaluationService:
    def __init__(self, db: Session, rng: random.Random | None = None):
        self.db = db
        self.rng = rng or random.Random(42)

    def refresh_all(
        self,
        *,
        min_training: int | None = None,
        include_dl: bool = True,
        algorithm_filter: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        min_training = min_training or WALK_FORWARD_MIN_TRAINING_DRAWS
        git_sha = get_git_sha()
        draws = (
            self.db.query(Draw)
            .filter(Draw.date >= CURRENT_REGIME_START)
            .order_by(Draw.date.asc())
            .all()
        )
        if len(draws) <= min_training:
            msg = f"Need more than {min_training} draws; have {len(draws)}"
            logger.error(msg)
            return {"success": False, "message": msg}

        self.db.query(EvaluationTicket).delete()
        self.db.query(StrategySummary).delete()
        self.db.commit()

        pairs = iter_strategy_pairs(include_dl=include_dl)
        if algorithm_filter:
            allowed = set(algorithm_filter)
            pairs = [(m, s) for m, s in pairs if m in allowed]

        per_strategy_steps: dict[str, dict[str, list]] = {}
        errors: list[dict[str, str]] = []

        for main_algo, strong_algo in pairs:
            sid = make_strategy_id(main_algo, strong_algo)
            per_strategy_steps[sid] = {
                "nets": [],
                "costs": [],
                "line_payouts": [],
                "hit3": [],
                "strong_hit": [],
            }
            step_seed = self.rng.randint(1, 2_000_000_000)
            step_rng = random.Random(step_seed)

            for i in range(min_training, len(draws)):
                target = draws[i]
                if not draw_has_prize_data(target):
                    continue
                train = draws[:i]
                as_of = train[-1].date
                try:
                    lines, params = run_strategy_on_draws(
                        train_draws=train,
                        main_algo=main_algo,
                        strong_algo=strong_algo,
                        as_of_date=as_of,
                        rng=step_rng,
                        db=self.db if main_algo.startswith(DL_PREFIX) else None,
                    )
                except (TicketValidationError, ValueError, RuntimeError) as exc:
                    errors.append(
                        {"strategy_id": sid, "draw_date": str(target.date), "error": str(exc)}
                    )
                    continue
                except Exception as exc:
                    logger.error(
                        "Arrr! Walk-forward step failed",
                        context={
                            "strategy_id": sid,
                            "draw": str(target.date),
                            "error": str(exc),
                        },
                    )
                    errors.append(
                        {"strategy_id": sid, "draw_date": str(target.date), "error": str(exc)}
                    )
                    continue

                draw_net = 0.0
                draw_cost = 0.0
                now = datetime.datetime.now(datetime.timezone.utc)
                for idx, line in enumerate(lines):
                    hits = count_hits(line["numbers"], target.numbers)
                    strong_hit = int(line["strong"]) == int(target.strong_number)
                    prize = calculate_prize(target, hits, strong_hit)
                    if prize is None:
                        continue
                    line_cost = draw_ticket_cost(target)
                    net = float(prize) - line_cost
                    draw_net += net
                    draw_cost += line_cost
                    per_strategy_steps[sid]["line_payouts"].append(float(prize))
                    per_strategy_steps[sid]["hit3"].append(hits >= 3)
                    self.db.add(
                        EvaluationTicket(
                            strategy_id=sid,
                            algorithm_version=main_algo,
                            strong_algorithm_version=strong_algo,
                            git_sha=git_sha,
                            params=params,
                            seed=step_seed,
                            training_cutoff=as_of,
                            draw_id=target.id,
                            line_index=idx + 1,
                            numbers=list(line["numbers"]),
                            strong_number=int(line["strong"]),
                            payout_ils=prize,
                            cost_ils=line_cost,
                            net_ils=net,
                            hits=hits,
                            strong_hit=strong_hit,
                            created_at=now,
                        )
                    )
                if draw_cost > 0:
                    per_strategy_steps[sid]["nets"].append(draw_net)
                    per_strategy_steps[sid]["costs"].append(draw_cost)
                    per_strategy_steps[sid]["strong_hit"].append(
                        any(int(ln["strong"]) == int(target.strong_number) for ln in lines)
                    )

            self.db.commit()
            logger.info(
                "Arrr! Walk-forward finished strategy",
                context={"strategy_id": sid, "steps": len(per_strategy_steps[sid]["nets"])},
            )

        control_id = make_strategy_id("uniform_random", "random")
        control_steps = per_strategy_steps.get(control_id, {"nets": [], "costs": []})
        bootstrap_rois = bootstrap_roi_from_steps(
            control_steps["nets"],
            control_steps["costs"],
            samples=WALK_FORWARD_RANDOM_BOOTSTRAP_SAMPLES,
            rng_seed=99,
        )
        baseline_median = quantile(bootstrap_rois, 0.5)
        baseline_p5 = quantile(bootstrap_rois, 0.05)
        baseline_p95 = quantile(bootstrap_rois, 0.95)

        summaries_written = 0
        for main_algo, strong_algo in pairs:
            sid = make_strategy_id(main_algo, strong_algo)
            steps = per_strategy_steps[sid]
            stats = summarize_draw_series(
                steps["nets"],
                steps["costs"],
                steps["line_payouts"],
                steps["hit3"],
                steps["strong_hit"],
            )
            roi = stats["roi"]
            pct = percentile_rank(roi, bootstrap_rois) if bootstrap_rois else 50.0
            edge = has_predictive_edge(
                int(stats["independent_draw_count"]),
                pct,
                min_draws=WALK_FORWARD_MIN_DRAWS_FOR_EDGE,
                band_low=WALK_FORWARD_RANDOM_PERCENTILE_LOW,
                band_high=WALK_FORWARD_RANDOM_PERCENTILE_HIGH,
            )
            self.db.add(
                StrategySummary(
                    strategy_id=sid,
                    algorithm_version=main_algo,
                    strong_algorithm_version=strong_algo,
                    git_sha=git_sha,
                    params=None,
                    roi=roi,
                    mean_payout_per_line=stats["mean_payout_per_line"],
                    median_payout_per_line=stats["median_payout_per_line"],
                    hit_rate_3plus=stats["hit_rate_3plus"],
                    strong_accuracy=stats["strong_accuracy"],
                    max_drawdown=stats["max_drawdown"],
                    variance_net=stats["variance_net"],
                    random_percentile=pct,
                    bootstrap_roi_p5=quantile(bootstrap_rois, 0.05),
                    bootstrap_roi_p95=quantile(bootstrap_rois, 0.95),
                    random_baseline_median_roi=baseline_median,
                    random_baseline_p5=baseline_p5,
                    random_baseline_p95=baseline_p95,
                    independent_draw_count=int(stats["independent_draw_count"]),
                    has_predictive_edge=edge,
                    updated_at=datetime.datetime.now(datetime.timezone.utc),
                )
            )
            summaries_written += 1

        self.db.commit()
        return {
            "success": True,
            "strategies": summaries_written,
            "min_training": min_training,
            "errors": errors[:50],
            "error_count": len(errors),
        }
