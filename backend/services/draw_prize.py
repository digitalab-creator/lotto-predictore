"""Real per-draw prize tiers from Pais API winTableReg — single source for scoring."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from config import TICKET_COST_ILS

PAIS_SOURCE = "paisapi"
MAGAYO_SOURCE = "magayo"


def pais_payload_source_hash(payload: Mapping[str, Any]) -> str:
    """Stable hash for idempotent ingest / change detection."""
    canonical = {
        "date": payload.get("date") or payload.get("drawDate"),
        "_id": payload.get("_id"),
        "winNumbers": payload.get("winNumbers"),
        "strongNumber": payload.get("strongNumber"),
        "winTableReg": payload.get("winTableReg"),
        "firstPrizeReg": payload.get("firstPrizeReg"),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_win_table_reg(payload: Mapping[str, Any]) -> Optional[dict[str, Optional[float]]]:
    """Extract per-tier prize amounts (sumPrize per winner) from a Pais draw payload."""
    win_table = payload.get("winTableReg")
    if not isinstance(win_table, dict):
        return None

    def tier(key: str) -> Optional[float]:
        row = win_table.get(key)
        if not isinstance(row, dict):
            return None
        val = row.get("sumPrize")
        if val is None:
            return None
        return float(val)

    parsed = {
        "prize_6_strong": tier("sixPlus"),
        "prize_6": tier("six"),
        "prize_5_strong": tier("fivePlus"),
        "prize_5": tier("five"),
        "prize_4_strong": tier("fourPlus"),
        "prize_4": tier("four"),
        "prize_3_strong": tier("threePlus"),
        "prize_3": tier("three"),
        "jackpot": float(payload["firstPrizeReg"])
        if payload.get("firstPrizeReg") is not None
        else None,
    }
    if parsed["prize_3"] is None:
        return None
    return parsed


def draw_has_prize_data(draw) -> bool:
    """Draws without Pais prize rows must not affect ROI."""
    return getattr(draw, "source", None) == PAIS_SOURCE and getattr(draw, "prize_3", None) is not None


def draw_ticket_cost(draw) -> float:
    cost = getattr(draw, "ticket_cost_ils", None)
    if cost is not None:
        return float(cost)
    return float(TICKET_COST_ILS)


def calculate_prize(draw, hits: int, strong_hit: bool) -> Optional[float]:
    """
    Prize for one line against a real draw row.
    Returns None when the draw has no stored prize table (exclude from ROI).
    """
    if not draw_has_prize_data(draw):
        return None
    if hits >= 6:
        return float(draw.prize_6_strong if strong_hit else draw.prize_6 or 0)
    if hits == 5:
        return float(draw.prize_5_strong if strong_hit else draw.prize_5 or 0)
    if hits == 4:
        return float(draw.prize_4_strong if strong_hit else draw.prize_4 or 0)
    if hits == 3:
        return float(draw.prize_3_strong if strong_hit else draw.prize_3 or 0)
    return 0.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
