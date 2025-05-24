import os
from datetime import date
from db import SessionLocal
from models import Draw
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from sqlalchemy import select, desc
import httpx
from services.logger import dh_log  # Arrr, use the pirate logger!
dh_log("Arrr! Script started, praisin' the FSM!", level="INFO")
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
    dh_log(f"Fetching latest draw from Magayo API", level="INFO")
    resp = httpx.get(MAGAYO_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error", 1) == 303:
        dh_log(f"API limit reached (error 303) for latest draw. Stopping script.", level="ERROR")
        raise SystemExit(f"API limit reached (error 303) for latest draw.")
    if data.get("error", 1) != 0:
        dh_log(f"No draw or error: {data}", level="WARNING")
        return None
    return data

def get_draw_by_date(db, draw_date):
    return db.execute(select(Draw).where(Draw.date == draw_date)).scalar_one_or_none()

def main():
    db = SessionLocal()
    try:
        data = fetch_latest_draw_magayo()
        if not data:
            dh_log(f"No data returned for latest draw.", level="INFO")
            return
        results = data.get("results")
        draw_date = data.get("draw")
        if not results or not draw_date:
            dh_log(f"Incomplete data for latest draw: {data}", level="WARNING")
            return
        nums = [int(n) for n in results.split(",") if n.strip().isdigit()]
        if len(nums) < 7:
            dh_log(f"Not enough numbers for latest draw: {results}", level="WARNING")
            return
        win_numbers = nums[:6]
        strong_number = nums[6]
        draw_date_obj = date.fromisoformat(draw_date)
        existing = get_draw_by_date(db, draw_date_obj)
        if existing:
            dh_log(f"Draw for {draw_date} already exists in DB. No action needed.", level="INFO")
            return
        d = Draw(
            date=draw_date_obj,
            numbers=win_numbers,
            strong_number=strong_number,
        )
        try:
            db.add(d)
            db.commit()
            dh_log(f"Added draw {draw_date}: {win_numbers} + {strong_number}", level="INFO")
        except IntegrityError:
            db.rollback()
            dh_log(f"Skipped duplicate draw {draw_date}", level="INFO")
        except Exception as e:
            db.rollback()
            dh_log(f"Error importing draw for {draw_date}: {e}", level="ERROR")
    finally:
        db.close()

if __name__ == "__main__":
    main() 