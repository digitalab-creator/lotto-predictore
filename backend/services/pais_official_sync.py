"""Official Pais CSV is the live source. Magayo runs only when that file is missing a draw."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from config import PAIS_MAX_FAILURES, TICKET_COST_ILS
from logger import logger
from models import Draw, DrawQuarantine, IngestState
from services.draw_prize import PAIS_CSV_SOURCE, utc_now
from services.fetch_latest_draw import import_magayo_latest_draw
from services.import_draws_paisapi import _ensure_draw_id_sequence
from services.pais_csv import download_official_csv, file_sha256, parse_official_csv
from services.pais_draw_detail import fetch_draw_detail
from services.pais_draw_rules import (
    DRAW_WEEKDAYS,
    MODERN_SERIES_START,
    CsvDraw,
    newest_modern_row,
    numbers_match,
    rejection_reason,
)
from services.pais_proxy import PaisSourceError, open_pais_client
from services.pais_rate_limit import mark_pais_error_cooldown
from services.sync_draws import SyncDrawsResult

# One prize page per sync run. Spacing is the shared Pais gate, not a private sleep.
PRIZE_FILL_PER_RUN = 1
PRIZE_FILL_SINCE = date(2024, 10, 1)
INGEST_STATE_ID = 1


def official_csv_enabled() -> bool:
    """Off restores the old paisapi + Magayo path without a code rollback."""
    return os.getenv("PAIS_OFFICIAL_CSV_ENABLED", "1").strip().lower() not in {"0", "false", "off"}


class PaisIntegrityError(PaisSourceError):
    """CSV disagreed with a stored draw, or a new row failed the rules."""


def _state(db) -> IngestState:
    row = db.get(IngestState, INGEST_STATE_ID)
    if row is None:
        row = IngestState(id=INGEST_STATE_ID, integrity_blocked=False)
        db.add(row)
        db.commit()
    return row


def _quarantine(db, row: CsvDraw | None, reason: str, raw: str) -> None:
    draw_number = row.draw_number if row else None
    existing = db.execute(
        select(DrawQuarantine).where(
            DrawQuarantine.draw_number == draw_number,
            DrawQuarantine.reason == reason,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(
        DrawQuarantine(
            draw_number=draw_number,
            reason=reason[:200],
            raw_row=raw[:4000],
            created_at=utc_now(),
        )
    )
    db.commit()


def _find_existing(db, row: CsvDraw) -> Draw | None:
    found = db.execute(select(Draw).where(Draw.draw_number == row.draw_number)).scalar_one_or_none()
    if found is not None:
        return found
    return db.execute(select(Draw).where(Draw.date == row.draw_date)).scalar_one_or_none()


def _insert_draw(db, row: CsvDraw, file_hash: str) -> None:
    _ensure_draw_id_sequence(db)
    db.add(
        Draw(
            date=row.draw_date,
            numbers=list(row.numbers),
            strong_number=row.strong,
            draw_number=row.draw_number,
            ticket_cost_ils=TICKET_COST_ILS,
            source=PAIS_CSV_SOURCE,
            source_hash=file_hash,
            ingested_at=utc_now(),
        )
    )
    db.commit()


def _apply_rows(db, rows: list[CsvDraw], file_hash: str, result: SyncDrawsResult) -> int:
    """Insert only new modern draws. Never rewrite a stored number set."""
    max_modern = db.execute(
        select(func.max(Draw.draw_number)).where(Draw.date >= MODERN_SERIES_START)
    ).scalar()
    previous = int(max_modern) if max_modern is not None else None
    today = datetime.now(timezone.utc).astimezone().date()
    quarantined = 0
    added = 0
    candidates = [
        row
        for row in rows
        if row.draw_date >= MODERN_SERIES_START and (previous is None or row.draw_number > previous)
    ]
    for row in candidates:
        reason = rejection_reason(row, previous_number=previous, today=today)
        if reason:
            _quarantine(db, row, reason, row.raw)
            quarantined += 1
            continue
        existing = _find_existing(db, row)
        if existing is not None:
            if not numbers_match(list(existing.numbers), int(existing.strong_number), row):
                _quarantine(db, row, "disagrees_with_stored_draw", row.raw)
                quarantined += 1
                continue
            if existing.draw_number is None:
                existing.draw_number = row.draw_number
                existing.source = existing.source or PAIS_CSV_SOURCE
                db.commit()
            previous = row.draw_number
            continue
        try:
            _insert_draw(db, row, file_hash)
        except IntegrityError:
            db.rollback()
            _quarantine(db, row, "insert_conflict", row.raw)
            quarantined += 1
            continue
        added += 1
        previous = row.draw_number
        result.pais_latest_draw_number = row.draw_number
        result.pais_latest_date = row.draw_date.isoformat()
    result.new_draws_added = added
    if quarantined:
        result.errors.append(f"quarantined {quarantined} pais csv rows")
    return quarantined


def _fill_missing_prizes(db, client, rows_by_number: dict[int, CsvDraw]) -> int:
    pending = db.execute(
        select(Draw)
        .where(
            Draw.draw_number.is_not(None),
            Draw.date >= PRIZE_FILL_SINCE,
            or_(Draw.prize_3.is_(None), Draw.jackpot_lotto.is_(None)),
        )
        .order_by(Draw.draw_number.desc())
        .limit(PRIZE_FILL_PER_RUN)
    ).scalars().all()
    filled = 0
    failures = 0
    for draw in pending:
        if draw.draw_number not in rows_by_number:
            continue
        try:
            prizes = fetch_draw_detail(client, int(draw.draw_number))
        except (httpx.HTTPError, PaisSourceError) as exc:
            failures += 1
            mark_pais_error_cooldown()
            logger.error(
                "Pais draw page failed",
                context={"draw_number": draw.draw_number, "error": str(exc)},
            )
            if failures >= PAIS_MAX_FAILURES:
                logger.error("Pais prize fill stopped after repeated error pages")
                break
            continue
        failures = 0
        for key, value in prizes.items():
            setattr(draw, key, value)
        draw.source = PAIS_CSV_SOURCE
        draw.verified_at = utc_now()
        db.commit()
        filled += 1
    return filled


def _draw_still_missing(rows: list[CsvDraw], today: date) -> bool:
    """True the morning after Tue/Thu/Sat when the CSV has not reached that night yet."""
    yesterday = today - timedelta(days=1)
    if yesterday.weekday() not in DRAW_WEEKDAYS or not rows:
        return False
    return max(row.draw_date for row in rows) < yesterday


def sync_official_draws(db, *, allow_magayo: bool) -> SyncDrawsResult:
    result = SyncDrawsResult()
    draws_before = db.execute(select(func.count(Draw.id))).scalar() or 0
    with open_pais_client() as client:
        raw = download_official_csv(client)
        digest = file_sha256(raw)
        parsed = parse_official_csv(raw)
        newest = newest_modern_row(parsed)
        if newest is not None:
            result.pais_latest_draw_number = newest.draw_number
            result.pais_latest_date = newest.draw_date.isoformat()
        state = _state(db)
        needs_prizes = (
            db.execute(
                select(func.count(Draw.id)).where(
                    Draw.prize_3.is_(None),
                    Draw.date >= PRIZE_FILL_SINCE,
                )
            ).scalar()
            or 0
        )
        unchanged = state.csv_sha256 == digest and not state.integrity_blocked and needs_prizes == 0
        if unchanged:
            result.pais_recent = "unchanged"
            logger.info("Pais CSV unchanged — skip")
        else:
            quarantined = _apply_rows(db, parsed, digest, result)
            by_number = {row.draw_number: row for row in parsed}
            filled = _fill_missing_prizes(db, client, by_number)
            result.pais_window = {"added": result.new_draws_added, "updated": filled, "skipped": 0}
            logger.info(
                "Pais CSV applied",
                context={"added": result.new_draws_added, "prizes": filled, "quarantined": quarantined},
            )
            if quarantined:
                state.integrity_blocked = True
                state.integrity_reason = f"quarantined {quarantined} rows"
                db.commit()
                raise PaisIntegrityError(state.integrity_reason)
            state.csv_sha256 = digest
            state.last_success_at = utc_now()
            db.commit()

    if allow_magayo and _draw_still_missing(parsed, datetime.now(timezone.utc).astimezone().date()):
        result.magayo = import_magayo_latest_draw(db)
        logger.info("Magayo fallback after a successful Pais file", context={"magayo": result.magayo})
    else:
        result.magayo = "not_called"

    db_latest = db.execute(select(func.max(Draw.date))).scalar()
    if db_latest:
        result.db_latest_date = db_latest.isoformat()
    draws_after = db.execute(select(func.count(Draw.id))).scalar() or 0
    result.new_draws_added = max(result.new_draws_added, int(draws_after) - int(draws_before))
    return result


def reconcile_last_draws(db, *, limit: int = 20) -> dict:
    """Sunday check: last stored draws must match the official CSV. Pais wins over Magayo."""
    with open_pais_client() as client:
        parsed = parse_official_csv(download_official_csv(client))
    by_number = {row.draw_number: row for row in parsed}
    recent = db.execute(
        select(Draw).where(Draw.date >= MODERN_SERIES_START).order_by(Draw.date.desc()).limit(limit)
    ).scalars().all()
    mismatches: list[str] = []
    for draw in recent:
        if draw.draw_number is None:
            mismatches.append(f"{draw.date} missing draw_number")
            continue
        official = by_number.get(int(draw.draw_number))
        if official is None:
            mismatches.append(f"draw {draw.draw_number} missing from CSV")
            continue
        if not numbers_match(list(draw.numbers), int(draw.strong_number), official):
            mismatches.append(f"draw {draw.draw_number} numbers differ")
            _quarantine(db, official, "reconcile_mismatch", official.raw)
        elif official.draw_date != draw.date:
            mismatches.append(f"draw {draw.draw_number} date differs")
    state = _state(db)
    if mismatches:
        state.integrity_blocked = True
        state.integrity_reason = "; ".join(mismatches)[:500]
        db.commit()
        raise PaisIntegrityError(state.integrity_reason)
    state.integrity_blocked = False
    state.integrity_reason = None
    state.last_success_at = utc_now()
    db.commit()
    return {"checked": len(recent), "integrity_blocked": False}
