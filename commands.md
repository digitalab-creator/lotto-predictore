# Lotto Predictor API Commands

Praisin' the FSM! 🍝⚓

## Quick Start: Schedule & Monitor Weekly Job

### Schedule Weekly Job for 2 Minutes

**Option 1: Via Cron Service API (if cron service is healthy)**
```bash
# First check if cron service is responding
curl -s --max-time 3 http://localhost:8002/health > /dev/null && \
JOB_ID=$(curl -s --max-time 10 -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])") && \
echo "✅ Job scheduled: $JOB_ID" || echo "❌ Cron service not responding - use Option 2"
```

**Option 2: Direct Backend Call with Delay (works even if cron service is down)**
```bash
# Schedule job directly via backend (runs in background)
nohup bash -c 'sleep 120 && curl -s -X POST http://localhost:8000/cron/generate-weekly-combinations-optimized -H "Content-Type: application/json" > /tmp/weekly_job_result.json 2>&1' &
echo "✅ Job scheduled to run in 2 minutes (PID: $!)"
echo "Monitor with: tail -f /tmp/weekly_job_result.json"
```

**Option 3: Simple Background Script (most reliable)**
```bash
# Create and run scheduling script
cat > /tmp/schedule_weekly.sh << 'EOF'
#!/bin/bash
echo "⏰ Waiting 2 minutes before triggering weekly job..."
sleep 120
echo "🚀 Triggering weekly job at $(date)"
curl -X POST http://localhost:8000/cron/generate-weekly-combinations-optimized \
  -H "Content-Type: application/json" \
  -w "\n⏱️  Response time: %{time_total}s\n" \
  | python3 -m json.tool
EOF
chmod +x /tmp/schedule_weekly.sh
nohup /tmp/schedule_weekly.sh > /tmp/weekly_job.log 2>&1 &
echo "✅ Job scheduled (PID: $!)"
echo "Monitor with: tail -f /tmp/weekly_job.log"
```

### Monitor Job Status

**⚠️ Note: If cron service (port 8002) is unhealthy, use these alternatives:**

**Option A: Monitor Backend Logs (Recommended - Never Gets Stuck)**
```bash
# Real-time backend logs filtered for weekly job (with line breaks between matches)
docker logs -f lotto-predictore_backend_1 2>&1 | grep --line-buffered -E "weekly|grid_search|optimized|FSM|Arrr" | while IFS= read -r line; do echo "$line"; echo ""; done

# Alternative: Using sed to add blank line after each match
docker logs -f lotto-predictore_backend_1 2>&1 | grep --line-buffered -E "weekly|grid_search|optimized|FSM|Arrr" | sed 'a\'
```

**Option B: Monitor Log File (If using Option 2/3)**
```bash
# Monitor the scheduling script log
tail -f /tmp/weekly_job.log

# Or monitor the result file
tail -f /tmp/weekly_job_result.json
```

**Option C: Check Cron Status in Database (With Timeout)**
```bash
# Use timeout to prevent hanging
timeout 5 curl -s http://localhost:8000/cron/status | python3 -m json.tool || echo "Backend not responding"

# Or use watch with timeout
watch -n 10 'timeout 5 curl -s http://localhost:8000/cron/status | python3 -m json.tool || echo "Timeout or error"'
```

**Option D: Monitor Process Status**
```bash
# Check if scheduling script is still running
ps aux | grep -E "schedule_weekly|weekly_job" | grep -v grep

# Check when it will trigger (if using sleep)
ps aux | grep "sleep 120" | grep -v grep
```

**Option E: Simple Status Check (No Watch - Run Manually)**
```bash
# Check cron job status (run this manually every few seconds)
curl -s --max-time 5 http://localhost:8000/cron/status | python3 -m json.tool

# Check backend health
curl -s --max-time 5 http://localhost:8000/health | python3 -m json.tool
```

**Option F: Check if LSTM/Grid Search is Working or Stuck**
```bash
# Quick check script (no hanging)
./scripts/check_lstm_status.sh

# Or run it continuously
watch -n 10 ./scripts/check_lstm_status.sh
```

**Option G: Monitor Multiple Things at Once**
```bash
# Create a monitoring script that won't hang
cat > /tmp/monitor_weekly.sh << 'EOF'
#!/bin/bash
while true; do
  clear
  echo "=== Weekly Job Monitor ==="
  echo "Time: $(date)"
  echo ""
  echo "--- Process Status ---"
  ps aux | grep -E "schedule_weekly|sleep 120" | grep -v grep || echo "No scheduling process found"
  echo ""
  echo "--- Backend Health ---"
  timeout 3 curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool | head -10 || echo "Backend timeout"
  echo ""
  echo "--- Cron Status (last 5 jobs) ---"
  timeout 3 curl -s http://localhost:8000/cron/status 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); jobs=d.get('jobs',{}); [print(f\"{k}: {v.get('status', 'N/A')} - Last: {v.get('last_success', 'Never')}\") for k,v in list(jobs.items())[:5]]" || echo "Timeout"
  echo ""
  echo "--- Recent Logs (last 3 lines) ---"
  tail -3 /tmp/weekly_job.log 2>/dev/null || echo "No log file yet"
  echo ""
  echo "Press Ctrl+C to stop"
  sleep 5
done
EOF
chmod +x /tmp/monitor_weekly.sh
/tmp/monitor_weekly.sh
```

