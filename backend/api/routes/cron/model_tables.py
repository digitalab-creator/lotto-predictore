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

@router.post("/cron/generate-best-model-tables")
async def generate_best_model_tables():
    """Generate tables using the best performing model (ROI > 1) - called by cron service"""
    start_time = time.time()
    
    # Initialize cron tracking
    db = next(get_db())
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="generate-best-model-tables",
            job_type="scheduled",
            metadata={"start_time": start_time}
        )
        
        # Import and run the script
        from scripts.generate_best_model_tables import generate_best_model_tables
        result = generate_best_model_tables()
        
        total_time = time.time() - start_time
        
        # Mark job as completed
        if cron_job:
            tracker.complete_job(cron_job, total_time)
        
        logger.info(
            "Arrr! Best model tables generated successfully!",
            context={
                "total_time": f"{total_time:.2f}s",
                "job_id": cron_job.id if cron_job else None
            }
        )
        
        return {"status": "success", "message": "Best model tables generated successfully", "data": result}
        
    except Exception as e:
        error_msg = f"Error generating best model tables: {str(e)}"
        logger.error(
            "Arrr! Error generating best model tables!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close() 