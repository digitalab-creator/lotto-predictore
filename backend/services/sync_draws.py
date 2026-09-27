"""
Incremental draw sync for cron and API — one entry point.

Order (praise the FSM for honest data):
1. Pais /recent + byID catch-up + recent byDates window (fills prizes on existing rows)
2. Magayo latest (numbers only when Pais is stale or missing a new date)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select

from db import SessionLocal
from logger import logger
from models import Draw
from services.draw_prize import PAIS_SOURCE
from services.fetch_latest_draw import import_magayo_latest_draw
from services.import_draws_paisapi import (
    _ensure_draw_id_sequence,
    apply_pais_payload,
    fetch_recent_draw,
    sync_by_dates,
    sync_by_id_range,
)

DEFAULT_PAIS_BACKFILL_DAYS = 90


@dataclass
class SyncDrawsResult:
    pais_recent: str = "skipped"
    pais_by_id: dict[str, int] = field(default_factory=lambda: {"added": 0, "updated": 0, "skipped": 0})
    pais_window: dict[str, int] = field(default_factory=lambda: {"added": 0, "updated": 0, "skipped": 0})
    magayo: str = "skipped"
    pais_latest_draw_number: int | None = None
    pais_latest_date: str | None = None
    db_latest_date: str | None = None
    new_draws_added: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _count_tuple(added: int, updated: int, skipped: int) -> dict[str, int]:
    return {"added": added, "updated": updated, "skipped": skipped}


def sync_draws_incremental(db, *, pais_backfill_days: int = DEFAULT_PAIS_BACKFILL_DAYS) -> SyncDrawsResult:
    result = SyncDrawsResult()
    _ensure_draw_id_sequence(db)

    draws_before = db.execute(select(func.count(Draw.id))).scalar() or 0

    db_latest = db.execute(select(func.max(Draw.date))).scalar()
    if db_latest:
        result.db_latest_date = db_latest.isoformat()

    # --- Pais: single latest row (numbers + real prizes) ---
    try:
        recent = fetch_recent_draw()
    except httpx.HTTPError as exc:
        msg = f"Pais /recent failed: {exc}"
        logger.error(msg)
        result.errors.append(msg)
        recent = None

    if recent:
        if recent.get("_id") is not None:
            result.pais_latest_draw_number = int(recent["_id"])
        draw_date = recent.get("date") or recent.get("drawDate")
        if draw_date:
            result.pais_latest_date = str(draw_date)[:10]
        try:
            result.pais_recent = apply_pais_payload(db, recent)
            logger.info(
                f"Pais /recent apply: {result.pais_recent} (draw {result.pais_latest_draw_number})"
            )
        except Exception as exc:
            msg = f"Pais /recent apply failed: {exc}"
            logger.error(msg)
            result.errors.append(msg)

        latest_api_id = result.pais_latest_draw_number
        max_id = db.execute(select(func.max(Draw.draw_number))).scalar()
        if latest_api_id is not None:
            next_id = (max_id or 0) + 1
            if next_id <= latest_api_id:
                try:
                    a, u, s = sync_by_id_range(db, next_id, latest_api_id)
                    result.pais_by_id = _count_tuple(a, u, s)
                    logger.info(
                        f"Pais byID {next_id}..{latest_api_id}: "
                        f"added={a} updated={u} skipped={s}"
                    )
                except Exception as exc:
                    msg = f"Pais byID sync failed: {exc}"
                    logger.error(msg)
                    result.errors.append(msg)

    # --- Pais: rolling window — backfill prizes on Magayo/legacy rows Pais knows about ---
    end_exclusive = date.today() + timedelta(days=1)
    if result.pais_latest_date:
        pais_cap = date.fromisoformat(result.pais_latest_date) + timedelta(days=1)
        if pais_cap < end_exclusive:
            end_exclusive = pais_cap

    start = end_exclusive - timedelta(days=pais_backfill_days)
    if start < date(2007, 1, 1):
        start = date(2007, 1, 1)

    if start < end_exclusive:
        try:
            a, u, s = sync_by_dates(db, start, end_exclusive)
            result.pais_window = _count_tuple(a, u, s)
            logger.info(
                f"Pais byDates {start}..{end_exclusive}: added={a} updated={u} skipped={s}"
            )
        except Exception as exc:
            msg = f"Pais byDates window failed: {exc}"
            logger.error(msg)
            result.errors.append(msg)
    else:
        logger.info("Pais byDates window empty — nothing to backfill in range")

    # --- Magayo: numbers-only when Pais has no newer official row ---
    try:
        result.magayo = import_magayo_latest_draw(db)
        logger.info(f"Magayo latest: {result.magayo}")
    except Exception as exc:
        msg = f"Magayo latest failed: {exc}"
        logger.error(msg)
        result.errors.append(msg)

    db_latest = db.execute(select(func.max(Draw.date))).scalar()
    if db_latest:
        result.db_latest_date = db_latest.isoformat()

    draws_after = db.execute(select(func.count(Draw.id))).scalar() or 0
    result.new_draws_added = max(0, int(draws_after) - int(draws_before))

    return result


def main() -> dict[str, Any]:
    db = SessionLocal()
    try:
        outcome = sync_draws_incremental(db)
        if outcome.errors:
            logger.warning(f"Draw sync finished with errors: {outcome.errors}")
        return outcome.to_dict()
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(main(), indent=2))
