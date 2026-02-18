# Stop Running Processes 🛑

Commands to stop running weekly cron jobs and other processes.

## Stop Weekly Cron Process

### Option 1: Kill Background Script Process (If using Option 2/3 from Quick Start)

**Find and kill the scheduling script:**
```bash
# Find the process
ps aux | grep -E "schedule_weekly|weekly_job" | grep -v grep

# Kill the process (replace PID with actual process ID)
kill <PID>

# Or kill all matching processes at once
pkill -f "schedule_weekly"
pkill -f "weekly_job"
```

**Kill the curl request if it's still running:**
```bash
# Find curl processes for weekly combinations
ps aux | grep "curl.*generate-weekly-combinations" | grep -v grep

# Kill all curl processes for weekly combinations
pkill -f "curl.*generate-weekly-combinations"
```

### Option 2: Stop Backend Container (Nuclear Option)

**Restart the backend container (will stop all running jobs):**
```bash
docker-compose restart backend
```

**Stop and start backend:**
```bash
docker-compose stop backend
docker-compose start backend
```

### Option 3: Kill Process Inside Container

**Find and kill processes inside the backend container:**
```bash
# Find Python processes in backend container
docker exec lotto-predictore_backend_1 ps aux | grep python | grep -v grep

# Kill specific process (replace PID)
docker exec lotto-predictore_backend_1 kill <PID>

# Or kill all Python processes (be careful!)
docker exec lotto-predictore_backend_1 pkill -f python
```

### Option 4: Cancel Job via API (If using job queue)

**If the job was started via the job queue system:**
```bash
# First, get the job ID from the response when you started it
# Then cancel it:
curl -X DELETE http://localhost:8000/api/jobs/{job_id}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/jobs/weekly-combinations-abc123
```

## Quick Stop Commands

**One-liner to stop all weekly-related processes:**
```bash
pkill -f "schedule_weekly" && pkill -f "weekly_job" && pkill -f "curl.*generate-weekly-combinations" && echo "✅ All weekly processes stopped"
```

**Check if processes are still running:**
```bash
ps aux | grep -E "schedule_weekly|weekly_job|generate-weekly-combinations" | grep -v grep
```

## Stop Scheduled Jobs (Cron Service)

**Cancel a scheduled job via cron service API:**
```bash
# First, list scheduled jobs to get job_id
curl http://localhost:8002/api/schedule | python3 -m json.tool

# Note: The cron service API doesn't have a cancel endpoint yet
# You'll need to restart the cron service to clear scheduled jobs:
docker-compose restart cron_service
```

**⚠️ Warning:** Restarting the cron service will clear all scheduled jobs from memory.

## Emergency Stop (All Processes)

**Stop everything related to weekly combinations:**
```bash
# Stop all background scripts
pkill -f "schedule_weekly"
pkill -f "weekly_job"
pkill -f "curl.*generate-weekly-combinations"

# Restart backend (stops all running jobs)
docker-compose restart backend

# Restart cron service (clears scheduled jobs)
docker-compose restart cron_service
```

## Verify Process is Stopped

**Check if process is still running:**
```bash
# Check host processes
ps aux | grep -E "schedule_weekly|weekly_job|generate-weekly-combinations" | grep -v grep

# Check container processes
docker exec lotto-predictore_backend_1 ps aux | grep python | grep -v grep

# Check CPU usage (should be low if stopped)
docker stats --no-stream lotto-predictore_backend_1
```

