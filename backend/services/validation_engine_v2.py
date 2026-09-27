"""Sealed validator. Select on the middle slice. Score the winner once on the last slice."""

from __future__ import annotations

import random
from typing import Any

from config import (
    VALIDATION_BOOTSTRAP_SAMPLES,
    VALIDATION_MIN_SUCCESS_FRACTION,
    VALIDATION_RANDOM_PORTFOLIOS,
    WALK_FORWARD_DEFAULT_STRONG,
)
from logger import logger
from services.algorithm_runner import run_strategy_on_draws
from services.exact_coverage import ANY_PRIZE_PROBABILITY
from services.game_regime import assert_regime_clean, split_regime
from services.pais_draw_rules import CURRENT_REGIME_START
from services.validation_report import build_holdout_report, expected_ticket_payout
from services.validation_stats_v2 import HoldoutAlreadyRan, halves_above_baseline, mean, split_bounds
from services.validation_walk import walk_forward, paired_random_rates
from services.git_sha import get_git_sha
from services.walk_forward_stats import make_strategy_id

_EXCLUDED = {"uniform_random", "diversified_random", "base"}
_HOLDOUT_SEAL = 1


def candidate_main_algorithms() -> list[str]:
    """Cheap registered algorithms. Neural nets and the random null stay out."""
    import algorithms  # noqa: F401  registers the non-neural modules
    from algorithms.base import ALGORITHM_REGISTRY

    names = []
    for name in sorted(ALGORITHM_REGISTRY):
        if name in _EXCLUDED or name.startswith("sequence_lstm"):
            continue
        names.append(name)
    return names


def _producer(main_algo: str, strong_algo: str):
    def produce(train: list[Any]) -> list[dict[str, Any]]:
        if not train:
            raise ValueError("no training draws before this step")
        lines, _params = run_strategy_on_draws(
            train_draws=train,
            main_algo=main_algo,
            strong_algo=strong_algo,
            as_of_date=train[-1].date,
            rng=random.Random(len(train)),
            db=None,
        )
        return lines

    return produce


def load_regime_draws(db: Any) -> list[Any]:
    from models import Draw

    rows = db.query(Draw).filter(Draw.date >= CURRENT_REGIME_START).order_by(Draw.date.asc()).all()
    legal, illegal = split_regime(rows)
    assert_regime_clean(illegal)
    return legal


