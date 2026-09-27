#!/usr/bin/env python3
"""Rebuild walk-forward evaluation_tickets and strategy_summaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.base import SessionLocal
from logger import logger
from services.walk_forward_evaluation import WalkForwardEvaluationService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run expanding-window walk-forward scoreboard")
    parser.add_argument(
        "--min-training",
        type=int,
        default=None,
        help="Minimum training draws before first scored step (default: config)",
    )
    parser.add_argument(
        "--skip-dl",
        action="store_true",
        help="Skip LSTM / deep-learning algorithms (faster local runs)",
    )
    parser.add_argument(
        "--algorithms",
        type=str,
        default=None,
        help="Comma-separated main algorithm ids to score (default: all registered)",
    )
    args = parser.parse_args()
    algo_filter = [a.strip() for a in args.algorithms.split(",")] if args.algorithms else None

    with SessionLocal() as db:
        service = WalkForwardEvaluationService(db)
        result = service.refresh_all(
            min_training=args.min_training,
            include_dl=not args.skip_dl,
            algorithm_filter=algo_filter,
        )
    logger.info("Arrr! Walk-forward refresh done", context=result)
    print(result)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
