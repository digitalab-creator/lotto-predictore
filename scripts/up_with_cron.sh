#!/bin/bash
# Arrr! This script brings up yer containers and ensures the fetch cronjob is active, praisin' the FSM!

set -e

cd "$(dirname "$0")"

echo "🏴‍☠️ Bringing up containers..."
docker-compose down
docker-compose up -d
echo "🏴‍☠️ Checking/setting up fetch cronjob..."
./setup_fetch_latest_cron.sh 