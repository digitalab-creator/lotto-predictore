# System Commands Guide ⚓️

May the Flying Spaghetti Monster bless yer system operations! 🍝

## System & Database

### Docker Operations
```sh
# Start production stack (~1.3 CPU / ~1.5 GiB caps in docker-compose.yml; backend-debug is off unless profile debug)
docker-compose up -d

# Optional dev API on :8877 (extra ~0.15 CPU / 192 MiB)
docker compose --profile debug up -d backend-debug

# Dynamic limits from host load (busy host = small lotto; clear host = larger lotto)
sudo ./scripts/install-resource-governor.sh
python3 scripts/resource_governor.py --dry-run

# Stop the system
docker-compose down

# Rebuild backend
docker-compose build backend

docker-compose restart backend

# Show Docker disk usage summary (images, containers, volumes, cache)
docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}"
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
    mm.name, sm.name
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
# The cron service automatically runs log cleanup daily at 2:00 AM

# Manually trigger system cleanup
curl -X POST http://localhost:8002/api/cleanup-system

# Check cleanup job status
curl -X GET http://localhost:8002/health
```

## Git Operations 🏴‍☠️

May the Flying Spaghetti Monster guide yer version control! 🍝

### Basic Git Commands
```sh
# Commit and push all changes
source venv/bin/activate && python3 scripts/git_manager.py commit

# Fetch latest commit from remote
python3 scripts/git_manager.py fetch

# Checkout specific commit
python3 scripts/git_manager.py checkout <commit_id>

# Quick commit and push (with optional messdage)
python3 scripts/git_manager.py commit_and_push "refactore cron service, add db backup"
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
