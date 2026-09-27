import os
from datetime import date

import httpx
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import SessionLocal
from logger import logger
from models import Draw
from services.draw_prize import MAGAYO_SOURCE, utc_now
from services.import_draws_paisapi import _ensure_draw_id_sequence

load_dotenv()

MAGAYO_API_KEY = os.getenv("MAGAYO_API_KEY")
MAGAYO_GAME_CODE = os.getenv("MAGAYO_GAME_CODE")
MAGAYO_URL = "https://www.magayo.com/api/results.php"


def fetch_latest_draw_magayo():
    if not MAGAYO_API_KEY or not MAGAYO_GAME_CODE:
        logger.info("Magayo not configured (MAGAYO_API_KEY / MAGAYO_GAME_CODE missing)")
        return None
    params = {
        "api_key": MAGAYO_API_KEY,
        "game": MAGAYO_GAME_CODE,
        "format": "json",
    }
    logger.info("Fetching latest draw from Magayo API")
    resp = httpx.get(MAGAYO_URL, params=params, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error", 1) == 303:
        logger.error("API limit reached (error 303) for latest draw.")
        raise Exception("API limit reached (error 303) for latest draw.")
    if data.get("error", 1) != 0:
        logger.warning(f"No draw or Magayo error: {data}")
        return None
    return data


def get_draw_by_date(db, draw_date):
    return db.execute(select(Draw).where(Draw.date == draw_date)).scalar_one_or_none()


def import_magayo_latest_draw(db) -> str:
    """
    Add the latest Magayo result when that draw date is not in the DB yet.
    Does not overwrite Pais rows (numbers-only fallback).
    Returns: added | skipped | unconfigured | incomplete
    """
    data = fetch_latest_draw_magayo()
    if data is None and (not MAGAYO_API_KEY or not MAGAYO_GAME_CODE):
        return "unconfigured"
    if not data:
        return "skipped"

    results = data.get("results")
    draw_date = data.get("draw")
    if not results or not draw_date:
        logger.warning(f"Incomplete Magayo payload: {data}")
        return "incomplete"

    nums = [int(n) for n in results.split(",") if n.strip().isdigit()]
    if len(nums) < 7:
        logger.warning(f"Not enough numbers in Magayo result: {results}")
        return "incomplete"

    win_numbers = nums[:6]
    strong_number = nums[6]
    draw_date_obj = date.fromisoformat(str(draw_date)[:10])
    existing = get_draw_by_date(db, draw_date_obj)
    if existing:
        logger.info(f"Draw for {draw_date_obj} already in DB — Magayo skipped")
        return "skipped"

    _ensure_draw_id_sequence(db)
    row = Draw(
        date=draw_date_obj,
        numbers=win_numbers,
        strong_number=strong_number,
        source=MAGAYO_SOURCE,
        ingested_at=utc_now(),
    )
    try:
        db.add(row)
        db.commit()
        logger.info(f"Magayo added draw {draw_date_obj}: {win_numbers} + {strong_number}")
        return "added"
    except IntegrityError:
        db.rollback()
        logger.info(f"Magayo duplicate draw {draw_date_obj}")
        return "skipped"
    except Exception as exc:
        db.rollback()
        logger.error(f"Magayo import error for {draw_date_obj}: {exc}")
        raise


def main():
    """CLI entry — delegates to full incremental sync."""
    from services.sync_draws import main as sync_main

    return sync_main()


if __name__ == "__main__":
    main()
