# Quick Start: Schedule & Monitor Weekly Job

## Schedule Weekly Job for 2 Minutes

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

## Monitor Job Status

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

