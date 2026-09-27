"""Phase 5 — ticket packs, real batches, portfolio refiner."""

from __future__ import annotations

import datetime
import random
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
from models.ticket_pack import (
    PACK_STATUS_NOT_SUBMITTED,
    PackDelivery,
    RealTicketBatch,
    TicketPack,
)
from services.draw_prize import PAIS_SOURCE
from services.portfolio_refiner import refine_portfolio
from services.real_ticket_settlement import RealTicketSettlementService
from services.ticket_pack_service import TicketPackService
from services.ticket_validator import validate_portfolio


def _eight_lines():
    return [
        {"numbers": [1, 2, 3, 4, 5, 6], "strong": 1},
        {"numbers": [7, 8, 9, 10, 11, 12], "strong": 2},
        {"numbers": [13, 14, 15, 16, 17, 18], "strong": 3},
        {"numbers": [19, 20, 21, 22, 23, 24], "strong": 4},
        {"numbers": [25, 26, 27, 28, 29, 30], "strong": 5},
        {"numbers": [31, 32, 33, 34, 35, 36], "strong": 6},
        {"numbers": [1, 3, 5, 7, 9, 11], "strong": 7},
        {"numbers": [2, 4, 6, 8, 10, 12], "strong": 1},
    ]


def _pack_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            TicketPack.__table__,
            RealTicketBatch.__table__,
            PackDelivery.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def test_refine_portfolio_keeps_eight_valid_lines():
    refined = refine_portfolio(_eight_lines(), random.Random(1))
    validate_portfolio(refined)


def test_submitted_creates_real_batch_not_submitted_does_not():
    db = _pack_db()
    svc = TicketPackService(db)
    pack = svc.create_pack(
        lines=_eight_lines(),
        main_algo="diversified_random",
        strong_algo="random",
        training_cutoff=datetime.date(2026, 1, 1),
        target_draw_number=100,
        strategy_meta={"source": "test"},
    )
    batch = svc.mark_submitted(pack.id)
    assert batch.id is not None
    assert db.query(RealTicketBatch).count() == 1

    pack2 = svc.create_pack(
        lines=_eight_lines(),
        main_algo="diversified_random",
        strong_algo="random",
        training_cutoff=datetime.date(2026, 1, 8),
        target_draw_number=101,
        strategy_meta={"source": "test"},
    )
    svc.mark_not_submitted(pack2.id)
    assert db.query(RealTicketBatch).filter(RealTicketBatch.ticket_pack_id == pack2.id).count() == 0
    assert pack2.status == PACK_STATUS_NOT_SUBMITTED


def test_settlement_uses_submitted_batch_only():
    db = _pack_db()
    lines_no_jackpot = [
        {"numbers": [10, 11, 12, 13, 14, 15], "strong": 2},
        {"numbers": [16, 17, 18, 19, 20, 21], "strong": 3},
        {"numbers": [22, 23, 24, 25, 26, 27], "strong": 4},
        {"numbers": [28, 29, 30, 31, 32, 33], "strong": 5},
        {"numbers": [34, 35, 36, 37, 10, 11], "strong": 6},
        {"numbers": [12, 13, 14, 15, 16, 17], "strong": 7},
        {"numbers": [18, 19, 20, 21, 22, 23], "strong": 2},
        {"numbers": [1, 2, 3, 10, 11, 12], "strong": 1},
    ]
    draw = SimpleNamespace(
        id=1,
        draw_number=50,
        date=datetime.date(2026, 2, 1),
        numbers=[1, 2, 3, 4, 5, 6],
        strong_number=1,
        prize_3=10,
        prize_3_strong=20,
        prize_4=100,
        prize_4_strong=200,
        prize_5=1000,
        prize_5_strong=2000,
        prize_6=10000,
        prize_6_strong=20000,
        source=PAIS_SOURCE,
        ticket_cost_ils=3,
    )

    svc = TicketPackService(db)
    pack = svc.create_pack(
        lines=lines_no_jackpot,
        main_algo="diversified_random",
        strong_algo="random",
        training_cutoff=datetime.date(2026, 1, 25),
        target_draw_number=50,
        strategy_meta={},
    )
    svc.mark_submitted(pack.id)
    result = RealTicketSettlementService(db).settle_submitted_pack_for_draw(draw)
    assert result is not None
    assert result["payout_ils"] == pytest.approx(20.0)  # 3 hits + strong
    assert result["net_ils"] == pytest.approx(-4.0)
