# Monitoring Commands

## Monitor Scheduled Job Status

**Monitor a specific job (replace JOB_ID):**
```bash
# Get job status
curl -s http://localhost:8002/api/schedule/JOB_ID | python3 -m json.tool

# Watch job status (updates every 5 seconds)
watch -n 5 'curl -s http://localhost:8002/api/schedule/JOB_ID | python3 -m json.tool'
```

**Monitor all scheduled jobs:**
```bash
# Get all scheduled jobs
curl -s http://localhost:8002/api/schedule | python3 -m json.tool

# Watch all scheduled jobs (updates every 5 seconds)
watch -n 5 'curl -s http://localhost:8002/api/schedule | python3 -m json.tool'
```

## Monitor Backend Cron Job Status

**Check cron job execution status in database:**
```bash
curl -s http://localhost:8000/cron/status | python3 -m json.tool
```

**Watch cron status (updates every 10 seconds):**
```bash
watch -n 10 'curl -s http://localhost:8000/cron/status | python3 -m json.tool'
```

## Monitor Backend Logs

**Tail backend logs for weekly combinations:**
```bash
# Docker logs
docker logs -f lotto-predictore_backend_1 | grep -i "weekly\|grid_search\|optimized"

# Or from log files
tail -f /home/orshv/lotto-predictore/logs/backend_service/backend_service.log | grep -i "weekly\|grid_search\|optimized"
```

## Monitor Scheduler Status

**Check all scheduled jobs (system + manual):**
```bash
curl -s http://localhost:8002/api/scheduler-status | python3 -m json.tool
```

**Watch scheduler status:**
```bash
watch -n 30 'curl -s http://localhost:8002/api/scheduler-status | python3 -m json.tool'
```

## Complete Monitoring Workflow

**1. Schedule the job and save job ID:**
```bash
JOB_ID=$(curl -s -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "✅ Job scheduled: $JOB_ID"
```

**2. Monitor job status in one terminal:**
```bash
watch -n 5 "echo '=== Scheduled Job Status ===' && \
curl -s http://localhost:8002/api/schedule/$JOB_ID | python3 -m json.tool && \
echo '' && echo '=== Cron Status ===' && \
curl -s http://localhost:8000/cron/status | python3 -c \"import sys, json; d=json.load(sys.stdin); print('Last run:', d.get('jobs', {}).get('generate-weekly-combinations-optimized', {}).get('last_success', 'N/A'))\""
```

**3. Monitor logs in another terminal:**
```bash
docker logs -f lotto-predictore_backend_1 2>&1 | grep -E "weekly|grid_search|optimized|FSM"
```

