import schedule
import time
from datetime import datetime, timedelta
from shared.logging_service import get_cron_logger
from cron.api_endpoints import call_backend_endpoint
from cron.job_handlers import cleanup_system, backup_database
from cron.error_handler import handle_cron_error

logger = get_cron_logger()

# Track failed jobs to prevent spam
failed_jobs = {}

def setup_jobs(last_successful_job: dict):
    """Set up all scheduled jobs"""
    # Weekly combinations generation - runs every Sunday at 3:00 AM
    schedule.every().sunday.at("03:00").do(
        lambda: _run_job_with_error_handling("generate-weekly-combinations", 
            lambda: call_backend_endpoint("/cron/generate-weekly-combinations", last_successful_job),
            last_successful_job)
    )
    
    # Daily latest draw fetch - runs every day at 3:00 AM
    schedule.every().day.at("03:00").do(
        lambda: _run_job_with_error_handling("fetch-latest-draw",
            lambda: call_backend_endpoint("/cron/fetch-latest-draw", last_successful_job),
            last_successful_job)
    )
    
    # Best model table generation and email - runs every Sunday at 14:00 UTC (16:00 Israel time)
    schedule.every().sunday.at("14:00").do(
        lambda: _run_job_with_error_handling("best-model-tables-and-email",
            lambda: _run_best_model_job(last_successful_job),
            last_successful_job)
    )
    
    # Daily system cleanup - runs every day at 2:00 AM
    # Includes log cleanup and Docker system prune
    schedule.every().day.at("02:00").do(
        lambda: _run_job_with_error_handling("cleanup-system",
            lambda: _run_cleanup_with_tracking(last_successful_job),
            last_successful_job)
    )
    
    # Weekly database backup - runs every Sunday at 2:00 AM
    schedule.every().sunday.at("02:00").do(
        lambda: _run_job_with_error_handling("backup-database",
            lambda: _run_backup_with_tracking(last_successful_job),
            last_successful_job)
    )
    
    logger.info("Arrr! All jobs scheduled successfully!")

def _run_job_with_error_handling(job_name: str, job_function, last_successful_job: dict):
    """Run a job with comprehensive error handling and notification"""
    try:
        logger.info(f"Arrr! Starting scheduled job: {job_name}")
        
        # Run the job
        job_function()
        
        # Job succeeded - clear any failure tracking
        if job_name in failed_jobs:
            del failed_jobs[job_name]
            logger.info(f"Arrr! Job '{job_name}' recovered from previous failure!")
        
        logger.info(f"Arrr! Job '{job_name}' completed successfully!")
        
    except Exception as e:
        # Check if we should send notification (cooldown period)
        should_notify = _should_send_notification(job_name)
        
        if should_notify:
            # Handle the error with logging and email notification
            handle_cron_error(job_name, e, {
                "last_successful_job": last_successful_job.get(job_name),
                "scheduled_time": datetime.now().isoformat(),
                "job_type": "scheduled",
                "failure_count": failed_jobs.get(job_name, {}).get('count', 0) + 1
            })
            
            # Update failure tracking
            failed_jobs[job_name] = {
                'last_failure': datetime.now(),
                'count': failed_jobs.get(job_name, {}).get('count', 0) + 1,
                'error': str(e)
            }
        else:
            # Just log the error without sending notification
            logger.warning(
                f"Arrr! Job '{job_name}' failed again (suppressing notification due to cooldown)",
                context={
                    "job_name": job_name,
                    "error": str(e),
                    "failure_count": failed_jobs.get(job_name, {}).get('count', 0),
                    "cooldown_until": failed_jobs.get(job_name, {}).get('last_failure', datetime.now()) + timedelta(hours=1)
                }
            )
        
        # Re-raise the exception so the scheduler knows the job failed
        raise

def _should_send_notification(job_name: str) -> bool:
    """Check if we should send a notification for a failed job (cooldown mechanism)"""
    if job_name not in failed_jobs:
        return True
    
    failure_info = failed_jobs[job_name]
    last_failure = failure_info['last_failure']
    failure_count = failure_info['count']
    
    # Cooldown periods based on failure count
    if failure_count == 1:
        # First failure - send notification immediately
        return True
    elif failure_count <= 3:
        # 2-3 failures - wait 1 hour between notifications
        cooldown_period = timedelta(hours=1)
    elif failure_count <= 5:
        # 4-5 failures - wait 6 hours between notifications
        cooldown_period = timedelta(hours=6)
    else:
        # 6+ failures - wait 24 hours between notifications
        cooldown_period = timedelta(hours=24)
    
    time_since_last_failure = datetime.now() - last_failure
    return time_since_last_failure >= cooldown_period

def _cleanup_old_failures():
    """Clean up old failure tracking data to prevent memory leaks"""
    try:
        current_time = datetime.now()
        jobs_to_remove = []
        
        for job_name, failure_info in failed_jobs.items():
            last_failure = failure_info['last_failure']
            # Remove failures older than 7 days
            if current_time - last_failure > timedelta(days=7):
                jobs_to_remove.append(job_name)
        
        for job_name in jobs_to_remove:
            del failed_jobs[job_name]
            logger.info(f"Arrr! Cleaned up old failure tracking for job: {job_name}")
            
    except Exception as e:
        logger.warning(
            "Arrr! Error during failure tracking cleanup!",
            context={"error": str(e)}
        )

def _run_best_model_job(last_successful_job: dict):
    """Run best model table generation and email sending"""
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
    
    logger.info("Arrr! Best model tables generated and email sent successfully!")

def _run_cleanup_with_tracking(last_successful_job: dict):
    """Run cleanup and track success"""
    cleanup_system()

def _run_backup_with_tracking(last_successful_job: dict):
    """Run backup and track success"""
    backup_database()

def run_scheduler():
    """Run the scheduler in a separate thread"""
    consecutive_errors = 0
    max_consecutive_errors = 5
    last_cleanup = datetime.now()
    cleanup_interval = timedelta(hours=6)  # Clean up every 6 hours
    
    while True:
        try:
            schedule.run_pending()
            consecutive_errors = 0  # Reset error counter on successful iteration
            
            # Periodically clean up old failure tracking
            current_time = datetime.now()
            if current_time - last_cleanup > cleanup_interval:
                _cleanup_old_failures()
                last_cleanup = current_time
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            consecutive_errors += 1
            
            if consecutive_errors <= max_consecutive_errors:
                logger.error(
                    "Arrr! Error in scheduler loop!",
                    context={
                        "error": str(e),
                        "consecutive_errors": consecutive_errors,
                        "max_consecutive_errors": max_consecutive_errors
                    }
                )
                time.sleep(60)  # Wait before retrying
            else:
                logger.critical(
                    "Arrr! Too many consecutive errors in scheduler loop! Stopping scheduler to prevent spam!",
                    context={
                        "error": str(e),
                        "consecutive_errors": consecutive_errors,
                        "max_consecutive_errors": max_consecutive_errors
                    }
                )
                
                # Send a critical notification about scheduler failure
                try:
                    handle_cron_error("scheduler-loop", e, {
                        "consecutive_errors": consecutive_errors,
                        "action": "scheduler_stopped_to_prevent_spam"
                    })
                except:
                    pass  # Don't let notification failure cause more issues
                
                # Stop the scheduler to prevent infinite error loops
                break 