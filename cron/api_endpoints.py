import os
import requests
from datetime import datetime
from fastapi import HTTPException
from shared.logging_service import get_cron_logger
from cron.job_handlers import cleanup_system, backup_database
from cron.error_handler import handle_cron_error

logger = get_cron_logger()

def call_backend_endpoint(endpoint: str, last_successful_job: dict) -> None:
    """
    Call a backend API endpoint with retry logic for connection errors.
    
    Args:
        endpoint (str): The endpoint to call (e.g., '/cron/generate-weekly-combinations')
        last_successful_job (dict): Dictionary to track last successful job times (deprecated - now using database)
    """
    import time as time_module
    
    backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
    url = f"{backend_url}{endpoint}"
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Arrr! Attempting to call backend endpoint: {url} (attempt {attempt}/{max_retries})")
            
            # Test backend connection first
            try:
                health_check = requests.get(f"{backend_url}/health", timeout=10)
                health_check.raise_for_status()
                logger.info("Arrr! Backend health check successful!")
            except Exception as health_error:
                if attempt < max_retries:
                    logger.warning(
                        f"Arrr! Backend health check failed (attempt {attempt}/{max_retries}), retrying...",
                        context={
                            "error": str(health_error),
                            "url": f"{backend_url}/health",
                            "retry_in_seconds": retry_delay
                        }
                    )
                    time_module.sleep(retry_delay)
                    continue
                else:
                    logger.error(
                        "Arrr! Backend health check failed after all retries!",
                        context={
                            "error": str(health_error),
                            "url": f"{backend_url}/health",
                            "total_attempts": max_retries
                        }
                    )
                    raise
            
            # Call the actual endpoint
            logger.info(f"Arrr! Sending POST request to: {url}")
            response = requests.post(url, timeout=30)  # Short timeout for job enqueueing
            response.raise_for_status()
            response_data = response.json()
            
            # Check if job was enqueued (async mode)
            if response_data.get("success") and response_data.get("data", {}).get("status") == "queued":
                job_id = response_data["data"]["job_id"]
                logger.info(
                    f"Arrr! Job enqueued, polling for completion: {job_id}",
                    context={"job_id": job_id, "endpoint": endpoint}
                )
                
                # Poll job status until completion
                max_poll_time = 600  # 10 minutes max
                poll_interval = 10  # Check every 10 seconds
                start_poll_time = time_module.time()
                
                while time_module.time() - start_poll_time < max_poll_time:
                    status_response = requests.get(f"{backend_url}/api/jobs/{job_id}/status", timeout=10)
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    job_status = status_data.get("data", {}).get("status")
                    
                    if job_status == "finished":
                        logger.info(
                            f"Arrr! Job completed successfully!",
                            context={
                                "job_id": job_id,
                                "result": status_data.get("data", {}).get("result")
                            }
                        )
                        return  # Success - exit retry loop
                    elif job_status == "failed":
                        error_info = status_data.get("data", {}).get("exc_info", "Unknown error")
                        logger.error(
                            f"Arrr! Job failed!",
                            context={"job_id": job_id, "error": error_info}
                        )
                        raise Exception(f"Job {job_id} failed: {error_info}")
                    
                    # Job still running, wait and poll again
                    logger.debug(
                        f"Arrr! Job still running, status: {job_status}",
                        context={"job_id": job_id, "status": job_status}
                    )
                    time_module.sleep(poll_interval)
                
                # Timeout waiting for job
                raise Exception(f"Job {job_id} did not complete within {max_poll_time} seconds")
            
            # Synchronous response (fallback mode)
            logger.info(f"Arrr! Successfully called {endpoint}: {response_data}")
            return  # Success - exit retry loop
            
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries:
                logger.warning(
                    f"Arrr! Connection error calling endpoint (attempt {attempt}/{max_retries}), retrying...",
                    context={
                        "error": str(e),
                        "endpoint": endpoint,
                        "backend_url": backend_url,
                        "retry_in_seconds": retry_delay
                    }
                )
                time_module.sleep(retry_delay)
                continue
            else:
                logger.error(
                    "Arrr! Connection error calling endpoint after all retries!",
                    context={
                        "error": str(e),
                        "endpoint": endpoint,
                        "backend_url": backend_url,
                        "total_attempts": max_retries
                    }
                )
                raise
        except requests.exceptions.Timeout as e:
            if attempt < max_retries:
                logger.warning(
                    f"Arrr! Timeout calling endpoint (attempt {attempt}/{max_retries}), retrying...",
                    context={
                        "error": str(e),
                        "endpoint": endpoint,
                        "backend_url": backend_url,
                        "retry_in_seconds": retry_delay
                    }
                )
                time_module.sleep(retry_delay)
                continue
            else:
                logger.error(
                    "Arrr! Timeout calling endpoint after all retries!",
                    context={
                        "error": str(e),
                        "endpoint": endpoint,
                        "backend_url": backend_url,
                        "total_attempts": max_retries
                    }
                )
                raise
        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"Arrr! Error calling endpoint (attempt {attempt}/{max_retries}), retrying...",
                    context={
                        "error": str(e),
                        "endpoint": endpoint,
                        "backend_url": backend_url,
                        "retry_in_seconds": retry_delay
                    }
                )
                time_module.sleep(retry_delay)
                continue
            else:
                logger.error(
                    f"Arrr! Error calling endpoint {endpoint} after all retries!",
                    context={
                        "error": str(e),
                        "endpoint": endpoint,
                        "backend_url": backend_url,
                        "total_attempts": max_retries
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
        
        # Get cron job status from database
        cron_status = requests.get(f"{backend_url}/cron/status")
        cron_status.raise_for_status()
        cron_data = cron_status.json()
        
        # Check if any jobs are scheduled
        import schedule
        if not schedule.jobs:
            raise HTTPException(
                status_code=503,
                detail="No jobs scheduled"
            )
        
        return {
            "status": "healthy",
            "services": {
                "cron": "up",
                "backend": "up",
                "database_tracking": "up",
                "jobs": cron_data.get("jobs", {})
            },
            "timestamp": cron_data.get("timestamp")
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
        # Use the error handler for consistent error handling
        handle_cron_error("cleanup-system-manual", e, {
            "trigger_type": "manual",
            "endpoint": "/api/cleanup-system"
        })
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
        backup_database()
        return {"status": "success", "message": "Database backup completed successfully"}
    except Exception as e:
        # Use the error handler for consistent error handling
        handle_cron_error("backup-database-manual", e, {
            "trigger_type": "manual",
            "endpoint": "/api/backup-database"
        })
        raise HTTPException(status_code=500, detail=str(e))

def best_model_job_endpoint():
    """
    Endpoint to manually trigger best model table generation and email sending.
    This is the same logic used by the scheduled job.
    """
    try:
        import requests
        import os
        import json
        
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        email_url = os.getenv('EMAIL_SERVICE_URL', 'http://email-service:8000')
        
        # First generate the best model tables
        logger.info("Arrr! Generating best model tables...")
        generate_response = requests.post(f"{backend_url}/cron/generate-best-model-tables")
        generate_response.raise_for_status()
        generate_data = generate_response.json()
        
        if not generate_data.get("data", {}).get("success", False):
            raise Exception(f"Failed to generate best model tables: {generate_data.get('message', 'Unknown error')}")
        
        # Extract the data from the generate response
        tables_data = generate_data["data"]
        
        # Prepare email data
        email_data = {
            "date": tables_data["date"],
            "tables": tables_data["tables"],
            "model_info": tables_data["model_info"]
        }
        
        # Send email directly to email service
        logger.info("Arrr! Sending best model email...")
        email_response = requests.post(
            f"{email_url}/send-best-model-tables",
            json=email_data,
            timeout=30
        )
        email_response.raise_for_status()
        
        return {
            "status": "success", 
            "message": "Best model tables generated and email sent successfully",
            "data": {
                "date": tables_data["date"],
                "num_tables": len(tables_data["tables"]),
                "main_model": tables_data["model_info"]["main_model"],
                "strong_model": tables_data["model_info"]["strong_model"],
                "roi_ratio": tables_data["model_info"]["roi_ratio"]
            }
        }
        
    except Exception as e:
        # Use the error handler for consistent error handling
        handle_cron_error("best-model-job-manual", e, {
            "trigger_type": "manual",
            "endpoint": "/api/best-model-job"
        })
        raise HTTPException(status_code=500, detail=str(e))

def fetch_latest_draw_endpoint():
    """
    Endpoint to manually trigger fetch latest draw.
    This is the same logic used by the scheduled job.
    """
    try:
        import requests
        import os
        
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        
        logger.info("Arrr! Fetching latest draw...")
        response = requests.post(f"{backend_url}/cron/fetch-latest-draw")
        response.raise_for_status()
        result = response.json()
        
        return {
            "status": "success",
            "message": "Latest draw fetched successfully",
            "data": result
        }
        
    except Exception as e:
        # Use the error handler for consistent error handling
        handle_cron_error("fetch-latest-draw-manual", e, {
            "trigger_type": "manual",
            "endpoint": "/api/fetch-latest-draw"
        })
        raise HTTPException(status_code=500, detail=str(e))

def test_error_handling_endpoint():
    """
    Test endpoint that deliberately fails to test error handling and email notifications.
    """
    try:
        # Deliberately raise an exception to test error handling
        raise Exception("This is a test error to verify the error handling system works correctly!")
        
    except Exception as e:
        # Use the error handler for consistent error handling
        handle_cron_error("test-error-handling", e, {
            "trigger_type": "manual",
            "endpoint": "/api/test-error-handling",
            "purpose": "Testing error notification system"
        })
        raise HTTPException(status_code=500, detail=str(e)) 