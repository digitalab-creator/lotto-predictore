"""Estimate next official Lotto draw date from the last known result."""

from __future__ import annotations

import datetime


def estimate_next_draw_date(last_draw_date: datetime.date) -> datetime.date:
    """
    Israel Lotto is usually Tue/Sat; Thu happens occasionally.
    Tue -> +4 (Sat), Sat -> +3 (Tue), Thu -> +2 (Sat) or +5 (Tue) — use +2 first.
    """
    weekday = last_draw_date.weekday()  # Mon=0
    if weekday == 1:  # Tuesday
        return last_draw_date + datetime.timedelta(days=4)
    if weekday == 5:  # Saturday
        return last_draw_date + datetime.timedelta(days=3)
    if weekday == 3:  # Thursday
        return last_draw_date + datetime.timedelta(days=2)
    return last_draw_date + datetime.timedelta(days=3)
