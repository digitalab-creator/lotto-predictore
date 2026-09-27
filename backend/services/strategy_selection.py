"""Production strategy comes from the sealed validator, or from the coverage wheel."""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import NO_EDGE_LABEL
from logger import logger

COVERAGE_MAIN = "coverage_optimizer"
COVERAGE_STRONG = "exact"


def choose_production_strategy(db: Session) -> tuple[str, str, dict[str, str | float | bool]]:
    """
    A holdout pass is the only way an algorithm is allowed to sell tickets.
    Until that pass exists, the pack is the exact 8-line coverage wheel.
    The old walk-forward scoreboard is not consulted.
    """
    sealed = _sealed_pass(db)
    if sealed is not None:
        return sealed

    logger.info("Arrr! No sealed pass — coverage wheel, not the old scoreboard")
    return (
        COVERAGE_MAIN,
        COVERAGE_STRONG,
        {
            "source": "coverage_optimizer",
            "detail": NO_EDGE_LABEL,
            "no_edge": True,
            "use_coverage": True,
            "strategy_id": f"{COVERAGE_MAIN}+{COVERAGE_STRONG}",
            "has_predictive_edge": False,
        },
    )


def _sealed_pass(db: Session) -> tuple[str, str, dict[str, str | float | bool]] | None:
    from models.validation_v2 import ValidationHoldoutResult, ValidationLock

    holdout = (
        db.query(ValidationHoldoutResult)
        .filter(ValidationHoldoutResult.verdict == "pass")
        .order_by(ValidationHoldoutResult.id.desc())
        .first()
    )
    if holdout is None:
        return None
    lock = (
        db.query(ValidationLock)
        .filter(ValidationLock.experiment_id == holdout.experiment_id)
        .one_or_none()
    )
    if lock is None:
        logger.error("Arrr! Holdout pass without a lock row")
        return None
    return (
        lock.main_algorithm,
        lock.strong_algorithm,
        {
            "source": "validation_v2",
            "detail": "sealed_holdout_pass",
            "strategy_id": lock.strategy_id,
            "no_edge": False,
            "has_predictive_edge": True,
        },
    )
