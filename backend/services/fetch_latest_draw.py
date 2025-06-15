import os
from datetime import date
from db import SessionLocal
from models import Draw
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from sqlalchemy import select, desc
import httpx
from logger import logger

logger.info("Arrr! Script started, praisin' the FSM!")
# Load environment variables from .env in project root
load_dotenv()

MAGAYO_API_KEY = os.getenv("MAGAYO_API_KEY")
MAGAYO_GAME_CODE = os.getenv("MAGAYO_GAME_CODE")
MAGAYO_URL = "https://www.magayo.com/api/results.php"

def fetch_latest_draw_magayo():
    params = {
        "api_key": MAGAYO_API_KEY,
        "game": MAGAYO_GAME_CODE,
        "format": "json",
    }
    logger.info("Fetching latest draw from Magayo API")
    resp = httpx.get(MAGAYO_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error", 1) == 303:
        logger.error("API limit reached (error 303) for latest draw. Stopping script.")
        raise SystemExit("API limit reached (error 303) for latest draw.")
    if data.get("error", 1) != 0:
        logger.warning(f"No draw or error: {data}")
        return None
    return data

def get_draw_by_date(db, draw_date):
    return db.execute(select(Draw).where(Draw.date == draw_date)).scalar_one_or_none()

def main():
    db = SessionLocal()
    try:
        data = fetch_latest_draw_magayo()
        if not data:
            logger.info("No data returned for latest draw.")
            return
        results = data.get("results")
        draw_date = data.get("draw")
        if not results or not draw_date:
            logger.warning(f"Incomplete data for latest draw: {data}")
            return
        nums = [int(n) for n in results.split(",") if n.strip().isdigit()]
        if len(nums) < 7:
            logger.warning(f"Not enough numbers for latest draw: {results}")
            return
        win_numbers = nums[:6]
        strong_number = nums[6]
        draw_date_obj = date.fromisoformat(draw_date)
        existing = get_draw_by_date(db, draw_date_obj)
        if existing:
            logger.info(f"Draw for {draw_date} already exists in DB. No action needed.")
            return
        d = Draw(
            date=draw_date_obj,
            numbers=win_numbers,
            strong_number=strong_number,
        )
        try:
            db.add(d)
            db.commit()
            logger.info(f"Added draw {draw_date}: {win_numbers} + {strong_number}")
        except IntegrityError:
            db.rollback()
            logger.info(f"Skipped duplicate draw {draw_date}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error importing draw for {draw_date}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 