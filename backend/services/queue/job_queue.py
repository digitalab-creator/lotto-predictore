"""Job queue management using RQ"""
import os
from typing import Dict, Any, Optional
from rq import Queue, Connection, Retry
from rq.job import Job
from services.queue.redis_client import get_redis_client
from logger import logger


def get_queue(name: str = 'default') -> Queue:
    """Get RQ queue instance"""
    redis_conn = get_redis_client()
    return Queue(name, connection=redis_conn)


def enqueue_job(
    func,
    *args,
    job_id: Optional[str] = None,
    job_timeout: int = 600,
    retry: Optional[Retry] = None,
    func_name: Optional[str] = None,
    **kwargs
) -> Job:
    """
    Enqueue a job to the RQ queue
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        job_id: Optional custom job ID
        job_timeout: Job timeout in seconds (default 10 minutes)
        retry: Optional retry configuration
        **kwargs: Keyword arguments for the function
    
    Returns:
        Job instance
    """
    queue = get_queue()
    
    if retry is None:
        retry = Retry(max=3, interval=[10, 30, 60])
    
    # Use string-based function reference if provided to avoid circular imports
    if func_name:
        # RQ can handle string function names, but we need to use enqueue_call properly
        import importlib
        module_path, func_path = func_name.rsplit('.', 1)
        module = importlib.import_module(module_path)
        actual_func = getattr(module, func_path)
        job = queue.enqueue(
            actual_func,
            *args,
            job_id=job_id,
            job_timeout=job_timeout,
            retry=retry,
            **kwargs
        )
    else:
        job = queue.enqueue(
            func,
            *args,
            job_id=job_id,
            job_timeout=job_timeout,
            retry=retry,
            **kwargs
        )
    
    logger.info(
        "Arrr! Job enqueued successfully!",
        context={
            "job_id": job.id,
            "job_timeout": job_timeout,
            "queue_name": queue.name
        }
    )
    
    return job


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get job status and result
    
    Args:
        job_id: Job ID
    
    Returns:
        Dictionary with job status, result, and metadata
    """
    try:
        job = Job.fetch(job_id, connection=get_redis_client())
        
        status_info = {
            "job_id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": None,
            "exc_info": None
        }
        
        if job.is_finished:
            status_info["result"] = job.result
        elif job.is_failed:
            status_info["exc_info"] = str(job.exc_info) if job.exc_info else None
        
        return status_info
        
    except Exception as e:
        logger.error(
            "Arrr! Failed to get job status!",
            context={"job_id": job_id, "error": str(e)}
        )
        return {
            "job_id": job_id,
            "status": "not_found",
            "error": str(e)
        }


def cancel_job(job_id: str) -> bool:
    """
    Cancel a job if it's still queued or started
    
    Args:
        job_id: Job ID
    
    Returns:
        True if job was cancelled, False otherwise
    """
    try:
        job = Job.fetch(job_id, connection=get_redis_client())
        if job.get_status() in ['queued', 'started']:
            job.cancel()
            logger.info("Arrr! Job cancelled!", context={"job_id": job_id})
            return True
        return False
    except Exception as e:
        logger.error(
            "Arrr! Failed to cancel job!",
            context={"job_id": job_id, "error": str(e)}
        )
        return False

