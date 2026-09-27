"""Create and manage ticket packs — the object you act on at the Pais counter."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from config import LINES_PER_DRAW, MAX_STAKE_PER_DRAW_ILS, NO_EDGE_LABEL, TICKET_COST_ILS
from logger import logger
from models.ticket_pack import (
    PACK_STATUS_NOT_SUBMITTED,
    PACK_STATUS_PENDING,
    PACK_STATUS_SUBMITTED,
    RealTicketBatch,
    TicketPack,
)
from services.draw_schedule import estimate_next_draw_date
from services.walk_forward_stats import make_strategy_id


def format_line_copy(numbers: list[int], strong: int) -> str:
    nums = " ".join(f"{int(n):02d}" for n in numbers)
    return f"{nums} | חזק {int(strong)}"


def pack_lines_copy_block(lines: list[dict]) -> str:
    rows = []
    for idx, ln in enumerate(lines, start=1):
        rows.append(f"{idx}. {format_line_copy(ln['numbers'], ln['strong'])}")
    return "\n".join(rows)


class TicketPackService:
    def __init__(self, db: Session):
        self.db = db

    def create_pack(
        self,
        *,
        lines: list[dict],
        main_algo: str,
        strong_algo: str,
        training_cutoff: datetime.date,
        target_draw_number: int | None,
        strategy_meta: dict[str, Any],
        prediction_id: int | None = None,
    ) -> TicketPack:
        target_date = None
        if training_cutoff:
            target_date = estimate_next_draw_date(training_cutoff)
        strategy_id = strategy_meta.get("strategy_id") or make_strategy_id(main_algo, strong_algo)
        no_edge = None
        if strategy_meta.get("no_edge") or strategy_meta.get("detail") == NO_EDGE_LABEL:
            no_edge = NO_EDGE_LABEL

        pack = TicketPack(
            target_draw_number=target_draw_number,
            target_draw_date=target_date,
            lines=lines,
            planned_cost_ils=LINES_PER_DRAW * float(TICKET_COST_ILS),
            strategy_id=strategy_id,
            main_algorithm=main_algo,
            strong_algorithm=strong_algo,
            training_cutoff=training_cutoff,
            generated_at=datetime.datetime.now(datetime.timezone.utc),
            status=PACK_STATUS_PENDING,
            prediction_id=prediction_id,
            no_edge_label=no_edge,
            strategy_meta=strategy_meta,
        )
        self.db.add(pack)
        self.db.commit()
        self.db.refresh(pack)
        logger.info(
            "Arrr! Ticket pack created — praise the FSM!",
            context={"pack_id": pack.id, "target_draw_number": target_draw_number},
        )
        return pack

    def get_pack(self, pack_id: int) -> TicketPack | None:
        return self.db.query(TicketPack).filter(TicketPack.id == pack_id).first()

    def mark_submitted(self, pack_id: int) -> RealTicketBatch:
        pack = self.get_pack(pack_id)
        if not pack:
            raise ValueError("Ticket pack not found")
        if pack.status == PACK_STATUS_SUBMITTED:
            existing = (
                self.db.query(RealTicketBatch)
                .filter(RealTicketBatch.ticket_pack_id == pack.id)
                .first()
            )
            if existing:
                return existing
        if pack.status == PACK_STATUS_NOT_SUBMITTED:
            raise ValueError("Pack already marked not submitted")

        now = datetime.datetime.now(datetime.timezone.utc)
        pack.status = PACK_STATUS_SUBMITTED
        batch = RealTicketBatch(
            ticket_pack_id=pack.id,
            draw_id=None,
            investment_ils=float(pack.planned_cost_ils),
            payout_ils=None,
            net_ils=None,
            submitted_at=now,
            settled_at=None,
            lines_snapshot=pack.lines,
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def mark_not_submitted(self, pack_id: int) -> TicketPack:
        pack = self.get_pack(pack_id)
        if not pack:
            raise ValueError("Ticket pack not found")
        if pack.status == PACK_STATUS_SUBMITTED:
            raise ValueError("Pack already submitted — cannot mark not submitted")
        pack.status = PACK_STATUS_NOT_SUBMITTED
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def find_pending_submitted_for_draw(self, draw_number: int) -> TicketPack | None:
        return (
            self.db.query(TicketPack)
            .filter(
                TicketPack.target_draw_number == draw_number,
                TicketPack.status == PACK_STATUS_SUBMITTED,
            )
            .order_by(TicketPack.generated_at.desc())
            .first()
        )

    def latest_pending_pack(self) -> TicketPack | None:
        return (
            self.db.query(TicketPack)
            .filter(TicketPack.status == PACK_STATUS_PENDING)
            .order_by(TicketPack.generated_at.desc())
            .first()
        )

    def pack_public_payload(self, pack: TicketPack) -> dict[str, Any]:
        return {
            "id": pack.id,
            "target_draw_number": pack.target_draw_number,
            "target_draw_date": pack.target_draw_date.isoformat() if pack.target_draw_date else None,
            "planned_cost_ils": float(pack.planned_cost_ils),
            "max_stake_ils": MAX_STAKE_PER_DRAW_ILS,
            "status": pack.status,
            "strategy_id": pack.strategy_id,
            "main_algorithm": pack.main_algorithm,
            "strong_algorithm": pack.strong_algorithm,
            "training_cutoff": pack.training_cutoff.isoformat(),
            "generated_at": pack.generated_at.isoformat(),
            "no_edge_label": pack.no_edge_label,
            "lines": pack.lines,
            "copy_text": pack_lines_copy_block(pack.lines),
            "strategy_meta": pack.strategy_meta or {},
        }
