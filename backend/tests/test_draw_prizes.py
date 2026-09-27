"""Unit tests for draw-backed prize lookup (Phase 2)."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from config import TICKET_COST_ILS
from services.draw_prize import (
    PAIS_SOURCE,
    calculate_prize,
    draw_has_prize_data,
    draw_ticket_cost,
    parse_win_table_reg,
)


def _pais_draw(**overrides):
    base = {
        "source": PAIS_SOURCE,
        "prize_6_strong": Decimal("0"),
        "prize_6": Decimal("125000"),
        "prize_5_strong": Decimal("7241"),
        "prize_5": Decimal("498"),
        "prize_4_strong": Decimal("144"),
        "prize_4": Decimal("57"),
        "prize_3_strong": Decimal("38"),
        "prize_3": Decimal("10"),
        "ticket_cost_ils": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_parse_win_table_reg_from_api_sample():
    payload = {
        "_id": 2013,
        "date": "2009-02-28T12:00:00.000Z",
        "winNumbers": [8, 14, 24, 28, 34, 35],
        "strongNumber": 8,
        "firstPrizeReg": 10_000_000,
        "winTableReg": {
            "sixPlus": {"winners": 0, "sumPrize": 0},
            "six": {"winners": 4, "sumPrize": 125000},
            "fivePlus": {"winners": 15, "sumPrize": 7241},
            "five": {"winners": 116, "sumPrize": 498},
            "fourPlus": {"winners": 581, "sumPrize": 144},
            "four": {"winners": 3477, "sumPrize": 57},
            "threePlus": {"winners": 7421, "sumPrize": 38},
            "three": {"winners": 47103, "sumPrize": 10},
        },
    }
    parsed = parse_win_table_reg(payload)
    assert parsed is not None
    assert parsed["prize_6"] == 125000.0
    assert parsed["prize_3"] == 10.0
    assert parsed["jackpot_lotto"] == 10_000_000.0


def test_calculate_prize_uses_draw_row_not_fake_table():
    draw = _pais_draw()
    assert calculate_prize(draw, 5, True) == 7241.0
    assert calculate_prize(draw, 3, False) == 10.0
    assert calculate_prize(draw, 2, True) == 0.0


def test_magayo_draw_without_prizes_excluded():
    draw = SimpleNamespace(source="magayo", prize_3=None)
    assert draw_has_prize_data(draw) is False
    assert calculate_prize(draw, 6, True) is None


def test_ticket_cost_defaults_to_config():
    draw = _pais_draw(ticket_cost_ils=Decimal("2.80"))
    assert draw_ticket_cost(draw) == 2.80
    assert draw_ticket_cost(_pais_draw()) == float(TICKET_COST_ILS)
