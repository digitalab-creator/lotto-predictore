"""
API endpoints for scheduling cron jobs dynamically.
Praisin' the FSM! 🍝⚓
"""
import schedule
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel
from shared.logging_service import get_cron_logger
from cron.api_endpoints import call_backend_endpoint

logger = get_cron_logger()

# Available cron job endpoints
AVAILABLE_JOBS = {
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
}

# Store scheduled jobs (job_id -> job_info)
_scheduled_jobs: Dict[str, Dict[str, Any]] = {}


class ScheduleRequest(BaseModel):
    """Request model for scheduling a cron job"""
    job_name: str
    scheduled_time: Optional[str] = None  # ISO format datetime string
    minutes_from_now: Optional[int] = None  # Alternative: schedule X minutes from now
    job_metadata: Optional[Dict[str, Any]] = None


class ScheduledJobResponse(BaseModel):
    """Response model for scheduled job"""
    status: str
    job_id: str
    job_name: str
    scheduled_time: str
    endpoint: str
    message: str


def list_available_jobs():
    """List all available cron jobs that can be scheduled"""
    return {
        "status": "success",
        "available_jobs": AVAILABLE_JOBS,
        "total_jobs": len(AVAILABLE_JOBS)
    }


def schedule_cron_job(request: ScheduleRequest, last_successful_job: dict):
    """
    Schedule a cron job to run at a specific time.
    
    You can either provide:
    - `scheduled_time`: ISO format datetime string (e.g., "2025-12-29T14:30:00")
    - `minutes_from_now`: Number of minutes from now (e.g., 5 for 5 minutes from now)
    
    Args:
        request: Schedule request with job name and timing
        last_successful_job: Dictionary to track last successful job times
    
    Returns:
        Scheduled job information
    """
    # Validate job name
    if request.job_name not in AVAILABLE_JOBS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown job name: {request.job_name}. Available jobs: {list(AVAILABLE_JOBS.keys())}"
        )
    
    job_info = AVAILABLE_JOBS[request.job_name]
    
    # Calculate scheduled time
    if request.scheduled_time:
        try:
            scheduled_time = datetime.fromisoformat(request.scheduled_time.replace('Z', '+00:00'))
            # Convert to naive datetime for schedule library
            if scheduled_time.tzinfo:
                scheduled_time = scheduled_time.replace(tzinfo=None)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scheduled_time format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
            )
    elif request.minutes_from_now is not None:
        if request.minutes_from_now < 0:
            raise HTTPException(
                status_code=400,
                detail="minutes_from_now must be >= 0"
            )
        scheduled_time = datetime.now() + timedelta(minutes=request.minutes_from_now)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either scheduled_time or minutes_from_now must be provided"
        )
    
    # Generate job ID
    job_id = f"{request.job_name}-{uuid.uuid4().hex[:8]}"
    
    # Create a one-time job using schedule library
    def run_scheduled_job():
        """Wrapper to run the scheduled job"""
        try:
            logger.info(
                "Arrr! Executing scheduled job!",
                context={
                    "job_id": job_id,
                    "job_name": request.job_name,
                    "endpoint": job_info["endpoint"]
                }
            )
            call_backend_endpoint(job_info["endpoint"], last_successful_job)
            _scheduled_jobs[job_id]["status"] = "executed"
            _scheduled_jobs[job_id]["executed_at"] = datetime.now().isoformat()
            logger.info(
                "Arrr! Scheduled job executed successfully!",
                context={"job_id": job_id, "job_name": request.job_name}
            )
        except Exception as e:
            _scheduled_jobs[job_id]["status"] = "failed"
            _scheduled_jobs[job_id]["error"] = str(e)
            logger.error(
                "Arrr! Scheduled job execution failed!",
                context={"job_id": job_id, "error": str(e)}
            )
            raise
    
    # Schedule the job
    schedule_time_str = scheduled_time.strftime("%H:%M")
    schedule_date = scheduled_time.date()
    
    # Check if scheduled time is today or in the future
    today = datetime.now().date()
    if schedule_date == today:
        # Schedule for today at the specified time
        schedule.every().day.at(schedule_time_str).do(run_scheduled_job).tag(job_id)
    else:
        # For future dates, we need to schedule it differently
        # Since schedule library doesn't support specific dates easily,
        # we'll schedule it to run once at the specified time
        # This is a limitation - for exact future dates, we'd need a more sophisticated scheduler
        logger.warning(
            "Arrr! Scheduling for future date - using daily schedule at specified time",
            context={
                "job_id": job_id,
                "scheduled_date": schedule_date.isoformat(),
                "scheduled_time": schedule_time_str
            }
        )
        schedule.every().day.at(schedule_time_str).do(run_scheduled_job).tag(job_id)
    
    # Store job info
    _scheduled_jobs[job_id] = {
        "job_id": job_id,
        "job_name": request.job_name,
        "endpoint": job_info["endpoint"],
        "scheduled_time": scheduled_time.isoformat(),
        "status": "scheduled",
        "created_at": datetime.now().isoformat(),
        "metadata": request.job_metadata or {}
    }
    
    logger.info(
        "Arrr! Cron job scheduled successfully!",
        context={
            "job_id": job_id,
            "job_name": request.job_name,
            "scheduled_time": scheduled_time.isoformat()
        }
    )
    
    return ScheduledJobResponse(
        status="success",
        job_id=job_id,
        job_name=request.job_name,
        scheduled_time=scheduled_time.isoformat(),
        endpoint=job_info["endpoint"],
        message=f"Job '{request.job_name}' scheduled for {scheduled_time.isoformat()}"
    )


def get_scheduled_job_status(job_id: str):
    """Get status of a scheduled job"""
    if job_id not in _scheduled_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return {
        "status": "success",
        "job": _scheduled_jobs[job_id]
    }


def list_scheduled_jobs():
    """List all scheduled jobs"""
    return {
        "status": "success",
        "scheduled_jobs": list(_scheduled_jobs.values()),
        "total": len(_scheduled_jobs)
    }

