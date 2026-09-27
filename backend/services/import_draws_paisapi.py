import httpx
import logging
from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from config import TICKET_COST_ILS
from db import SessionLocal
from models import Draw
from services.draw_prize import (
    PAIS_SOURCE,
    parse_win_table_reg,
    pais_payload_source_hash,
    utc_now,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

PAISAPI_BY_DATES = "https://paisapi.azurewebsites.net/lotto/byDates/{from_date}/{to_date}"
PAISAPI_BY_ID = "https://paisapi.azurewebsites.net/lotto/byID/{from_id}/{to_id}"
PAISAPI_RECENT = "https://paisapi.azurewebsites.net/lotto/recent"
START_DATE = date(2007, 1, 1)


def fetch_draws_by_dates(from_date: date, to_date: date) -> list:
    url = PAISAPI_BY_DATES.format(from_date=from_date.isoformat(), to_date=to_date.isoformat())
    logging.info("Fetching draws from %s to %s via %s", from_date, to_date, url)
    resp = httpx.get(url, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def fetch_draws_by_id(from_id: int, to_id: int) -> list:
    url = PAISAPI_BY_ID.format(from_id=from_id, to_id=to_id)
    logging.info("Fetching draws by lottery id %s..%s", from_id, to_id)
    resp = httpx.get(url, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def fetch_recent_draw() -> dict | None:
    resp = httpx.get(PAISAPI_RECENT, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) else None


def next_month(dt: date) -> date:
    if dt.month == 12:
        return date(dt.year + 1, 1, 1)
    return date(dt.year, dt.month + 1, 1)


def _draw_date_from_payload(draw: dict) -> date | None:
    draw_date = draw.get("date") or draw.get("drawDate")
    if not draw_date:
        return None
    return date.fromisoformat(str(draw_date)[:10])


def apply_pais_payload(db, payload: dict) -> str:
    """
    Insert or update a draw from Pais API JSON.
    Returns: added | updated | skipped
    """
    win_numbers = payload.get("winNumbers")
    strong_number = payload.get("strongNumber")
    draw_date = _draw_date_from_payload(payload)
    if not (win_numbers and strong_number is not None and draw_date):
        logging.warning("Skipping incomplete draw payload: %s", payload)
        return "skipped"

    prizes = parse_win_table_reg(payload)
    if not prizes:
        logging.warning("Skipping draw without winTableReg prizes: %s", draw_date)
        return "skipped"

    source_hash = pais_payload_source_hash(payload)
    draw_number = payload.get("_id")
    if draw_number is not None:
        draw_number = int(draw_number)

    existing = db.execute(select(Draw).where(Draw.date == draw_date)).scalar_one_or_none()
    if existing is None and draw_number is not None:
        existing = db.execute(select(Draw).where(Draw.draw_number == draw_number)).scalar_one_or_none()

    def _apply_to_row(row: Draw) -> str:
        if row.source_hash == source_hash:
            return "skipped"
        row.numbers = list(win_numbers)
        row.strong_number = int(strong_number)
        if draw_number is not None:
            row.draw_number = draw_number
        for key, val in prizes.items():
            setattr(row, key, val)
        row.ticket_cost_ils = TICKET_COST_ILS
        row.source = PAIS_SOURCE
        row.source_hash = source_hash
        row.ingested_at = utc_now()
        db.commit()
        return "updated"

    if existing:
        return _apply_to_row(existing)

    row = Draw(
        date=draw_date,
        numbers=list(win_numbers),
        strong_number=int(strong_number),
        draw_number=draw_number,
        ticket_cost_ils=TICKET_COST_ILS,
        source=PAIS_SOURCE,
        source_hash=source_hash,
        ingested_at=utc_now(),
        **prizes,
    )
    db.add(row)
    try:
        db.commit()
        return "added"
    except IntegrityError as exc:
        db.rollback()
        logging.warning("Insert conflict for draw %s: %s", draw_date, exc.orig)
        existing = db.execute(select(Draw).where(Draw.date == draw_date)).scalar_one_or_none()
        if existing is None and draw_number is not None:
            existing = db.execute(select(Draw).where(Draw.draw_number == draw_number)).scalar_one_or_none()
        if existing is None:
            logging.error("Could not resolve IntegrityError for draw %s", draw_date)
            return "skipped"
        return _apply_to_row(existing)


def sync_by_dates(db, start: date, end_exclusive: date) -> tuple[int, int, int]:
    added = updated = skipped = 0
    batch_start = start
    while batch_start < end_exclusive:
        batch_end = next_month(batch_start)
        if batch_end > end_exclusive:
            batch_end = end_exclusive
        try:
            draws = fetch_draws_by_dates(batch_start, batch_end - timedelta(days=1))
        except httpx.HTTPError as exc:
            logging.error("Pais byDates failed for %s..%s: %s", batch_start, batch_end, exc)
            batch_start = batch_end
            continue
        logging.info("Fetched %s draws for %s to %s", len(draws), batch_start, batch_end)
        for payload in draws:
            result = apply_pais_payload(db, payload)
            if result == "added":
                added += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1
        batch_start = batch_end
    return added, updated, skipped


def sync_by_id_range(db, from_id: int, to_id: int) -> tuple[int, int, int]:
    if from_id > to_id:
        return 0, 0, 0
    added = updated = skipped = 0
    chunk = 50
    current = from_id
    while current <= to_id:
        end = min(current + chunk - 1, to_id)
        try:
            draws = fetch_draws_by_id(current, end)
        except httpx.HTTPError as exc:
            logging.error("Pais byID failed for %s..%s: %s", current, end, exc)
            current = end + 1
            continue
        for payload in draws:
            result = apply_pais_payload(db, payload)
            if result == "added":
                added += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1
        current = end + 1
    return added, updated, skipped


def _ensure_draw_id_sequence(db) -> None:
    """Fix serial drift after manual/legacy imports (avoids draws_pkey collisions)."""
    db.execute(
        text(
            "SELECT setval(pg_get_serial_sequence('draws', 'id'), "
            "COALESCE((SELECT MAX(id) FROM draws), 1))"
        )
    )
    db.commit()


def main():
    end_exclusive = date.today() + timedelta(days=1)
    db = SessionLocal()
    try:
        _ensure_draw_id_sequence(db)
        a, u, s = sync_by_dates(db, START_DATE, end_exclusive)
        logging.info("byDates import: added=%s updated=%s skipped=%s", a, u, s)

        recent = fetch_recent_draw()
        max_id = db.execute(select(Draw.draw_number).order_by(Draw.draw_number.desc()).limit(1)).scalar_one_or_none()
        latest_api_id = int(recent["_id"]) if recent and recent.get("_id") else None
        if latest_api_id is not None:
            next_id = (max_id or 0) + 1
            if next_id <= latest_api_id:
                a2, u2, s2 = sync_by_id_range(db, next_id, latest_api_id)
                logging.info(
                    "byID catch-up %s..%s: added=%s updated=%s skipped=%s",
                    next_id,
                    latest_api_id,
                    a2,
                    u2,
                    s2,
                )
    finally:
        db.close()


if __name__ == "__main__":
    main()
