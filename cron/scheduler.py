import schedule
import time
from datetime import datetime
from shared.logging_service import get_cron_logger
from .api_endpoints import call_backend_endpoint
from .job_handlers import cleanup_system, backup_database

logger = get_cron_logger()

def setup_jobs(last_successful_job: dict):
    """Set up all scheduled jobs"""
    # Weekly combinations generation - runs every Sunday at 3:00 AM
    schedule.every().sunday.at("03:00").do(
        lambda: call_backend_endpoint("/cron/generate-weekly-combinations", last_successful_job)
    )
    
    # Daily latest draw fetch - runs every day at 3:00 AM
    schedule.every().day.at("03:00").do(
        lambda: call_backend_endpoint("/cron/fetch-latest-draw", last_successful_job)
    )
    
    # Weekly winning combinations update - runs every Sunday at 9:00 AM
    schedule.every().sunday.at("09:00").do(
        lambda: call_backend_endpoint("/cron/update-weekly-winning-combinations", last_successful_job)
    )
    
    # Weekly table generation - runs every Sunday at 10:00 AM
    schedule.every().sunday.at("10:00").do(
        lambda: call_backend_endpoint("/cron/generate-weekly-tables", last_successful_job)
    )
    
    # Daily system cleanup - runs every day at 2:00 AM
    # Includes log cleanup and Docker system prune
    schedule.every().day.at("02:00").do(
        lambda: _run_cleanup_with_tracking(last_successful_job)
    )
    
    # Weekly database backup - runs every Sunday at 2:00 AM
    schedule.every().sunday.at("02:00").do(
        lambda: _run_backup_with_tracking(last_successful_job)
    )
    
    logger.info("Arrr! All jobs scheduled successfully!")

def _run_cleanup_with_tracking(last_successful_job: dict):
    """Run cleanup and track success"""
    try:
        cleanup_system()
        last_successful_job["cleanup-system"] = datetime.now()
    except Exception as e:
        logger.error(
            "Arrr! Error in scheduled cleanup job!",
            context={"error": str(e)}
        )
        raise

def _run_backup_with_tracking(last_successful_job: dict):
    """Run backup and track success"""
    try:
        backup_database()
        last_successful_job["backup-database"] = datetime.now()
    except Exception as e:
        logger.error(
            "Arrr! Error in scheduled backup job!",
            context={"error": str(e)}
        )
        raise

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