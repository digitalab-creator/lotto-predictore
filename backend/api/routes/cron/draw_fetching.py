from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.base import SessionLocal
from services.cron_tracker import CronTracker
from logger import logger
import time

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/cron/fetch-latest-draw")
async def fetch_latest_draw():
    """Fetch latest draw - called by cron service"""
    start_time = time.time()
    
    # Initialize cron tracking
    db = next(get_db())
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="fetch-latest-draw",
            job_type="scheduled",
            metadata={"start_time": start_time}
        )
        
        # Import and run the script
        from services.fetch_latest_draw import main as fetch_draw
        fetch_draw()
        
        total_time = time.time() - start_time
        
        # Mark job as completed
        if cron_job:
            tracker.complete_job(cron_job, total_time)
        
        logger.info(
            "Arrr! Latest draw fetched successfully!",
            context={
                "total_time": f"{total_time:.2f}s",
                "job_id": cron_job.id if cron_job else None
            }
        )
        
        return {"status": "success", "message": "Latest draw fetched successfully"}
        
    except Exception as e:
        error_msg = f"Error fetching latest draw: {str(e)}"
        logger.error(
            "Arrr! Error fetching latest draw!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close() 