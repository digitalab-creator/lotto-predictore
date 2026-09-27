"""Append one walk-forward step after a new draw — without full refresh."""

from __future__ import annotations

import datetime
import random
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from config import WALK_FORWARD_MIN_TRAINING_DRAWS
from logger import logger
from models import Draw
from services.pais_draw_rules import CURRENT_REGIME_START
from models.evaluation import EvaluationTicket, StrategySummary
from services.draw_prize import calculate_prize, draw_has_prize_data, draw_ticket_cost
from services.ticket_validator import TicketValidationError, count_hits
from services.walk_forward_evaluation import (
    WalkForwardEvaluationService,
    get_git_sha,
    iter_strategy_pairs,
)
from services.walk_forward_stats import (
    bootstrap_roi_from_steps,
    has_predictive_edge,
    make_strategy_id,
    percentile_rank,
    quantile,
    summarize_draw_series,
)
from services.algorithm_runner import run_strategy_on_draws
from config import (
    WALK_FORWARD_RANDOM_BOOTSTRAP_SAMPLES,
    WALK_FORWARD_MIN_DRAWS_FOR_EDGE,
    WALK_FORWARD_RANDOM_PERCENTILE_HIGH,
    WALK_FORWARD_RANDOM_PERCENTILE_LOW,
)

DL_PREFIX = "sequence_lstm"


def _steps_from_tickets(db: Session, strategy_id: str) -> dict[str, list]:
    tickets = (
        db.query(EvaluationTicket)
        .filter(EvaluationTicket.strategy_id == strategy_id)
        .order_by(EvaluationTicket.draw_id.asc(), EvaluationTicket.line_index.asc())
        .all()
    )
    per_draw: dict[int, list[EvaluationTicket]] = defaultdict(list)
    for t in tickets:
        per_draw[t.draw_id].append(t)
    nets: list[float] = []
    costs: list[float] = []
    line_payouts: list[float] = []
    hit3: list[bool] = []
    strong_hit: list[bool] = []
    for draw_id in sorted(per_draw.keys()):
        rows = per_draw[draw_id]
        draw_net = sum(float(r.net_ils) for r in rows)
        draw_cost = sum(float(r.cost_ils) for r in rows)
        nets.append(draw_net)
        costs.append(draw_cost)
        for r in rows:
            line_payouts.append(float(r.payout_ils))
            hit3.append(int(r.hits) >= 3)
        strong_hit.append(any(r.strong_hit for r in rows))
    return {
        "nets": nets,
        "costs": costs,
        "line_payouts": line_payouts,
        "hit3": hit3,
        "strong_hit": strong_hit,
    }


def rebuild_strategy_summaries(db: Session, *, include_dl: bool = False) -> int:
    pairs = iter_strategy_pairs(include_dl=include_dl)
    control_id = make_strategy_id("uniform_random", "random")
    control_steps = _steps_from_tickets(db, control_id)
    bootstrap_rois = bootstrap_roi_from_steps(
        control_steps["nets"],
        control_steps["costs"],
        samples=WALK_FORWARD_RANDOM_BOOTSTRAP_SAMPLES,
        rng_seed=99,
    )
    baseline_median = quantile(bootstrap_rois, 0.5)
    baseline_p5 = quantile(bootstrap_rois, 0.05)
    baseline_p95 = quantile(bootstrap_rois, 0.95)
    git_sha = get_git_sha()
    db.query(StrategySummary).delete()
    written = 0
    for main_algo, strong_algo in pairs:
        sid = make_strategy_id(main_algo, strong_algo)
        steps = _steps_from_tickets(db, sid)
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
        db.add(
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
        written += 1
    db.commit()
    return written


def append_walk_forward_for_latest_draw(
    db: Session,
    *,
    include_dl: bool = False,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    draws = (
        db.query(Draw)
        .filter(Draw.date >= CURRENT_REGIME_START)
        .order_by(Draw.date.asc())
        .all()
    )
    min_training = WALK_FORWARD_MIN_TRAINING_DRAWS
    if len(draws) <= min_training:
        return {"success": False, "skipped": True, "reason": "insufficient_draws"}

    target = draws[-1]
    if not draw_has_prize_data(target):
        return {"success": False, "skipped": True, "reason": "no_prize_data"}

    exists = (
        db.query(EvaluationTicket.id)
        .filter(EvaluationTicket.draw_id == target.id)
        .first()
    )
    if exists:
        return {"success": True, "skipped": True, "reason": "already_evaluated"}

    train = draws[:-1]
    as_of = train[-1].date
    rng = rng or random.Random(42)
    git_sha = get_git_sha()
    errors: list[dict[str, str]] = []
    wrote = 0

    for main_algo, strong_algo in iter_strategy_pairs(include_dl=include_dl):
        sid = make_strategy_id(main_algo, strong_algo)
        step_seed = rng.randint(1, 2_000_000_000)
        step_rng = random.Random(step_seed)
        try:
            lines, params = run_strategy_on_draws(
                train_draws=train,
                main_algo=main_algo,
                strong_algo=strong_algo,
                as_of_date=as_of,
                rng=step_rng,
                db=db if main_algo.startswith(DL_PREFIX) else None,
            )
        except (TicketValidationError, ValueError, RuntimeError) as exc:
            errors.append({"strategy_id": sid, "error": str(exc)})
            continue

        now = datetime.datetime.now(datetime.timezone.utc)
        for idx, line in enumerate(lines):
            hits = count_hits(line["numbers"], target.numbers)
            strong_hit = int(line["strong"]) == int(target.strong_number)
            prize = calculate_prize(target, hits, strong_hit)
            if prize is None:
                continue
            line_cost = draw_ticket_cost(target)
            net = float(prize) - line_cost
            db.add(
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
            wrote += 1
    db.commit()
    summaries = rebuild_strategy_summaries(db, include_dl=include_dl)
    logger.info(
        "Arrr! Walk-forward incremental step complete",
        context={"draw_id": target.id, "tickets": wrote, "summaries": summaries},
    )
    return {
        "success": True,
        "draw_id": target.id,
        "tickets_written": wrote,
        "summaries": summaries,
        "errors": errors[:20],
    }


def ensure_walk_forward_bootstrapped(db: Session) -> dict[str, Any]:
    """If scoreboard empty, run a full refresh (skip DL on cron path)."""
    if db.query(StrategySummary).count() > 0:
        return {"bootstrapped": False}
    logger.info("Arrr! Empty scoreboard — one-time full walk-forward refresh")
    service = WalkForwardEvaluationService(db)
    return service.refresh_all(include_dl=False)
