import os
import httpx
import logging
from datetime import date, timedelta
from db import SessionLocal
from models import Draw
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from sqlalchemy import select, desc
import json

# Load environment variables from .env in project root
load_dotenv()  # This loads .env from the current working directory, which is /app

print("ENV FILE DEBUG:", os.path.abspath('.'), os.listdir('.'))
print("MAGAYO_API_KEY:", os.getenv("MAGAYO_API_KEY"))
print("MAGAYO_GAME_CODE:", os.getenv("MAGAYO_GAME_CODE"))

MAGAYO_API_KEY = os.getenv("MAGAYO_API_KEY")
MAGAYO_GAME_CODE = os.getenv("MAGAYO_GAME_CODE")

if not MAGAYO_API_KEY or not MAGAYO_GAME_CODE:
    raise RuntimeError("MAGAYO_API_KEY and MAGAYO_GAME_CODE must be set in .env, praisin' the FSM!")

MAGAYO_URL = "https://www.magayo.com/api/results.php"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

def fetch_draw_magayo(draw_date):
    params = {
        "api_key": MAGAYO_API_KEY,
        "game": MAGAYO_GAME_CODE,
        "draw": draw_date.isoformat(),
        "format": "json",
    }
    logging.info(f"Fetching draw for {draw_date} from Magayo API")
    resp = httpx.get(MAGAYO_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error", 1) == 303:
        logging.error(f"API limit reached (error 303) for {draw_date}. Stopping script.")
        raise SystemExit(f"API limit reached (error 303) for {draw_date}. Latest date in DB: {draw_date}")
    if data.get("error", 1) != 0:
        logging.warning(f"No draw or error for {draw_date}: {data}")
        return None
    return data

def get_latest_draw_date(db):
    latest = db.execute(select(Draw.date).order_by(desc(Draw.date))).scalar()
    return latest

def main():
    db = SessionLocal()
    try:
        added, skipped = 0, 0
        # Load draw dates from JSON
        with open('israel_lotto_draw_dates.json', 'r', encoding='utf-8') as f:
            all_draw_dates = [date.fromisoformat(d) for d in json.load(f)]
        latest_date = get_latest_draw_date(db)
        if latest_date:
            draw_dates = [d for d in all_draw_dates if d > latest_date]
            logging.info(f"Most recent draw in DB: {latest_date}. Fetching {len(draw_dates)} new draws.")
        else:
            draw_dates = all_draw_dates
            logging.info(f"No draws in DB. Fetching all {len(draw_dates)} draws from JSON.")
        for curr_date in draw_dates:
            data = fetch_draw_magayo(curr_date)
            if data:
                try:
                    results = data.get("results")
                    draw_date = data.get("draw")
                    if not results or not draw_date:
                        logging.warning(f"Incomplete data for {curr_date}: {data}")
                        continue
                    nums = [int(n) for n in results.split(",") if n.strip().isdigit()]
                    if len(nums) < 7:
                        logging.warning(f"Not enough numbers for {curr_date}: {results}")
                        continue
                    win_numbers = nums[:6]
                    strong_number = nums[6]
                    d = Draw(
                        date=date.fromisoformat(draw_date),
                        numbers=win_numbers,
                        strong_number=strong_number,
                    )
                    db.add(d)
                    db.commit()
                    added += 1
                    logging.info(f"Added draw {draw_date}: {win_numbers} + {strong_number}")
                except IntegrityError:
                    db.rollback()
                    skipped += 1
                    logging.info(f"Skipped duplicate draw {draw_date}")
                except Exception as e:
                    db.rollback()
                    logging.error(f"Error importing draw for {curr_date}: {e}")
        logging.info(f"Magayo import complete. Added: {added}, Skipped: {skipped}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 