**Option H: Quick Manual Checks (No Scripts) - BEST WAY TO CHECK**

**1. Check CPU Usage (MOST RELIABLE - if > 0%, it's working!):**
```bash
docker stats --no-stream lotto-predictore_backend_1
# Look for CPUPerc column - if > 0%, process is working!
# If 0% for > 5 minutes, might be stuck
```

**2. Check Recent Log Activity:**
```bash
# Last 5 minutes
docker logs --since 5m lotto-predictore_backend_1 2>&1 | grep -E "FSM GRID|evaluation|strong algo|Loaded existing" | tail -10

# Or just check if ANY logs in last 2 minutes
docker logs --since 2m lotto-predictore_backend_1 2>&1 | wc -l
# If > 0, process is generating logs (working)
```

**3. Check Model File Activity:**
```bash
docker exec lotto-predictore_backend_1 find /app/models -type f -mmin -5 2>/dev/null | head -5
# If files listed, model files are being accessed (working)
```

**4. Check Last Log Timestamp:**
```bash
docker logs --tail 1 lotto-predictore_backend_1 2>&1 | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"
# Compare with current time - if < 5 minutes ago, likely working
```

**5. One-Liner Quick Check:**
```bash
# Check CPU + recent logs in one command
echo "CPU: $(docker stats --no-stream lotto-predictore_backend_1 --format '{{.CPUPerc}}')" && \
echo "Recent logs (last 2min): $(docker logs --since 2m lotto-predictore_backend_1 2>&1 | wc -l) lines"
```

**6. Check Resource Usage (CPU/Memory Analysis):**
```bash
# Detailed resource analysis
./scripts/check_resource_usage.sh

# Quick resource check
docker stats --no-stream lotto-predictore_backend_1
```

**Understanding CPU Usage:**
- **Backend container has 2 CPUs allocated** (from docker-compose.yml)
- **106% CPU = Using ~1.06 out of 2 CPUs** (53% of allocation)
- **This is NORMAL and GOOD** - process is working efficiently
- **> 200% CPU** = Using more than 2 CPUs (might need more resources)
- **0% CPU** = Process stuck or idle

---

## Cron Job Scheduling API

The cron service (port 8002) provides endpoints to dynamically schedule cron jobs.

### Base URL
- **Cron Service**: `http://localhost:8002` (or `http://cron:8002` from within Docker network)

---

## Schedule API Endpoints

### 1. List Available Jobs

Get a list of all available cron jobs that can be scheduled.

```bash
curl http://localhost:8002/api/schedule/jobs
```

**Response:**
```json
{
  "status": "success",
  "available_jobs": {
    "generate-weekly-combinations-optimized": {
      "endpoint": "/cron/generate-weekly-combinations-optimized",
      "description": "Generate weekly combinations using grid search optimization"
    },
    "generate-weekly-combinations": {
      "endpoint": "/cron/generate-weekly-combinations",
      "description": "Generate weekly combinations (standard)"
    },
    "generate-weekly-combinations-fast": {
      "endpoint": "/cron/generate-weekly-combinations-fast",
      "description": "Generate weekly combinations (fast mode for debugging)"
    },
    "fetch-draws": {
      "endpoint": "/cron/fetch-draws",
      "description": "Fetch latest lottery draws"
    },
    "generate-model-tables": {
      "endpoint": "/cron/generate-model-tables",
      "description": "Generate model performance tables"
    },
    "send-weekly-email": {
      "endpoint": "/cron/send-weekly-combinations-email",
      "description": "Send weekly combinations email"
    }
  },
  "total_jobs": 6
}
```

---

### 2. Schedule a Job

Schedule a cron job to run at a specific time.

**Endpoint:** `POST /api/schedule`

**Request Body Options:**

**Option A: Schedule X minutes from now**
```json
{
  "job_name": "generate-weekly-combinations-optimized",
  "minutes_from_now": 5,
  "job_metadata": {
    "reason": "Manual trigger for testing"
  }
}
```

**Option B: Schedule at specific time (ISO format)**
```json
{
  "job_name": "generate-weekly-combinations-optimized",
  "scheduled_time": "2025-12-29T14:30:00",
  "job_metadata": {
    "reason": "Scheduled maintenance"
  }
}
```

**Example: Schedule job in 2 minutes**
```bash
curl -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "generate-weekly-combinations-optimized",
    "minutes_from_now": 2
  }'
```

**Example: Schedule job at specific time**
```bash
curl -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "fetch-draws",
    "scheduled_time": "2025-12-29T15:00:00"
  }'
```

**Response:**
```json
{
  "status": "success",
  "job_id": "generate-weekly-combinations-optimized-a1b2c3d4",
  "job_name": "generate-weekly-combinations-optimized",
  "scheduled_time": "2025-12-29T14:32:00",
  "endpoint": "/cron/generate-weekly-combinations-optimized",
  "message": "Job 'generate-weekly-combinations-optimized' scheduled for 2025-12-29T14:32:00"
}
```

---

### 3. List Scheduled Jobs

Get a list of all currently scheduled jobs.

```bash
curl http://localhost:8002/api/schedule
```

**Response:**
```json
{
  "status": "success",
  "scheduled_jobs": [
    {
      "job_id": "generate-weekly-combinations-optimized-a1b2c3d4",
      "job_name": "generate-weekly-combinations-optimized",
      "endpoint": "/cron/generate-weekly-combinations-optimized",
      "scheduled_time": "2025-12-29T14:32:00",
      "status": "scheduled",
      "created_at": "2025-12-29T14:30:00",
      "metadata": {}
    }
  ],
  "total": 1
}
```

---

### 4. Get Scheduled Job Status

Get the status of a specific scheduled job by job_id.

```bash
curl http://localhost:8002/api/schedule/{job_id}
```

**Example:**
```bash
curl http://localhost:8002/api/schedule/generate-weekly-combinations-optimized-a1b2c3d4
```

**Response:**
```json
{
  "status": "success",
  "job": {
    "job_id": "generate-weekly-combinations-optimized-a1b2c3d4",
    "job_name": "generate-weekly-combinations-optimized",
    "endpoint": "/cron/generate-weekly-combinations-optimized",
    "scheduled_time": "2025-12-29T14:32:00",
    "status": "executed",
    "created_at": "2025-12-29T14:30:00",
    "executed_at": "2025-12-29T14:32:05",
    "metadata": {}
  }
}
```

**Job Status Values:**
- `scheduled` - Job is scheduled and waiting to run
- `executed` - Job has been executed successfully
- `failed` - Job execution failed

---

## Common Use Cases

### Schedule Weekly Combinations in 2 Minutes

**Quick Command:**
```bash
curl -X POST http://localhost:8002/api/schedule -H "Content-Type: application/json" -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}'
```

**With Pretty Output:**
```bash
curl -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "generate-weekly-combinations-optimized",
    "minutes_from_now": 2
  }' | python3 -m json.tool
```

**Save Job ID for Monitoring:**
```bash
JOB_ID=$(curl -s -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "Job ID: $JOB_ID"
```

### Schedule Job for Tomorrow at 3 AM

```bash
curl -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "fetch-draws",
    "scheduled_time": "2025-12-30T03:00:00"
  }'
```

### Check What Jobs Are Available

```bash
curl http://localhost:8002/api/schedule/jobs | python3 -m json.tool
```

### Check All Scheduled Jobs

```bash
curl http://localhost:8002/api/schedule | python3 -m json.tool
```

---

## Monitoring Commands

### Monitor Scheduled Job Status

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

### Monitor Backend Cron Job Status

**Check cron job execution status in database:**
```bash
curl -s http://localhost:8000/cron/status | python3 -m json.tool
```

**Watch cron status (updates every 10 seconds):**
```bash
watch -n 10 'curl -s http://localhost:8000/cron/status | python3 -m json.tool'
```

### Monitor Backend Logs

**Tail backend logs for weekly combinations:**
```bash
# Docker logs
docker logs -f lotto-predictore_backend_1 | grep -i "weekly\|grid_search\|optimized"

# Or from log files
tail -f /home/orshv/lotto-predictore/logs/backend_service/backend_service.log | grep -i "weekly\|grid_search\|optimized"
```

### Monitor Scheduler Status

**Check all scheduled jobs (system + manual):**
```bash
curl -s http://localhost:8002/api/scheduler-status | python3 -m json.tool
```

**Watch scheduler status:**
```bash
watch -n 30 'curl -s http://localhost:8002/api/scheduler-status | python3 -m json.tool'
```

### Complete Monitoring Workflow

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

---

## Notes

- Jobs are scheduled using the `schedule` library and run within the cron service
- Scheduled jobs are stored in memory (will be lost on service restart)
- The cron service must be running and healthy for scheduling to work
- Jobs execute by calling the backend API endpoints
- All times are in local server time (not timezone-aware)

---

## Error Handling

If a job name is invalid:
```json
{
  "detail": "Unknown job name: invalid-job. Available jobs: ['generate-weekly-combinations-optimized', ...]"
}
```

If scheduling parameters are missing:
```json
{
  "detail": "Either scheduled_time or minutes_from_now must be provided"
}
```

---

## Related Endpoints

- **Scheduler Status**: `GET /api/scheduler-status` - Check all scheduled jobs (including system jobs)
- **Health Check**: `GET /health` - Check cron service health

