"""Current Lotto rules era. One date cut, used by proof and live packs.

Dropping rows where the strong number happened to be 8 keeps the rest of the
old game. This helper keeps or drops a whole era by date.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from services.pais_draw_rules import (
    CURRENT_REGIME_START,
    REGULAR_COUNT,
    REGULAR_MAX,
    REGULAR_MIN,
    STRONG_MAX,
    STRONG_MIN,
)


class RegimeAuditError(RuntimeError):
    """The frozen rules date does not match the rows we were given."""


def is_legal_current_row(numbers: Any, strong: Any) -> bool:
    """True when mains are 6 distinct values in 1–37 and strong is 1–7."""
    if numbers is None or strong is None:
        return False
    try:
        nums = [int(n) for n in numbers]
        strong_n = int(strong)
    except (TypeError, ValueError):
        return False
    if len(nums) != REGULAR_COUNT or len(set(nums)) != REGULAR_COUNT:
        return False
    if any(n < REGULAR_MIN or n > REGULAR_MAX for n in nums):
        return False
    return STRONG_MIN <= strong_n <= STRONG_MAX


def in_current_regime(draw: Any) -> bool:
    """Date on or after the frozen cut, and the row is a legal current ticket."""
    draw_date = getattr(draw, "date", None)
    if not isinstance(draw_date, date) or draw_date < CURRENT_REGIME_START:
        return False
    return is_legal_current_row(getattr(draw, "numbers", None), getattr(draw, "strong_number", None))


def split_regime(draws: list[Any]) -> tuple[list[Any], list[Any]]:
    """Return (legal current-era rows, illegal rows on or after the cut).

    Rows before the cut are omitted entirely, including strong numbers 1–7.
    """
    legal: list[Any] = []
    illegal: list[Any] = []
    for draw in draws:
        draw_date = getattr(draw, "date", None)
        if not isinstance(draw_date, date) or draw_date < CURRENT_REGIME_START:
            continue
        if is_legal_current_row(getattr(draw, "numbers", None), getattr(draw, "strong_number", None)):
            legal.append(draw)
        else:
            illegal.append(draw)
    legal.sort(key=lambda row: row.date)
    return legal, illegal


def assert_regime_clean(illegal_after_start: list[Any]) -> None:
    """Refuse to score when a post-cut row breaks the current contract."""
    if not illegal_after_start:
        return
    sample = [str(getattr(row, "date", "?")) for row in illegal_after_start[:8]]
    raise RegimeAuditError(
        f"{len(illegal_after_start)} draws on or after {CURRENT_REGIME_START.isoformat()} "
        f"are not 6/37 + strong 1–7. Sample dates: {sample}"
    )


def current_regime_query(db: Any):
    """SQL date cut only. Callers still drop illegal post-cut rows in Python."""
    from models import Draw

    return db.query(Draw).filter(Draw.date >= CURRENT_REGIME_START)
