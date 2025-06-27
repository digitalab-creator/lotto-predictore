import os
import requests
from datetime import datetime
from fastapi import HTTPException
from shared.logging_service import get_cron_logger
from .job_handlers import cleanup_system, backup_database

logger = get_cron_logger()

def call_backend_endpoint(endpoint: str, last_successful_job: dict) -> None:
    """
    Call a backend API endpoint.
    
    Args:
        endpoint (str): The endpoint to call (e.g., '/cron/generate-weekly-combinations')
        last_successful_job (dict): Dictionary to track last successful job times
    """
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        url = f"{backend_url}{endpoint}"
        logger.info(f"Arrr! Attempting to call backend endpoint: {url}")
        
        # Test backend connection first
        try:
            health_check = requests.get(f"{backend_url}/health")
            health_check.raise_for_status()
            logger.info("Arrr! Backend health check successful!")
        except Exception as health_error:
            logger.error(
                "Arrr! Backend health check failed!",
                context={
                    "error": str(health_error),
                    "url": f"{backend_url}/health"
                }
            )
            raise
        
        # Call the actual endpoint
        logger.info(f"Arrr! Sending POST request to: {url}")
        response = requests.post(url)
        response.raise_for_status()
        
        # Update last successful job timestamp
        job_name = endpoint.split('/')[-1]
        if job_name in last_successful_job:
            last_successful_job[job_name] = datetime.now()
        
        logger.info(f"Arrr! Successfully called {endpoint}: {response.json()}")
    except requests.exceptions.ConnectionError as e:
        logger.error(
            "Arrr! Connection error calling endpoint!",
            context={
                "error": str(e),
                "endpoint": endpoint,
                "backend_url": backend_url
            }
        )
        raise
    except requests.exceptions.Timeout as e:
        logger.error(
            "Arrr! Timeout calling endpoint!",
            context={
                "error": str(e),
                "endpoint": endpoint,
                "backend_url": backend_url
            }
        )
        raise
    except Exception as e:
        logger.error(
            f"Arrr! Error calling endpoint {endpoint}!",
            context={
                "error": str(e),
                "endpoint": endpoint,
                "backend_url": backend_url
            }
        )
        # Notify via API
        try:
            requests.post(
                f"{backend_url}/api/notifications/error",
                json={
                    "error": str(e),
                    "endpoint": endpoint,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as notify_error:
            logger.error(
                "Arrr! Failed to send error notification!",
                context={
                    "error": str(notify_error),
                    "original_error": str(e)
                }
            )
        raise

def health_check_endpoint(last_successful_job: dict):
    """Health check endpoint that verifies cron service and backend connection"""
    try:
        # Check backend connection
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        backend_health = requests.get(f"{backend_url}/health")
        backend_health.raise_for_status()
        
        # Check if any jobs are scheduled
        import schedule
        if not schedule.jobs:
            raise HTTPException(
                status_code=503,
                detail="No jobs scheduled"
            )
        
        # Check last successful job times
        now = datetime.now()
        job_status = {}
        for job_name, last_success in last_successful_job.items():
            if last_success is None:
                job_status[job_name] = "never_run"
            else:
                # If job hasn't run in 24 hours, mark it as stale
                hours_since_last_run = (now - last_success).total_seconds() / 3600
                job_status[job_name] = "stale" if hours_since_last_run > 24 else "healthy"
        
        return {
            "status": "healthy",
            "services": {
                "cron": "up",
                "backend": "up",
                "jobs": job_status
            }
        }
    except requests.exceptions.RequestException as e:
        logger.error("Health check failed - backend connection error", context={'error': str(e)})
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "services": {
                    "cron": "up",
                    "backend": "down",
                    "error": str(e)
                }
            }
        )
    except Exception as e:
        logger.error("Health check failed", context={'error': str(e)})
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "services": {
                    "cron": "up",
                    "backend": "unknown",
                    "error": str(e)
                }
            }
        )

def check_model_files_endpoint():
    """
    Endpoint that calls the backend service to check model files.
    If any corrupted files are found, sends email notification.
    """
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        
        # Call backend endpoint to check model files
        response = requests.post(f"{backend_url}/api/check-model-files")
        response.raise_for_status()
        result = response.json()
        
        # If backend found any corrupted files, send email notification
        if result.get("corrupted_files"):
            try:
                notify_response = requests.post(
                    f"{backend_url}/api/notifications/model-corruption",
                    json=result
                )
                notify_response.raise_for_status()
                logger.info(
                    "Arrr! Sent corruption notification email!",
                    context={"corrupted_count": len(result["corrupted_files"])}
                )
            except Exception as notify_error:
                logger.error(
                    "Arrr! Failed to send corruption notification!",
                    context={
                        "error": str(notify_error),
                        "corrupted_files": result.get("corrupted_files", [])
                    }
                )
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(
            "Arrr! Error calling backend model check endpoint!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=503,
            detail=f"Backend service error: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Arrr! Error in model check endpoint!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check model files: {str(e)}"
        )

def cleanup_system_endpoint():
    """
    Endpoint to manually trigger comprehensive system cleanup.
    This includes log cleanup and Docker system pruning.
    """
    try:
        logger.info("Arrr! Manual system cleanup triggered via API!")
        cleanup_system()
        return {
            "status": "success",
            "message": "Arrr! System cleanup completed successfully!",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(
            "Arrr! Error during manual system cleanup!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"System cleanup failed: {str(e)}"
        )

def backup_database_endpoint():
    """
    Endpoint to manually trigger database backup.
    This creates a compressed database dump with timestamp.
    """
    try:
        logger.info("Arrr! Manual database backup triggered via API!")
        backup_database()
        return {
            "status": "success",
            "message": "Arrr! Database backup completed successfully!",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(
            "Arrr! Error during manual database backup!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Database backup failed: {str(e)}"
        ) 