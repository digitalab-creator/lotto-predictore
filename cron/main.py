import os
import sys
import schedule
import time
import requests
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
import uvicorn
from threading import Thread
from shared.logging_service import get_cron_logger, LoggingService

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
    "generate-weekly-tables": None,
    "update-weekly-winning-combinations": None,
    "cleanup-old-logs": None
}

def call_backend_endpoint(endpoint: str) -> None:
    """
    Call a backend API endpoint.
    
    Args:
        endpoint (str): The endpoint to call (e.g., '/cron/generate-weekly-combinations')
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

@app.get("/health")
async def health_check():
    """Health check endpoint that verifies cron service and backend connection"""
    try:
        # Check backend connection
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        backend_health = requests.get(f"{backend_url}/health")
        backend_health.raise_for_status()
        
        # Check if any jobs are scheduled
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

def cleanup_old_logs() -> None:
    """
    Clean up old log files using the shared LoggingService.
    This is called directly by the cron service since it's a shared service function.
    """
    try:
        removed_files = LoggingService.cleanup_old_logs()
        # Update last successful job timestamp
        last_successful_job["cleanup-old-logs"] = datetime.now()
        
        # Log the results
        if removed_files:
            logger.info(
                "Arrr! Successfully cleaned up old logs!",
                context={"removed_files": removed_files}
            )
        else:
            logger.info("Arrr! No old logs to clean up!")
            
    except Exception as e:
        logger.error(
            "Arrr! Error during log cleanup!",
            context={"error": str(e)}
        )
        raise

@app.post("/api/check-model-files")
async def check_model_files_endpoint():
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

def setup_jobs():
    """Set up all scheduled jobs"""
    # Weekly combinations generation - runs every Sunday at 3:00 AM
    schedule.every().sunday.at("03:00").do(
        lambda: call_backend_endpoint("/cron/generate-weekly-combinations")
    )
    
    # Daily latest draw fetch - runs every day at 3:00 AM
    schedule.every().day.at("03:00").do(
        lambda: call_backend_endpoint("/cron/fetch-latest-draw")
    )
    
    # Weekly winning combinations update - runs every Sunday at 9:00 AM
    schedule.every().sunday.at("09:00").do(
        lambda: call_backend_endpoint("/cron/update-weekly-winning-combinations")
    )
    
    # Weekly table generation - runs every Sunday at 10:00 AM
    schedule.every().sunday.at("10:00").do(
        lambda: call_backend_endpoint("/cron/generate-weekly-tables")
    )
    
    # Log cleanup - runs every day at 2:00 AM
    schedule.every().day.at("02:00").do(
        lambda: cleanup_old_logs()
    )
    
    logger.info("Arrr! All jobs scheduled successfully!")

def run_scheduler():
    """Run the scheduler in a separate thread"""
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(
                "Arrr! Error in scheduler loop!",
                context={"error": str(e)}
            )
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    logger.info("Arrr! Starting cron service...")
    setup_jobs()
    
    # Start scheduler in a separate thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8002) 