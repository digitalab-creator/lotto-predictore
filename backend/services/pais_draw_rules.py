"""Rules for a current-format Lotto row. One function, used by ingest and the Sunday check."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# After this date the draw numbers climb 1035 → today. Older rows use a different number series.
MODERN_SERIES_START = date(1999, 9, 1)
# Last stored strong number 8 is draw 2233 on 2011-03-01.
# From the next draw (2011-03-05) every year has strong in 1–7 only.
# The rest of 2011 has zero 8s; that is not luck under a 1–8 wheel.
# Draws before this date are a different game, even when their strong was 1–7.
CURRENT_REGIME_START = date(2011, 3, 5)
REGULAR_MIN = 1
REGULAR_MAX = 37
STRONG_MIN = 1
STRONG_MAX = 7
REGULAR_COUNT = 6
DRAW_WEEKDAYS = {1, 3, 5}  # Tue, Thu, Sat (Monday = 0)


@dataclass(frozen=True)
class CsvDraw:
    draw_number: int
    draw_date: date
    numbers: list[int]
    strong: int
    raw: str


def rejection_reason(row: CsvDraw, *, previous_number: int | None, today: date) -> str | None:
    """Return a short reason to quarantine the row, or None when it may be stored."""
    nums = row.numbers
    if len(nums) != REGULAR_COUNT:
        return "not_six_numbers"
    if len(set(nums)) != REGULAR_COUNT:
        return "duplicate_numbers"
    if any(n < REGULAR_MIN or n > REGULAR_MAX for n in nums):
        return "number_out_of_range"
    if row.strong < STRONG_MIN or row.strong > STRONG_MAX:
        return "strong_out_of_range"
    if row.draw_date > today + timedelta(days=1):
        return "date_in_future"
    if previous_number is not None and row.draw_number <= previous_number:
        return "draw_number_not_increasing"
    return None


def numbers_match(stored_numbers: list[int], stored_strong: int, row: CsvDraw) -> bool:
    return sorted(int(n) for n in stored_numbers) == sorted(row.numbers) and int(stored_strong) == row.strong


def newest_modern_row(rows: list[CsvDraw]) -> CsvDraw | None:
    """Newest by calendar date. Draw 9934 is 1999-08-24, so the biggest number is not the latest draw."""
    modern = [row for row in rows if row.draw_date >= MODERN_SERIES_START]
    pool = modern or list(rows)
    if not pool:
        return None
    return max(pool, key=lambda row: (row.draw_date, row.draw_number))
