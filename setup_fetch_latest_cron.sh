#!/bin/bash
# Arrr! This script sets up a daily cronjob to fetch the latest lotto draw, praisin' the FSM!
# It logs output to cron_fetch_latest.log in the project root.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_LOG="$PROJECT_DIR/cron_fetch_latest.log"
CRON_JOB="0 3 * * * cd $PROJECT_DIR && docker-compose exec backend python fetch_latest_draw.py >> $CRON_LOG 2>&1"

# Check if the cron job already exists
(crontab -l 2>/dev/null | grep -F -q "fetch_latest_draw.py")
if [ $? -eq 0 ]; then
    echo "Cronjob already exists, praisin' the FSM!"
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cronjob added, matey!"
fi

echo "Current crontab, yarrr:"
crontab -l 