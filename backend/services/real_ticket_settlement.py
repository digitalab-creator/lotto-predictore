"""Settle submitted real_ticket_batches against an official draw with real prizes."""

from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from logger import logger
from models import Draw
from models.ticket_pack import PACK_STATUS_SUBMITTED, RealTicketBatch, TicketPack
from services.draw_prize import calculate_prize, draw_has_prize_data, draw_ticket_cost
from services.ticket_validator import count_hits


class RealTicketSettlementService:
    def __init__(self, db: Session):
        self.db = db

    def settle_submitted_pack_for_draw(self, draw: Draw) -> dict | None:
        """If a submitted pack targets this draw_number, settle its batch."""
        if draw.draw_number is None:
            return None
        pack = (
            self.db.query(TicketPack)
            .filter(
                TicketPack.target_draw_number == int(draw.draw_number),
                TicketPack.status == PACK_STATUS_SUBMITTED,
            )
            .order_by(TicketPack.generated_at.desc())
            .first()
        )
        if not pack:
            return None
        batch = (
            self.db.query(RealTicketBatch)
            .filter(RealTicketBatch.ticket_pack_id == pack.id)
            .first()
        )
        if not batch:
            logger.warning(
                "Arrr! Submitted pack without real batch row",
                context={"pack_id": pack.id},
            )
            return None
        if batch.settled_at is not None:
            return {
                "pack_id": pack.id,
                "batch_id": batch.id,
                "already_settled": True,
                "net_ils": float(batch.net_ils or 0),
            }
        if not draw_has_prize_data(draw):
            logger.info(
                "Arrr! Draw has no prize data — settlement deferred",
                context={"draw_id": draw.id},
            )
            return {"pack_id": pack.id, "deferred": True, "reason": "no_prize_data"}

        payout = Decimal("0")
        line_cost = Decimal(str(draw_ticket_cost(draw)))
        for ln in batch.lines_snapshot:
            hits = count_hits(ln["numbers"], draw.numbers)
            strong_hit = int(ln["strong"]) == int(draw.strong_number)
            prize = calculate_prize(draw, hits, strong_hit)
            if prize is None:
                continue
            payout += Decimal(str(prize))

        investment = Decimal(str(batch.investment_ils))
        net = payout - investment
        now = datetime.datetime.now(datetime.timezone.utc)
        batch.draw_id = draw.id
        batch.payout_ils = payout
        batch.net_ils = net
        batch.settled_at = now
        self.db.commit()
        logger.info(
            "Arrr! Real ticket batch settled — FSM be watchin' the ledger!",
            context={
                "batch_id": batch.id,
                "draw_number": draw.draw_number,
                "payout": float(payout),
                "net": float(net),
            },
        )
        return {
            "pack_id": pack.id,
            "batch_id": batch.id,
            "investment_ils": float(investment),
            "payout_ils": float(payout),
            "net_ils": float(net),
        }

    def latest_settled_real_summary(self) -> dict | None:
        batch = (
            self.db.query(RealTicketBatch)
            .filter(RealTicketBatch.settled_at.isnot(None))
            .order_by(RealTicketBatch.settled_at.desc())
            .first()
        )
        if not batch:
            return None
        return {
            "batch_id": batch.id,
            "investment_ils": float(batch.investment_ils),
            "payout_ils": float(batch.payout_ils or 0),
            "net_ils": float(batch.net_ils or 0),
            "settled_at": batch.settled_at.isoformat() if batch.settled_at else None,
        }
