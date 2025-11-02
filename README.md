# Lotto Predictore ⚓️

Arrr matey! Here be how to keep yer draws fresh and yer database up to date, praisin' the FSM!

## 🏴‍☠️ Historical Draw Import Steps

To fill yer database with all the draws, follow these three steps, as decreed by the pirate code and the FSM:

### 1. Fetch All Draws Up to October 2024 (PaisAPI)

Run this command to fetch all historical draws from the earliest possible up to October 2024:

```sh
docker-compose exec backend python import_draws_paisapi.py
```

---

### 2. Fetch Draws From October 2024 Onward (Magayo API)

Once ye have the old draws, fetch the newer draws (from October 2024 onward) one at a time using the Magayo API:

```sh
docker-compose run --rm backend python import_draws_magayo.py
```

---

### 3. Fetch and Store Each New Draw as It Happens (Cronjob)

After ye be caught up, set up the daily cronjob to fetch and store each new draw as it happens:

```sh
./up_with_cron.sh
```

This will:
- Start yer containers
- Ensure a cronjob is set to fetch the latest draw every day at 3:00 AM
- Log all output to `cron_fetch_latest.log`

---

May yer database be ever complete and yer draws ever fresh, praisin' the FSM and his noodly appendage!

## 🏴‍☠️ Automatic Daily Draw Fetching (Cronjob)

### 1. Set Up the Daily Cronjob

Run this command to bring up yer containers and set the daily cronjob:

```sh
./up_with_cron.sh
```

This will:
- Start yer Docker containers
- Ensure a cronjob is set to fetch the latest draw every day at 3:00 AM
- Log all output to `cron_fetch_latest.log`

---

### 2. Check If the Cronjob Be Workin'

To see if the cronjob be fetchin' draws as the FSM intended, run:

```sh
tail -n 50 cron_fetch_latest.log
```

Ye should see log entries like:
- "Fetching latest draw from Magayo API"
- "Added draw YYYY-MM-DD: [...] + N"
- Or "Draw for YYYY-MM-DD already exists in DB. No action needed."

To see the cron schedule:
```sh
crontab -l
```

---

### 3. Manually Test the Fetch Script

If ye want to fetch the latest draw right now (without waitin' for cron), run:

```sh
docker-compose exec backend python fetch_latest_draw.py
```

Or, to simulate the cronjob exactly:

```sh
cd /home/orshv/lotto-predictore && docker-compose exec backend python fetch_latest_draw.py >> cron_fetch_latest.log 2>&1
```

Then check the log file again to see the results, praisin' the FSM!

---

## 🏴‍☠️ Code Quality Setup

Arrr! Keep yer code clean with pre-commit hooks that run automatically before each commit!

### Initial Setup (Run Once)

**Quick setup:**
```sh
./scripts/setup_pre_commit.sh
```

**Or manual setup:**
```sh
# Install dependencies
pip install -r backend/requirements.txt

# Install pre-commit hooks
pre-commit install
```

### What It Does

Automatically runs:
- **Black** - Code formatting
- **Ruff** - Fast linting
- **isort** - Import organization
- **Bandit** - Security checks

See `docs/pre-commit-setup.md` for full details!

---

May yer draws be ever fresh and yer logs ever clear, matey! If ye run into trouble, consult the log or call for help from the FSM's chosen ones. 