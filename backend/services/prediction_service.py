"""Production next-draw generation — one path for API, cron, and email."""

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
from services.algorithm_runner import run_strategy_on_draws
from services.strategy_selection import choose_production_strategy
from services.portfolio_refiner import refine_portfolio
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
        """
        Fit on all draws through the last known result; persist one production pack.
        Strategy comes from config until Phase 4 walk-forward summaries exist.
        """
        logger.info("Arrr! generate_next_draw — praisin' the FSM!")
        try:
            draws = (
                self.db.query(Draw)
                .filter(Draw.strong_number <= 7)
                .order_by(Draw.date.asc())
                .all()
            )
            if len(draws) < MIN_DRAWS_FOR_PRODUCTION:
                msg = f"Not enough draws in database (need {MIN_DRAWS_FOR_PRODUCTION})"
                logger.error(msg, context={"draw_count": len(draws)})
                return {"success": False, "message": msg, "tables": []}

            last_draw = draws[-1]
            as_of_date = last_draw.date
            train_start = draws[0].date
            main_algo, strong_algo, strategy_meta = self._select_production_strategy()

            top_n = _top_n_for_algo(main_algo)
            raw_lines, _algo_params = run_strategy_on_draws(
                train_draws=draws,
                main_algo=main_algo,
                strong_algo=strong_algo,
                as_of_date=as_of_date,
                rng=self.rng,
                db=self.db if main_algo.startswith("sequence_lstm") else None,
            )
            lines = refine_portfolio(raw_lines, self.rng)

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
        """Rank from walk-forward ``strategy_summaries`` — never SUM(predictions)."""
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
