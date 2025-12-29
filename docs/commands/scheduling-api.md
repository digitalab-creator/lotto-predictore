# Cron Job Scheduling API

The cron service (port 8002) provides endpoints to dynamically schedule cron jobs.

## Base URL
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

