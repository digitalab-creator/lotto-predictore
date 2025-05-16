import httpx
import logging
from datetime import date, timedelta
from db import SessionLocal
from models import Draw
from sqlalchemy.exc import IntegrityError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

PAISAPI_URL = "https://paisapi.azurewebsites.net/lotto/byDates/{to_date}/{from_date}"
START_DATE = date(2007, 1, 1)
END_DATE = date(2024, 10, 1)  # exclusive upper bound for part 1


def fetch_draws(from_date, to_date):
    url = PAISAPI_URL.format(from_date=from_date, to_date=to_date)
    logging.info(f"Fetching draws from {from_date} to {to_date} via {url}")
    resp = httpx.get(url)
    resp.raise_for_status()
    return resp.json()


def next_month(dt):
    if dt.month == 12:
        return date(dt.year + 1, 1, 1)
    else:
        return date(dt.year, dt.month + 1, 1)


def main():
    db = SessionLocal()
    try:
        added, skipped = 0, 0
        batch_start = START_DATE
        while batch_start < END_DATE:
            batch_end = next_month(batch_start)
            if batch_end > END_DATE:
                batch_end = END_DATE
            draws = fetch_draws(batch_start.isoformat(), batch_end.isoformat())
            logging.info(f"Fetched {len(draws)} draws for {batch_start} to {batch_end}")
            for draw in draws:
                try:
                    win_numbers = draw.get('winNumbers')
                    strong_number = draw.get('strongNumber')
                    draw_date = draw.get('date') or draw.get('drawDate')
                    if not (win_numbers and strong_number and draw_date):
                        logging.warning(f"Skipping incomplete draw: {draw}")
                        continue
                    d = Draw(
                        date=date.fromisoformat(draw_date[:10]),
                        numbers=win_numbers,
                        strong_number=int(strong_number),
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
                    logging.error(f"Error importing draw {draw}: {e}")
            batch_start = batch_end
        logging.info(f"Import complete. Added: {added}, Skipped: {skipped}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 