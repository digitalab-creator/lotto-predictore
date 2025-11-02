# System Commands Guide ⚓️

May the Flying Spaghetti Monster bless yer system operations! 🍝

## System & Database

### Docker Operations
```sh
# Start the system
docker-compose up -d

# Stop the system
docker-compose down

# Rebuild backend
docker-compose build backend

docker-compose restart backend

# Show Docker disk usage summary (images, containers, volumes, cache)
docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}"

# View logs
docker-compose logs -f backend
docker-compose logs -f cron_service
```

### Database Management
```sh
# List all tables
docker-compose exec db psql -U lotto_user -d lotto_db -c "\dt"

# View recent draws
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT * FROM draws ORDER BY id DESC LIMIT 100;"

# Get latest draw date
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT date FROM draws ORDER BY date DESC LIMIT 1;"

# Clear prediction data
docker-compose exec db psql -U lotto_user -d lotto_db -c "DELETE FROM predictions;"
docker-compose exec db psql -U lotto_user -d lotto_db -c "DELETE FROM prediction_details;"

# View model performance by main/strong model combination
docker-compose exec db psql -U lotto_user -d lotto_db -c "
SELECT
    mm.name AS main_model_name,
    sm.name AS strong_model_name,
    COUNT(*) AS total_predictions,
    (
        SELECT COUNT(*)
        FROM prediction_details pd
        JOIN predictions p2 ON pd.prediction_id = p2.id
        WHERE p2.model_id = p.model_id AND p2.strong_model_id = p.strong_model_id
    ) AS total_prediction_details,
    ROUND(SUM(p.total_prize)::numeric, 2) AS total_prize,
    ROUND(SUM(p.total_cost)::numeric, 2) AS total_cost,
    ROUND(
        CASE 
            WHEN SUM(p.total_cost) = 0 THEN NULL
            ELSE (SUM(p.total_prize)::numeric / NULLIF(SUM(p.total_cost), 0)::numeric)
        END, 4
    ) AS roi_ratio
FROM
    predictions p
JOIN
    models mm ON p.model_id = mm.id
JOIN
    models sm ON p.strong_model_id = sm.id
GROUP BY
    mm.name, sm.name, p.model_id, p.strong_model_id
ORDER BY
    roi_ratio DESC;
"
```

### Database Migrations
```sh
# Downgrade to specific version
docker-compose exec backend alembic downgrade 2b81cd7d248b

# Upgrade to latest version
docker-compose exec backend alembic upgrade head
```

## Data Operations

### Import Draws
```sh
# Import from Pais API
docker-compose exec backend python import_draws_paisapi.py

# Import from Magayo
docker-compose run --rm backend python -m services.import_draws_magayo

# Scrape draw dates
docker-compose run --rm backend python services/scrape_israel_lotto_draw_dates.py
```

### Generate Combinations
```sh
# Generate weekly combinations
docker exec -it lotto-predictore_backend_1 python3 /app/scripts/generate_weekly_combinations.py

# Update weekly winning combinations
docker-compose exec backend python scripts/update_weekly_winning_combinations.py

# Generate weekly tables
docker-compose exec backend python scripts/generate_weekly_tables.py
```

## Communication

### Email Notifications
```sh
# Send test error notification
curl -X POST http://localhost:8001/send-email \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test Email from Lotto Predictor",
    "template_name": "error_notification.html",
    "template_data": {
      "error_message": "This is a test email, matey!",
      "service": "email-service",
      "script": "test_script.py",
      "traceback": "No errors, just a test!"
    }
  }'

# Send pirate-themed test email
curl -X POST http://localhost:8001/send-email \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Test Email from the Pirate Ship!",
    "template_name": "error_notification.html",
    "template_data": {
      "error_message": "This be a test, matey!",
      "service": "Test Service",
      "script": "test_script.py",
      "traceback": "No errors, just rum!"
    }
  }' | cat
```

## Maintenance

### Cache Management
```sh
# Clear all cache files
find /home/orshv/lotto-predictore/shared/cache -name "*.json" -delete

# Clear specific cache (e.g., strong number cache)
rm /home/orshv/lotto-predictore/shared/cache/strong_number_cache.json

# List all cache files
find /home/orshv/lotto-predictore/shared/cache -name "*.json"
```

### Log Management
```sh
# Clear backend logs
docker-compose exec backend sh -c "echo '' > /app/logs/backend_service/backend_service.log"

# View recent backend logs
docker-compose logs backend | tail -30

# Remove old log files
sudo rm /home/orshv/lotto-predictore/logs/backend_service/backend_service.log.2025-06-14

# Run cleanup script
./scripts/cleanup.sh
```

### System Cleanup (Automated)
```sh
# The cron service automatically runs comprehensive system cleanup daily at 2:00 AM
# This includes:
# - Cleaning up old log files
# - Running docker system prune -a -f to free up disk space

# Manually trigger system cleanup
curl -X POST http://localhost:8002/api/cleanup-system

# Check cleanup job status
curl -X GET http://localhost:8002/health
```

