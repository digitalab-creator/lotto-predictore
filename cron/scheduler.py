import schedule
import time
from datetime import datetime
from shared.logging_service import get_cron_logger
from cron.api_endpoints import call_backend_endpoint
from cron.job_handlers import cleanup_system, backup_database
from cron.error_handler import handle_cron_error

logger = get_cron_logger()

POST_DRAW_CHAIN_PATH = "/cron/post-draw-chain"
# Morning after a draw night (Tue/Thu/Sat ~23:14). 23:30 is too early for the official file.
RETRY_DAYS = ("wednesday", "friday", "sunday")
RETRY_PATH = "/cron/post-draw-chain?allow_magayo=true"
RECONCILE_PATH = "/cron/reconcile-draws"


def _schedule_post_draw_chain(last_successful_job: dict, job_name: str = "post-draw-chain") -> None:
    """Ingest draws; settle, scoreboard step, ticket pack, email/WhatsApp when new draw inserted."""
    _run_job_with_error_handling(
        job_name,
        lambda: call_backend_endpoint(POST_DRAW_CHAIN_PATH, last_successful_job),
        last_successful_job,
    )


def setup_jobs(last_successful_job: dict):
    """Set up all scheduled jobs"""
    # Official CSV, then settle and email only when a new draw was stored. No Magayo here.
    schedule.every().day.at("01:00").do(
        lambda: _schedule_post_draw_chain(last_successful_job, job_name="post-draw-chain-daily")
    )

    # If the 01:00 file still lacks last night's draw, try once more, then Magayo.
    for day in RETRY_DAYS:
        getattr(schedule.every(), day).at("04:00").do(
            lambda: _run_job_with_error_handling(
                "post-draw-chain-retry",
                lambda: call_backend_endpoint(RETRY_PATH, last_successful_job),
                last_successful_job,
            )
        )

    schedule.every().sunday.at("05:00").do(
        lambda: _run_job_with_error_handling(
            "reconcile-draws",
            lambda: call_backend_endpoint(RECONCILE_PATH, last_successful_job),
            last_successful_job,
        )
    )
    
    # Daily log cleanup - runs every day at 2:00 AM
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
    
    logger.info(
        "Arrr! Post-draw chain scheduled: daily 01:00, retry "
        f"{', '.join(RETRY_DAYS)} 04:00, reconcile Sunday 05:00 (Asia/Jerusalem)"
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
        # Do not re-raise: schedule marks last_run only when the job returns.
        # Re-raising left the daily job "due" and it retried every minute → email spam.

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