class ValidationEngineV2:
    def __init__(self, db: Any):
        self.db = db

    def run_select(self) -> dict[str, Any]:
        from models.validation_v2 import ValidationExperiment, ValidationLock

        draws = load_regime_draws(self.db)
        select_start, holdout_start = split_bounds(len(draws))
        strong = WALK_FORWARD_DEFAULT_STRONG
        experiment = ValidationExperiment(
            regime_start=CURRENT_REGIME_START,
            select_start_date=draws[select_start].date,
            holdout_start_date=draws[holdout_start].date,
            holdout_end_date=draws[-1].date,
            draw_count=len(draws),
            git_sha=get_git_sha(),
            status="selecting",
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        logger.info(
            "Validation select started",
            context={
                "experiment_id": experiment.id,
                "draws": len(draws),
                "select_from": str(draws[select_start].date),
                "holdout_from": str(draws[holdout_start].date),
            },
        )

        scores = []
        window = holdout_start - select_start
        for main_algo in candidate_main_algorithms():
            strategy_id = make_strategy_id(main_algo, strong)
            logger.info("Validation candidate", context={"strategy_id": strategy_id})
            walked = walk_forward(
                draws,
                start=select_start,
                end=holdout_start,
                produce_lines=_producer(main_algo, strong),
            )
            self._store_steps(experiment.id, "select", strategy_id, walked.steps)
            success = len(walked.steps)
            if window == 0 or success / window < VALIDATION_MIN_SUCCESS_FRACTION:
                scores.append(
                    {
                        "strategy_id": strategy_id,
                        "disqualified": True,
                        "successes": success,
                        "errors": len(walked.errors),
                    }
                )
                logger.error(
                    "Candidate disqualified",
                    context={"strategy_id": strategy_id, "successes": success, "errors": len(walked.errors)},
                )
                continue
            rates = [step.ticket_rate for step in walked.steps]
            first, second, promoted_halves = halves_above_baseline(rates)
            scores.append(
                {
                    "strategy_id": strategy_id,
                    "main_algorithm": main_algo,
                    "strong_algorithm": strong,
                    "primary_rate": mean(rates),
                    "first_half_rate": first,
                    "second_half_rate": second,
                    "halves_above": promoted_halves,
                    "successes": success,
                    "disqualified": False,
                }
            )

        eligible = [row for row in scores if not row.get("disqualified")]
        if not eligible:
            experiment.status = "no_stable_candidate"
            experiment.refusal_reason = "no candidate scored enough select draws"
            self.db.commit()
            return {"experiment_id": experiment.id, "promoted": False, "verdict": "inconclusive", "scores": scores}

        # Lock the best pack that clears both select halves. A higher rate that
        # fails the second half must not block a stable lower-rate winner.
        promotable = [row for row in eligible if row.get("halves_above")]
        if promotable:
            winner = max(promotable, key=lambda row: row["primary_rate"])
            promoted = True
        else:
            winner = max(eligible, key=lambda row: row["primary_rate"])
            promoted = False
        self.db.add(
            ValidationLock(
                experiment_id=experiment.id,
                main_algorithm=winner["main_algorithm"],
                strong_algorithm=winner["strong_algorithm"],
                strategy_id=winner["strategy_id"],
                primary_rate=winner["primary_rate"],
                first_half_rate=winner["first_half_rate"],
                second_half_rate=winner["second_half_rate"],
                promoted=promoted,
                candidate_scores=scores,
            )
        )
        experiment.status = "locked" if promoted else "no_stable_candidate"
        if not promoted:
            experiment.refusal_reason = "no candidate had both select halves above 4.1751%"
        self.db.commit()
        logger.info(
            "Validation select finished",
            context={"experiment_id": experiment.id, "winner": winner["strategy_id"], "promoted": promoted},
        )
        return {
            "experiment_id": experiment.id,
            "promoted": promoted,
            "verdict": "pending_holdout" if promoted else "inconclusive",
            "winner": winner,
            "baseline": ANY_PRIZE_PROBABILITY,
        }

    def run_holdout(self) -> dict[str, Any]:
        from models.validation_v2 import ValidationExperiment, ValidationHoldoutResult, ValidationLock

        if self.db.query(ValidationHoldoutResult).count():
            raise HoldoutAlreadyRan("A sealed holdout result already exists")
        experiment = (
            self.db.query(ValidationExperiment).order_by(ValidationExperiment.id.desc()).first()
        )
        if experiment is None:
            raise RuntimeError("Run select before holdout")
        lock = (
            self.db.query(ValidationLock).filter(ValidationLock.experiment_id == experiment.id).one_or_none()
        )
        if lock is None or not lock.promoted:
            experiment.status = "no_stable_candidate"
            self.db.commit()
            return {
                "experiment_id": experiment.id,
                "promoted": False,
                "verdict": "inconclusive",
                "reason": "select did not lock a strategy, holdout was not run",
            }

        draws = [
            row
            for row in load_regime_draws(self.db)
            if row.date <= experiment.holdout_end_date
        ]
        holdout_start = next(
            (index for index, row in enumerate(draws) if row.date >= experiment.holdout_start_date),
            None,
        )
        if holdout_start is None:
            raise RuntimeError("Holdout boundary moved after the lock. Refusing to score.")
        walked = walk_forward(
            draws,
            start=holdout_start,
            end=len(draws),
            produce_lines=_producer(lock.main_algorithm, lock.strong_algorithm),
        )
        if not walked.steps:
            raise RuntimeError("Holdout produced no scored draws")
        rng = random.Random(holdout_start)
        for index, step in enumerate(walked.steps):
            draw = next(row for row in draws if row.date == step.draw_date)
            step.random_ticket_rate = paired_random_rates(
                step,
                draw,
                portfolios=VALIDATION_RANDOM_PORTFOLIOS,
                rng=rng,
            )
            fair = expected_ticket_payout(draw)
            if fair is not None:
                step.expected_payout = fair * step.line_count
            if index % 25 == 0:
                logger.info(
                    "Holdout baseline",
                    context={"index": index, "of": len(walked.steps), "date": str(step.draw_date)},
                )
        self._store_steps(experiment.id, "holdout", lock.strategy_id, walked.steps)
        report = build_holdout_report(
            walked.steps,
            strategy_id=lock.strategy_id,
            samples=VALIDATION_BOOTSTRAP_SAMPLES,
        )
        report["experiment_id"] = experiment.id
        report["main_algorithm"] = lock.main_algorithm
        report["strong_algorithm"] = lock.strong_algorithm
        report["errors"] = walked.errors
        self.db.add(
            ValidationHoldoutResult(
                experiment_id=experiment.id,
                seal=_HOLDOUT_SEAL,
                verdict=report["verdict"],
                report=report,
            )
        )
        experiment.status = "holdout_done"
        self.db.commit()
        logger.info(
            "Holdout sealed",
            context={"experiment_id": experiment.id, "verdict": report["verdict"]},
        )
        return report

    def _store_steps(self, experiment_id: int, stage: str, strategy_id: str, steps: list[Any]) -> None:
        from models.validation_v2 import ValidationStep

        for step in steps:
            self.db.add(
                ValidationStep(
                    experiment_id=experiment_id,
                    stage=stage,
                    strategy_id=strategy_id,
                    draw_id=step.draw_id,
                    draw_date=step.draw_date,
                    lines=step.lines,
                    ticket_wins=step.ticket_wins,
                    line_count=step.line_count,
                    tier_counts=step.tier_counts,
                    mean_main_hits=step.mean_main_hits,
                    payout_ils=step.payout,
                    cost_ils=step.cost,
                    random_ticket_rate=step.random_ticket_rate,
                )
            )
        self.db.commit()


def load_public_report(db: Any) -> dict[str, Any]:
    from models.validation_v2 import CoveragePortfolio, ValidationExperiment, ValidationHoldoutResult

    holdout = db.query(ValidationHoldoutResult).order_by(ValidationHoldoutResult.id.desc()).first()
    coverage = db.query(CoveragePortfolio).order_by(CoveragePortfolio.id.desc()).first()
    coverage_payload = None
    if coverage is not None:
        coverage_payload = {
            "p_any_prize": float(coverage.p_any),
            "regime_start": coverage.regime_start.isoformat(),
            "report": coverage.report,
        }
    if holdout is not None:
        payload = dict(holdout.report)
        payload["coverage"] = coverage_payload
        return payload
    experiment = db.query(ValidationExperiment).order_by(ValidationExperiment.id.desc()).first()
    if experiment is None:
        return {
            "evidence_valid": False,
            "verdict": "not_run",
            "coverage": coverage_payload,
            "note": "Select has not been run.",
        }
    return {
        "evidence_valid": False,
        "verdict": "inconclusive" if experiment.status == "no_stable_candidate" else experiment.status,
        "experiment_id": experiment.id,
        "reason": experiment.refusal_reason,
        "coverage": coverage_payload,
    }
