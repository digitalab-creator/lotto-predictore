"""Choose production main+strong from walk-forward strategy_summaries."""

from __future__ import annotations

from sqlalchemy.orm import Session

from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import (
    NO_EDGE_LABEL,
    PRODUCTION_FALLBACK_MAIN,
    PRODUCTION_FALLBACK_STRONG,
    PRODUCTION_MAIN_ALGO,
    PRODUCTION_STRONG_ALGO,
    WALK_FORWARD_MIN_DRAWS_FOR_EDGE,
    WALK_FORWARD_RANDOM_PERCENTILE_HIGH,
    WALK_FORWARD_RANDOM_PERCENTILE_LOW,
)
from logger import logger
from models.evaluation import StrategySummary
from services.walk_forward_stats import parse_strategy_id

CONTROL_STRATEGY_ID = "uniform_random+random"


def choose_production_strategy(db: Session) -> tuple[str, str, dict[str, str | float | bool]]:
    """
    Rank on random percentile and independent draw count — never SUM(predictions).
    Falls back to env config when the scoreboard is empty or sample size is small.
    """
    summaries = (
        db.query(StrategySummary)
        .filter(StrategySummary.strategy_id != CONTROL_STRATEGY_ID)
        .order_by(
            StrategySummary.random_percentile.desc(),
            StrategySummary.independent_draw_count.desc(),
        )
        .all()
    )
    if not summaries:
        logger.warning("Arrr! No strategy_summaries rows — using config fallback")
        return _config_fallback("scoreboard_empty")

    best = summaries[0]
    n = int(best.independent_draw_count or 0)
    percentile = float(best.random_percentile or 0.0)

    meta: dict[str, str | float | bool] = {
        "source": "walk_forward",
        "strategy_id": best.strategy_id,
        "random_percentile": percentile,
        "independent_draw_count": n,
        "has_predictive_edge": bool(best.has_predictive_edge),
    }

    if n < WALK_FORWARD_MIN_DRAWS_FOR_EDGE:
        logger.info(
            "Arrr! Walk-forward sample too small for edge claim — config fallback",
            context={"n": n, "required": WALK_FORWARD_MIN_DRAWS_FOR_EDGE},
        )
        meta["detail"] = "insufficient_independent_draws"
        main, strong = _config_fallback_pair()
        meta["config_main"] = main
        meta["config_strong"] = strong
        return main, strong, meta

    if (
        WALK_FORWARD_RANDOM_PERCENTILE_LOW <= percentile <= WALK_FORWARD_RANDOM_PERCENTILE_HIGH
    ):
        logger.info(
            "Arrr! Best strategy inside random band — diversified_random for production",
            context={"strategy_id": best.strategy_id, "percentile": percentile},
        )
        meta["detail"] = NO_EDGE_LABEL
        meta["no_edge"] = True
        return PRODUCTION_FALLBACK_MAIN, PRODUCTION_FALLBACK_STRONG, meta

    if not best.has_predictive_edge:
        meta["detail"] = NO_EDGE_LABEL
        meta["no_edge"] = True
        return PRODUCTION_FALLBACK_MAIN, PRODUCTION_FALLBACK_STRONG, meta

    main, strong = parse_strategy_id(best.strategy_id)
    if main not in ALGORITHM_REGISTRY or strong not in STRONG_NUMBER_REGISTRY:
        logger.error(
            "Arrr! Scoreboard winner not in registry — config fallback",
            context={"strategy_id": best.strategy_id},
        )
        meta["detail"] = "winner_not_registered"
        main, strong = _config_fallback_pair()
        return main, strong, meta

    meta["detail"] = "walk_forward_winner"
    return main, strong, meta


def _config_fallback(reason: str) -> tuple[str, str, dict[str, str]]:
    main, strong = _config_fallback_pair()
    return main, strong, {"source": "config", "detail": reason}


def _config_fallback_pair() -> tuple[str, str]:
    return PRODUCTION_MAIN_ALGO, PRODUCTION_STRONG_ALGO
