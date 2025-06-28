import schedule
import time
from datetime import datetime
from shared.logging_service import get_cron_logger
from cron.api_endpoints import call_backend_endpoint
from cron.job_handlers import cleanup_system, backup_database
from cron.error_handler import handle_cron_error

logger = get_cron_logger()

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
    
    # Weekly winning combinations update - runs every Sunday at 9:00 AM
    schedule.every().sunday.at("09:00").do(
        lambda: _run_job_with_error_handling("update-weekly-winning-combinations",
            lambda: call_backend_endpoint("/cron/update-weekly-winning-combinations", last_successful_job),
            last_successful_job)
    )
    
    # Weekly table generation - runs every Sunday at 10:00 AM
    schedule.every().sunday.at("10:00").do(
        lambda: _run_job_with_error_handling("generate-weekly-tables",
            lambda: call_backend_endpoint("/cron/generate-weekly-tables", last_successful_job),
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
        
        # Update last successful job timestamp
        last_successful_job[job_name] = datetime.now()
        
        logger.info(f"Arrr! Job '{job_name}' completed successfully!")
        
    except Exception as e:
        # Handle the error with logging and email notification
        handle_cron_error(job_name, e, {
            "last_successful_job": last_successful_job.get(job_name),
            "scheduled_time": datetime.now().isoformat(),
            "job_type": "scheduled"
        })
        
        # Re-raise the exception so the scheduler knows the job failed
        raise

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