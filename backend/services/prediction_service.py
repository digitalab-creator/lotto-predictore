"""Production next-draw generation — coverage wheel only (API, cron, email).

Legacy name: predictions are audit rows for packs, not algorithm picks.
"""

from __future__ import annotations

import datetime
import random
from typing import Any

from sqlalchemy.orm import Session

from algorithms import register_algorithms
from config import (
    LINES_PER_DRAW,
    MAX_STAKE_PER_DRAW_ILS,
    NUM_COMBINATIONS_TO_RECOMMEND,
    TICKET_COST_ILS,
)
from logger import logger
from models import Draw, Model, ModelType
from models.generated_combination import GeneratedCombination
from models.prediction import Prediction
from services.coverage_optimizer import load_cached_lines
from services.game_regime import split_regime
from services.pais_draw_rules import CURRENT_REGIME_START
from services.strategy_selection import choose_production_strategy
from services.ticket_validator import TicketValidationError
from services.simulation_helpers.simulation_db import get_or_create_model
from services.ticket_pack_service import TicketPackService

register_algorithms()

MIN_DRAWS_FOR_PRODUCTION = 20


def _top_n_for_algo(algo_name: str) -> int:
    if algo_name == "top_6_overall_frequent_v2":
        return 10
    return 3


class PredictionService:
    def __init__(self, db: Session, rng: random.Random | None = None):
        self.db = db
        self.rng = rng or random.Random()

    def generate_next_draw(self) -> dict[str, Any]:
        """Persist one production pack from the exact coverage wheel."""
        logger.info("Arrr! generate_next_draw — praisin' the FSM!")
        try:
            rows = (
                self.db.query(Draw)
                .filter(Draw.date >= CURRENT_REGIME_START)
                .order_by(Draw.date.asc())
                .all()
            )
            draws, illegal = split_regime(rows)
            if illegal:
                logger.error(
                    "Arrr! Current-regime rows failed the 6/37 + strong 1-7 check",
                    context={"illegal": len(illegal)},
                )
            if len(draws) < MIN_DRAWS_FOR_PRODUCTION:
                msg = f"Not enough draws in database (need {MIN_DRAWS_FOR_PRODUCTION})"
                logger.error(msg, context={"draw_count": len(draws)})
                return {"success": False, "message": msg, "tables": []}

            last_draw = draws[-1]
            as_of_date = last_draw.date
            train_start = draws[0].date
            main_algo, strong_algo, strategy_meta = self._select_production_strategy()

            if not strategy_meta.get("use_coverage"):
                logger.error(
                    "Arrr! Non-coverage production path blocked",
                    context={"strategy_meta": strategy_meta},
                )
                return {
                    "success": False,
                    "message": "Production only serves the coverage wheel.",
                    "tables": [],
                }
            cached = load_cached_lines(self.db)
            if not cached:
                msg = "Coverage pack is not cached yet. Run scripts/run_validation_v2.py coverage."
                logger.error(msg)
                return {"success": False, "message": msg, "tables": []}
            lines = cached
            top_n = _top_n_for_algo(main_algo)

            target_draw_number = None
            if last_draw.draw_number is not None:
                target_draw_number = int(last_draw.draw_number) + 1

            prediction_row = self._persist_prediction(
                main_algo=main_algo,
                strong_algo=strong_algo,
                lines=lines,
                train_start=train_start,
                train_end=as_of_date,
                top_n=top_n,
                strategy_meta=strategy_meta,
                target_draw_number=target_draw_number,
            )
            pack = TicketPackService(self.db).create_pack(
                lines=lines,
                main_algo=main_algo,
                strong_algo=strong_algo,
                training_cutoff=as_of_date,
                target_draw_number=target_draw_number,
                strategy_meta=strategy_meta,
                prediction_id=prediction_row.id,
            )

            total_cost = LINES_PER_DRAW * float(TICKET_COST_ILS)
            model_info = {
                "main_model": main_algo,
                "strong_model": strong_algo,
                "strategy_source": strategy_meta.get("source"),
                "training_cutoff": as_of_date.isoformat(),
                "target_draw_number": target_draw_number,
                "planned_cost_ils": total_cost,
                "max_stake_ils": MAX_STAKE_PER_DRAW_ILS,
            }
            for key in (
                "detail",
                "no_edge",
                "random_percentile",
                "independent_draw_count",
                "strategy_id",
                "has_predictive_edge",
            ):
                if strategy_meta.get(key) is not None:
                    model_info[key] = strategy_meta[key]

            tables = [{"numbers": ln["numbers"], "strong": ln["strong"]} for ln in lines]
            result = {
                "success": True,
                "date": datetime.date.today().isoformat(),
                "as_of_date": as_of_date.isoformat(),
                "target_draw_number": target_draw_number,
                "tables": tables,
                "lines": lines,
                "prediction_id": prediction_row.id,
                "ticket_pack_id": pack.id,
                "model_info": model_info,
                "algorithm": main_algo,
                "strong_algorithm": strong_algo,
                "combinations": [
                    {
                        "numbers": ln["numbers"],
                        "strong": ln["strong"],
                        "position": idx + 1,
                    }
                    for idx, ln in enumerate(lines)
                ],
            }
            logger.info(
                "Arrr! Production next-draw pack ready",
                context={
                    "prediction_id": prediction_row.id,
                    "main_algo": main_algo,
                    "strong_algo": strong_algo,
                    "target_draw_number": target_draw_number,
                },
            )
            return result
        except TicketValidationError as exc:
            logger.error(
                "Arrr! Ticket validation failed for production pack",
                context={"error": str(exc)},
            )
            return {"success": False, "message": str(exc), "tables": []}
        except Exception as exc:
            logger.error(
                "Arrr! generate_next_draw failed",
                context={"error": str(exc)},
            )
            raise

    def _select_production_strategy(self) -> tuple[str, str, dict[str, Any]]:
        return choose_production_strategy(self.db)

    def _persist_prediction(
        self,
        *,
        main_algo: str,
        strong_algo: str,
        lines: list[dict],
        train_start: datetime.date,
        train_end: datetime.date,
        top_n: int,
        strategy_meta: dict,
        target_draw_number: int | None,
    ) -> Prediction:
        main_model = get_or_create_model(
            self.db,
            main_algo,
            main_algo,
            ModelType.main,
            {"top_n": top_n, "production": True},
        )
        strong_model = get_or_create_model(
            self.db,
            strong_algo,
            strong_algo,
            ModelType.strong,
            {"production": True},
        )
        if not main_model or not strong_model:
            raise ValueError(
                f"Could not resolve model rows for {main_algo} / {strong_algo}"
            )

        now = datetime.datetime.utcnow()
        planned_cost = LINES_PER_DRAW * float(TICKET_COST_ILS)
        notes = (
            f"production_next_draw | target={target_draw_number} | "
            f"strategy={strategy_meta.get('source')} | cutoff={train_end.isoformat()}"
        )
        prediction = Prediction(
            model_id=main_model.id,
            strong_model_id=strong_model.id,
            run_time=now,
            roi=0.0,
            total_prize=0.0,
            total_cost=planned_cost,
            test_count=0,
            notes=notes,
            train_start_date=train_start,
            train_end_date=train_end,
            num_test_draws=0,
            main_model_params={
                "top_n": top_n,
                "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND,
                "as_of_date": train_end.isoformat(),
                "target_draw_number": target_draw_number,
            },
            strong_model_params={
                "strong_algo": strong_algo,
                "as_of_date": train_end.isoformat(),
            },
        )
        self.db.add(prediction)
        self.db.flush()

        for idx, line in enumerate(lines):
            self.db.add(
                GeneratedCombination(
                    prediction_id=prediction.id,
                    algorithm_id=main_algo,
                    numbers=line["numbers"],
                    strong_number=line["strong"],
                    version=main_algo,
                    position=idx + 1,
                    generated_at=now,
                )
            )
        self.db.commit()
        self.db.refresh(prediction)
        return prediction
