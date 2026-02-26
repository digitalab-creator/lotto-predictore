# Lotto Predictor

A lottery prediction system that imports historical draws from Pais and Magayo APIs, stores them in PostgreSQL, and runs prediction algorithms. It can send weekly result emails via a separate email service.

## What it does

- Imports historical lottery draws (Pais API up to Oct 2024, Magayo API from Oct 2024 onward).
- Stores draws in PostgreSQL and runs algorithms for predictions.
- Optional: cron job to fetch the latest draw daily; email service to send weekly summaries.

## How to use

### 1. Import historical draws (Pais API, up to October 2024)

From the project root:

```sh
docker compose exec backend python services/import_draws_paisapi.py
```

(Backend container has `WORKDIR /app`; scripts live under `backend/services/`.)

### 2. Import draws from October 2024 onward (Magayo API)

```sh
docker compose run --rm backend python services/import_draws_magayo.py
```

Set `MAGAYO_API_KEY` and `MAGAYO_GAME_CODE` in your environment (e.g. in `backend/.env`).

### 3. Fetch the latest draw (one-off)

```sh
docker compose exec backend python services/fetch_latest_draw.py
```

### 4. Run daily fetch via cron (optional)

Set up a cron job on your host that runs the fetch command, for example:

```sh
docker compose exec backend python services/fetch_latest_draw.py
```

Run `docker compose up -d` so the backend is up when cron runs. Log output to a file if needed (e.g. `>> cron_fetch_latest.log 2>&1`).

## Environment

- Copy `backend/.env.example` to `backend/.env` (create one if missing) and set:
  - `DATABASE_URL` — PostgreSQL connection string (e.g. `postgresql+psycopg2://lotto_user:lotto_pass@db:5432/lotto_db`).
  - `MAGAYO_API_KEY`, `MAGAYO_GAME_CODE` — for Magayo API.
  - `BACKEND_URL` — used by cron service (e.g. `http://backend:8000`).
- Email service has its own `.env.example` in `email-service/` for SMTP and recipient settings.

## Project layout

- `backend/` — API, models, algorithms, import scripts (`services/import_draws_*.py`, `services/fetch_latest_draw.py`), Alembic migrations.
- `cron/` — Cron job runner and error handling.
- `email-service/` — Email sending for weekly summaries and notifications.
- `shared/` — Shared logging and cache utilities.
- `docker-compose.yml` — Defines backend, db, cron, and email-service.
