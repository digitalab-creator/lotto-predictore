**Lottery Prediction & Simulation Platform**

---

### 🌎 Project Overview:

A smart lottery analysis and prediction system that uses historical draw data to generate weekly ticket combinations based on statistically frequent numbers per position. The platform includes a dashboard, simulation engine, automatic notification system, and full tracking and versioning of all algorithmic changes.

---

### 📊 Core Features:

1. **Historical Draw Database**

   * Import all past draw results via API (`https://paisapi.azurewebsites.net/lotto/byDates/{to}/{from}`).
   * Save draw date, 6 numbers, and strong number.

2. **Algorithm Engine**

   * Analyze number frequency by position (1st through 6th).
   * Extract top N (default: 3) frequent numbers per position.
   * Generate 8 optimal combinations based on variations of top numbers.
   * Select top strong number(s) by frequency.

3. **Simulation Engine**

   * Run simulations for a given algorithm version over a date range.
   * Calculate: number of hits per line, prize per line, overall profit/loss, ROI.
   * Support different strategies/algorithms.
   * Save simulation run metadata and results.

4. **Real-world Prediction Output**

   * Auto-run generation each week before the next draw (via cronjob).
   * Email or Telegram delivery of 8 recommended lines.
   * Log which combinations were used, when, and which algorithm version.

5. **Performance Dashboard** (React + Tailwind preferred)

   * Overview of current and past prediction performance.
   * Filter by algorithm, date range, ROI, hit rate.
   * Table/chart of weekly performance.

6. **Versioning & Change Tracking**

   * Track every change to the prediction logic or parameters.
   * Each change tagged with a version and explanation.
   * Compare performance across versions.

7. **Submission Log & Prize Recording**

   * Log every line submitted in reality.
   * Log number of hits and prize for each line.
   * Track cumulative winnings vs. costs.

---

### 📊 Database Schema (Suggested Tables)

* **draws** (`id`, `date`, `numbers[]`, `strong_number`)
* **generated\_combinations** (`id`, `algorithm_id`, `generated_at`, `numbers[]`, `strong`, `version`, `used_in_real_draw`)
* **results** (`combination_id`, `draw_id`, `hits`, `strong_hit`, `prize`)
* **strategies** (`id`, `name`, `description`, `version`, `created_at`, `notes`)
* **simulations** (`id`, `strategy_id`, `start_date`, `end_date`, `sim_type`, `rows_generated`, `avg_hits`, `total_prize`, `roi`, `notes`)
* **strategy\_changes\_log** (`id`, `strategy_id`, `change_type`, `description`, `timestamp`)
* **user\_actions\_log** (`id`, `action_type`, `details`, `timestamp`)

---

### ⚖️ MVP Goals (for immediate delivery)

* guess enough numbers correct (3? 4?) for positive roi over time after 3 months while filling 1 tickert 8 tables per week

---

### ⌚ Stack Recommendations

* Backend: Python (FastAPI) or Node.js (Express)
* DB: PostgreSQL (preferred for analysis) or MariaDB
* Frontend: Next.js + Tailwind + Chart.js/Recharts
* Infra: Docker + cron + Supabase (optional for auth/storage)

---

### 📆 Weekly Workflow (Automated)

1. Fetch all past draws up to this week.
2. Run current strategy (version X) to generate 8 lines.
3. Send numbers to configured channels.
4. Log output (version + lines).
5. After result published: manually or automatically fetch result, compare to lines, log hits + prizes.

---

### 🌟 Bonus Ideas (Future Phases)

* ML model to recommend combinations beyond frequency.
* Compare "hot/cold" strategies or mix-ins.
* Optimization module: simulate over parameter sets.
* Multi-user support.
* Gamification for fun.

---

*Written for technical implementation. Suitable for splitting into tasks in Cursor, Jira, Notion, or Trello.*
