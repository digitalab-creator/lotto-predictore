#!/usr/bin/env python3
"""Build the coverage wheel, then select, then at most one sealed holdout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.base import SessionLocal
from logger import logger
from services.coverage_optimizer import optimize_coverage, save_coverage_portfolio
from services.prize_backfill import backfill_missing_prizes
from services.validation_engine_v2 import ValidationEngineV2
from services.validation_stats_v2 import HoldoutAlreadyRan


def _coverage(db) -> None:
    logger.info("Coverage search starting")
    packed = optimize_coverage(iterations=20, neighbors=8)
    row = save_coverage_portfolio(db, packed)
    logger.info(
        "Coverage pack stored",
        context={"id": row.id, "p_any": packed["p_any_prize"]},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sealed go/no-go validator")
    parser.add_argument(
        "stage",
        nargs="?",
        default="all",
        choices=("all", "coverage", "select", "holdout", "prizes"),
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.stage == "prizes":
            summary = backfill_missing_prizes(db)
            logger.info("Prize backfill finished", context=summary)
            return 0
        if args.stage in {"coverage", "all"}:
            _coverage(db)
            if args.stage == "coverage":
                return 0
        engine = ValidationEngineV2(db)
        if args.stage in {"select", "all"}:
            select_result = engine.run_select()
            logger.info("Select result", context={"promoted": select_result.get("promoted")})
            if args.stage == "select":
                return 0
            if not select_result.get("promoted"):
                logger.info("Holdout not burned — no stable candidate")
                return 0
        try:
            report = engine.run_holdout()
        except HoldoutAlreadyRan as exc:
            logger.error(str(exc))
            return 2
        logger.info("Verdict", context={"verdict": report.get("verdict")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
