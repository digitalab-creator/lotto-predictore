"""Production tickets always come from the exact coverage wheel.

Sealed holdout results are recorded for research only. They never select algorithms
for live packs.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import NO_EDGE_LABEL
from logger import logger

COVERAGE_MAIN = "coverage_optimizer"
COVERAGE_STRONG = "exact"
PRODUCTION_MODE = "coverage_wheel"


def choose_production_strategy(db: Session) -> tuple[str, str, dict[str, str | float | bool]]:
    """Always return the cached exact wheel. Prediction models are not production paths."""
    meta: dict[str, str | float | bool] = {
        "source": PRODUCTION_MODE,
        "production_mode": PRODUCTION_MODE,
        "detail": NO_EDGE_LABEL,
        "no_edge": True,
        "use_coverage": True,
        "has_predictive_edge": False,
        "prediction_allowed": False,
        "strategy_id": f"{COVERAGE_MAIN}+{COVERAGE_STRONG}",
    }
    sealed = _latest_holdout_summary(db)
    if sealed is not None:
        meta["sealed_holdout_verdict"] = sealed["verdict"]
        meta["sealed_strategy_tested"] = sealed["strategy_id"]
        if sealed["verdict"] == "fail":
            meta["detail"] = "Sealed holdout failed — coverage wheel only."
    logger.info("Arrr! Production mode is coverage wheel (prediction disabled)")
    return COVERAGE_MAIN, COVERAGE_STRONG, meta


def _latest_holdout_summary(db: Session) -> dict[str, str] | None:
    from models.validation_v2 import ValidationHoldoutResult, ValidationLock

    holdout = (
        db.query(ValidationHoldoutResult)
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
    strategy_id = lock.strategy_id if lock is not None else "unknown"
    return {"verdict": str(holdout.verdict), "strategy_id": strategy_id}
