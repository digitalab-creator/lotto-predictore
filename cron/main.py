import os
import sys
from pathlib import Path
from fastapi import FastAPI
import uvicorn
from threading import Thread
from shared.logging_service import get_cron_logger
from cron.api_endpoints import (
    call_backend_endpoint,
    health_check_endpoint,
    check_model_files_endpoint,
    cleanup_system_endpoint,
    backup_database_endpoint,
    best_model_job_endpoint,
    fetch_latest_draw_endpoint,
    test_error_handling_endpoint
)
from cron.schedule_api import (
    list_available_jobs,
    schedule_cron_job,
    get_scheduled_job_status,
    list_scheduled_jobs,
    ScheduleRequest
)
from cron.scheduler import setup_jobs, run_scheduler

# Add shared directory to Python path
shared_dir = Path('/app/shared')
sys.path.append(str(shared_dir))

# Initialize FastAPI app
app = FastAPI(title="Cron Service")

# Get logger instance
logger = get_cron_logger()

# Global state for health check
last_successful_job = {
    "generate-weekly-combinations": None,
    "fetch-latest-draw": None,
    "best-model-tables-and-email": None,
    "cleanup-system": None,
    "backup-database": None
}

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint that verifies cron service and backend connection"""
    try:
        return health_check_endpoint(last_successful_job)
    except Exception as e:
        # Fallback - return minimal health status
        return {
            "status": "degraded",
            "services": {
                "cron": "up",
                "error": str(e)
            }
        }

@app.post("/api/check-model-files")
async def check_model_files():
    """
    Endpoint that calls the backend service to check model files.
    If any corrupted files are found, sends email notification.
    """
    return check_model_files_endpoint()

@app.post("/api/cleanup-system")
async def cleanup_system():
    """
    Endpoint to manually trigger comprehensive system cleanup.
    This includes log cleanup and Docker system pruning.
    """
    return cleanup_system_endpoint()

@app.post("/api/backup-database")
async def backup_database():
    """
    Endpoint to manually trigger database backup.
    This creates a compressed database dump with timestamp.
    """
    return backup_database_endpoint()

@app.post("/api/best-model-job")
async def best_model_job():
    """
    Endpoint to manually trigger best model table generation and email sending.
    This is the same logic used by the scheduled job.
    """
    return best_model_job_endpoint()

@app.post("/api/fetch-latest-draw")
async def fetch_latest_draw():
    """
    Endpoint to manually trigger fetch latest draw.
    This is the same logic used by the scheduled job.
    """
    return fetch_latest_draw_endpoint()

@app.post("/api/test-error-handling")
async def test_error_handling():
    """
    Test endpoint that deliberately fails to test error handling and email notifications.
    """
    return test_error_handling_endpoint()

@app.get("/api/scheduler-status")
async def scheduler_status():
    """
    Diagnostic endpoint to check scheduler status and next run times for all jobs.
    """
    import schedule
    from datetime import datetime
    import pytz
    
    UTC = pytz.UTC
    current_time_utc = datetime.now(UTC)
    
    jobs_info = []
    for job in schedule.jobs:
        next_run = job.next_run
        if next_run:
            # Handle timezone-aware datetime
            if next_run.tzinfo is None:
                next_run_utc = UTC.localize(next_run)
            else:
                next_run_utc = next_run.astimezone(UTC)
            
            time_until_run = next_run_utc - current_time_utc
            jobs_info.append({
                "job_tag": str(job.tags) if hasattr(job, 'tags') else "N/A",
                "next_run_utc": next_run_utc.isoformat(),
                "time_until_run_seconds": int(time_until_run.total_seconds()),
                "time_until_run_human": str(time_until_run),
                "is_pending": time_until_run.total_seconds() > 0
            })
        else:
            jobs_info.append({
                "job_tag": str(job.tags) if hasattr(job, 'tags') else "N/A",
                "next_run_utc": None,
                "status": "No next run scheduled"
            })
    
    return {
        "status": "active",
        "current_time_utc": current_time_utc.isoformat(),
        "total_jobs": len(schedule.jobs),
        "jobs": jobs_info,
        "scheduler_running": True
    }

@app.get("/api/schedule/jobs")
async def list_available_jobs_endpoint():
    """List all available cron jobs that can be scheduled"""
    return list_available_jobs()

@app.post("/api/schedule")
async def schedule_job_endpoint(request: ScheduleRequest):
    """
    Schedule a cron job to run at a specific time.
    
    You can either provide:
    - `scheduled_time`: ISO format datetime string (e.g., "2025-12-29T14:30:00")
    - `minutes_from_now`: Number of minutes from now (e.g., 5 for 5 minutes from now)
    """
    return schedule_cron_job(request, last_successful_job)

@app.get("/api/schedule")
async def list_scheduled_jobs_endpoint():
    """List all scheduled jobs"""
    return list_scheduled_jobs()

@app.get("/api/schedule/{job_id}")
async def get_scheduled_job_status_endpoint(job_id: str):
    """Get status of a scheduled job"""
    return get_scheduled_job_status(job_id)

if __name__ == "__main__":
    logger.info("Arrr! Starting cron service...")
    setup_jobs(last_successful_job)
    
    # Start scheduler in a separate thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8002) 