## Git Operations 🏴‍☠️

May the Flying Spaghetti Monster guide yer version control! 🍝

### Basic Git Commands
```sh
# Commit and push all changes (interactive - prompts for message, runs pre-commit checks)
source venv/bin/activate && python3 scripts/git_manager.py commit

# Commit with message (bypasses prompt)
source venv/bin/activate && python3 scripts/git_manager.py commit "your commit message"

# Skip pre-commit checks (use sparingly!)
source venv/bin/activate && python3 scripts/git_manager.py commit --no-verify

# Fetch latest commit from remote
python3 scripts/git_manager.py fetch

# Checkout specific commit
python3 scripts/git_manager.py checkout <commit_id>
```

### Environment Setup
```sh
# Required environment variables in .env or .env.development:
GITHUB_REPO_URL=https://github.com/username/repo.git
GIT_AUTHOR_NAME="Yer Pirate Name"
GIT_AUTHOR_EMAIL=pirate@example.com
GIT_BRANCH=main
GITHUB_TOKEN=your_github_personal_access_token
```

### Troubleshooting
```sh
# Check if in git repository
python3 scripts/git_manager.py

# View git root directory
python3 -c "from scripts.git_manager import find_git_root; print(find_git_root())"

# Test repository access
git ls-remote origin
```

### Notes
- Git operations run directly on the host machine, not in Docker
- The git manager script handles authentication automatically using your GitHub token
- It will initialize a git repository if one doesn't exist
- All operations are logged to the logs directory
- Force push is used to ensure remote matches local state
- Commit messages are required for commits

'roi':\s*-\d+(\.\d+)?
'roi':\s*(0(\.\d+)?|[1-9]\d*(\.\d+)?)

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Generate Combinations
```bash
curl http://localhost:8000/generate-combinations
```

### Weekly Combinations Generation (Balanced)
```bash
# Generate weekly combinations with balanced prediction details
docker-compose exec backend curl -X POST http://localhost:8000/cron/generate-weekly-combinations
```

### Check Prediction Balance Status
```bash
# Check current balance of prediction details across models
docker-compose exec backend curl http://localhost:8000/cron/prediction-balance-status
```

### Manual Simulation
```bash
# Run simulation with specific parameters
curl "http://localhost:8000/simulate?train_start=2024-01-01&train_end=2024-12-31&test_count=12&top_n=3"
```

## Prediction Balance System

### How It Works
The weekly combinations generation now includes a **prediction balance system** that:

1. **Analyzes Current Data**: Counts prediction details for each model combination
2. **Prioritizes Underrepresented Models**: Focuses on models with fewer prediction details
3. **Maintains Balance**: Aims to keep ~100 prediction details per model combination
4. **Adaptive Selection**: Automatically selects algorithms that need more data

### Balance Status Endpoint
The `/cron/prediction-balance-status` endpoint provides:

```json
{
  "status": "success",
  "balance_summary": {
    "total_model_combinations": 84,
    "min_prediction_details": 0,
    "max_prediction_details": 480,
    "average_prediction_details": 120.5,
    "models_needing_data": 25,
    "target_details_per_model": 100
  },
  "top_models_needing_data": [
    {
      "main_algo": "sequence_lstm_classifier",
      "strong_algo": "random",
      "current_details": 0,
      "priority_score": 100
    }
  ],
  "main_algorithm_averages": {
    "top_n_frequent_per_position_v2": 96.0,
    "sequence_lstm_classifier": 48.0
  }
}
```

### Benefits
- **Fair Evaluation**: All models get equal opportunity for evaluation
- **Data Quality**: Ensures sufficient data for reliable ROI calculations
- **Performance Tracking**: Better comparison across all algorithms
- **Automatic Management**: No manual intervention needed

### Monitoring Commands
```bash
# Check balance before running weekly generation
docker-compose exec backend curl http://localhost:8000/cron/prediction-balance-status | jq

# Run weekly generation (will prioritize models needing data)
docker-compose exec backend curl -X POST http://localhost:8000/cron/generate-weekly-combinations

# Check balance after running
docker-compose exec backend curl http://localhost:8000/cron/prediction-balance-status | jq
```

## Troubleshooting

### Check Service Status
```bash
# Check if all services are running
docker-compose ps

# Check backend logs
docker-compose logs backend

# Check cron service logs
docker-compose logs cron_service
```

### Database Issues
```bash
# Reset database (WARNING: This will delete all data)
docker-compose down
docker volume rm lotto-predictore_postgres_data
docker-compose up -d

# Check database connection
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT version();"
```

### Algorithm Issues
```bash
# Check available algorithms
docker-compose exec backend curl http://localhost:8000/health | jq '.algorithms'

# Test specific algorithm
curl "http://localhost:8000/simulate?train_start=2024-01-01&train_end=2024-12-31&algorithms=top_n_frequent_per_position_v2"
```
