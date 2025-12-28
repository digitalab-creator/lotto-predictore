"""Job status endpoints for queue system"""
from fastapi import APIRouter, HTTPException
from services.queue.job_queue import get_job_status, cancel_job
from logger import logger

router = APIRouter()


@router.get("/api/jobs/{job_id}/status")
async def get_job_status_endpoint(job_id: str):
    """
    Get the status of a background job
    
    Args:
        job_id: Job ID returned when job was enqueued
    
    Returns:
        Job status information including result if completed
    """
    try:
        status_info = get_job_status(job_id)
        
        if status_info.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        logger.info(
            "Arrr! Job status retrieved!",
            context={"job_id": job_id, "status": status_info.get("status")}
        )
        
        return {
            "success": True,
            "data": status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Arrr! Error getting job status!",
            context={"job_id": job_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/jobs/{job_id}")
async def cancel_job_endpoint(job_id: str):
    """
    Cancel a queued or running job
    
    Args:
        job_id: Job ID to cancel
    
    Returns:
        Success status
    """
    try:
        cancelled = cancel_job(job_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} cannot be cancelled (may already be finished or failed)"
            )
        
        logger.info("Arrr! Job cancelled!", context={"job_id": job_id})
        
        return {
            "success": True,
            "data": {"job_id": job_id, "cancelled": True}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Arrr! Error cancelling job!",
            context={"job_id": job_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

