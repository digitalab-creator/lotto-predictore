# Queue System Implementation Summary

## Overview
Implemented a Redis-based queue system using RQ to handle ML jobs asynchronously, preventing API blocking and improving resource utilization.

## Components Added

### 1. Redis Service
- Added Redis container to `docker-compose.yml`
- Resource limits: 0.5 CPU, 256MB RAM
- Health check configured

### 2. Worker Service
- New `worker/` directory with Dockerfile
- RQ worker processes background jobs
- Resource limits: 2 CPU, 1GB RAM
- Imports `services.queue.workers` to register tasks

### 3. Queue Modules
- `backend/services/queue/redis_client.py` - Redis connection manager
- `backend/services/queue/job_queue.py` - Job enqueueing and status checking
- `backend/services/queue/workers.py` - Background task definitions

### 4. API Endpoints
- `POST /cron/generate-weekly-combinations` - Now enqueues jobs by default (use `?sync=true` for fallback)
- `GET /api/jobs/{job_id}/status` - Check job status and results
- `DELETE /api/jobs/{job_id}` - Cancel a queued/running job

### 5. Docker Resource Limits
All services now have CPU and memory limits:
- **Backend**: 2 CPU, 1.5GB RAM
- **Worker**: 2 CPU, 1GB RAM
- **Redis**: 0.5 CPU, 256MB RAM
- **Database**: 1 CPU, 512MB RAM
- **Cron**: 1 CPU, 512MB RAM
- **Email Service**: 0.5 CPU, 256MB RAM

### 6. Optimizations
- **Parallel Algorithm Evaluation**: `SimulationEngine.run_comparison` now processes up to 4 algorithm pairs concurrently
- **Async Job Processing**: ML jobs no longer block the API
- **Job Status Polling**: Cron service polls job status until completion

## Usage

### Enqueue a Job (Default)
```bash
curl -X POST http://localhost:8000/cron/generate-weekly-combinations
# Returns: {"success": true, "data": {"status": "queued", "job_id": "...", ...}}
```

### Check Job Status
```bash
curl http://localhost:8000/api/jobs/{job_id}/status
```

### Run Synchronously (Fallback)
```bash
curl -X POST "http://localhost:8000/cron/generate-weekly-combinations?sync=true"
```

## VM Capacity Assessment

**Current VM**: 4 CPUs, 3.8GB RAM

**Resource Allocation**:
- Backend: 2 CPU, 1.5GB
- Worker: 2 CPU, 1GB
- Redis: 0.5 CPU, 256MB
- Database: 1 CPU, 512MB
- Cron: 1 CPU, 512MB
- Email: 0.5 CPU, 256MB
- **Total Reserved**: ~7 CPU (overcommitted), ~4GB RAM

**Recommendations**:
1. **Monitor** resource usage after deployment
2. If CPU consistently >90%, consider upgrading to **6-8 CPUs**
3. If memory pressure occurs, consider upgrading to **8GB RAM**
4. Consider using **cloud auto-scaling** for worker instances during peak loads

## Performance Expectations

- **Before**: 5-10+ minutes blocking API, 103% CPU usage
- **After**: 
  - API responds immediately (<1s)
  - Job completes in 2-4 minutes (parallel execution)
  - No API blocking
  - Better resource utilization with limits

## Testing

1. Start services: `docker-compose up -d`
2. Check worker logs: `docker logs lotto-predictore_worker_1`
3. Enqueue a test job: `curl -X POST http://localhost:8000/cron/generate-weekly-combinations`
4. Monitor job status via the status endpoint
5. Check resource usage: `docker stats`


