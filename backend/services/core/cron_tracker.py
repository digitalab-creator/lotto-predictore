import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import CronJob, JobStatus
from shared.logging_service import get_backend_logger

logger = get_backend_logger()

class CronTracker:
    """Service for tracking cron job executions in the database"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_job(self, job_name: str, job_type: str = 'scheduled', metadata: Optional[Dict[str, Any]] = None) -> CronJob:
        """
        Start tracking a new cron job
        
        Args:
            job_name: Name of the job
            job_type: Type of job ('scheduled' or 'manual')
            metadata: Additional job-specific data
            
        Returns:
            CronJob instance
        """
        try:
            cron_job = CronJob(
                job_name=job_name,
                status=JobStatus.RUNNING.value,
                job_type=job_type,
                job_metadata=metadata
            )
            self.db.add(cron_job)
            self.db.flush()  # Get the ID without committing
            
            logger.info(
                f"Arrr! Started tracking cron job: {job_name}",
                context={
                    "job_id": cron_job.id,
                    "job_name": job_name,
                    "job_type": job_type,
                    "started_at": cron_job.started_at.isoformat()
                }
            )
            
            return cron_job
            
        except Exception as e:
            logger.error(
                f"Arrr! Failed to start tracking job: {job_name}",
                context={
                    "error": str(e),
                    "job_name": job_name,
                    "job_type": job_type
                }
            )
            raise
    
    def complete_job(self, cron_job: CronJob, duration_seconds: Optional[float] = None) -> None:
        """
        Mark a job as completed
        
        Args:
            cron_job: The CronJob instance to update
            duration_seconds: Optional duration override
        """
        try:
            cron_job.mark_completed(duration_seconds)
            self.db.commit()
            
            logger.info(
                f"Arrr! Completed cron job: {cron_job.job_name}",
                context={
                    "job_id": cron_job.id,
                    "job_name": cron_job.job_name,
                    "duration_seconds": cron_job.duration_seconds,
                    "completed_at": cron_job.completed_at.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(
                f"Arrr! Failed to mark job as completed: {cron_job.job_name}",
                context={
                    "error": str(e),
                    "job_id": cron_job.id,
                    "job_name": cron_job.job_name
                }
            )
            self.db.rollback()
            raise
    
    def fail_job(self, cron_job: CronJob, error_message: str, duration_seconds: Optional[float] = None) -> None:
        """
        Mark a job as failed
        
        Args:
            cron_job: The CronJob instance to update
            error_message: Error message describing the failure
            duration_seconds: Optional duration override
        """
        try:
            cron_job.mark_failed(error_message, duration_seconds)
            self.db.commit()
            
            logger.error(
                f"Arrr! Cron job failed: {cron_job.job_name}",
                context={
                    "job_id": cron_job.id,
                    "job_name": cron_job.job_name,
                    "error_message": error_message,
                    "duration_seconds": cron_job.duration_seconds,
                    "completed_at": cron_job.completed_at.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(
                f"Arrr! Failed to mark job as failed: {cron_job.job_name}",
                context={
                    "error": str(e),
                    "job_id": cron_job.id,
                    "job_name": cron_job.job_name,
                    "original_error": error_message
                }
            )
            self.db.rollback()
            raise
    
    def get_last_successful_job(self, job_name: str) -> Optional[CronJob]:
        """
        Get the last successful execution of a specific job
        
        Args:
            job_name: Name of the job
            
        Returns:
            CronJob instance or None if no successful execution found
        """
        try:
            return self.db.query(CronJob).filter(
                CronJob.job_name == job_name,
                CronJob.status == JobStatus.COMPLETED.value
            ).order_by(CronJob.completed_at.desc()).first()
            
        except Exception as e:
            logger.error(
                f"Arrr! Failed to get last successful job: {job_name}",
                context={"error": str(e), "job_name": job_name}
            )
            return None
    
    def get_job_status_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a summary of all job statuses for health checks
        
        Returns:
            Dictionary with job status information
        """
        try:
            summary = {}
            now = datetime.datetime.utcnow()
            
            # Get all unique job names
            job_names = self.db.query(CronJob.job_name).distinct().all()
            
            for (job_name,) in job_names:
                # Get last successful job
                last_successful = self.get_last_successful_job(job_name)
                
                # Get currently running jobs
                running_jobs = self.db.query(CronJob).filter(
                    CronJob.job_name == job_name,
                    CronJob.status == JobStatus.RUNNING.value
                ).count()
                
                # Get recent failed jobs (last 24 hours)
                recent_failures = self.db.query(CronJob).filter(
                    CronJob.job_name == job_name,
                    CronJob.status == JobStatus.FAILED.value,
                    CronJob.completed_at >= now - datetime.timedelta(hours=24)
                ).count()
                
                if last_successful is None:
                    summary[job_name] = {
                        "status": "never_run",
                        "last_success": None,
                        "hours_since_last_run": None,
                        "running_jobs": running_jobs,
                        "recent_failures": recent_failures
                    }
                else:
                    hours_since_last_run = (now - last_successful.completed_at).total_seconds() / 3600
                    summary[job_name] = {
                        "status": "stale" if hours_since_last_run > 24 else "healthy",
                        "last_success": last_successful.completed_at.isoformat(),
                        "hours_since_last_run": hours_since_last_run,
                        "running_jobs": running_jobs,
                        "recent_failures": recent_failures
                    }
            
            return summary
            
        except Exception as e:
            logger.error(
                "Arrr! Failed to get job status summary",
                context={"error": str(e)}
            )
            return {}
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """
        Clean up old cron job records
        
        Args:
            days_to_keep: Number of days of records to keep
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_to_keep)
            
            # Delete old completed and failed jobs
            deleted_count = self.db.query(CronJob).filter(
                CronJob.completed_at < cutoff_date,
                CronJob.status.in_([JobStatus.COMPLETED.value, JobStatus.FAILED.value])  # Use enum values directly
            ).delete()
            
            self.db.commit()
            
            logger.info(
                f"Arrr! Cleaned up {deleted_count} old cron job records",
                context={
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "days_to_keep": days_to_keep
                }
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "Arrr! Failed to cleanup old cron job records",
                context={"error": str(e), "days_to_keep": days_to_keep}
            )
            self.db.rollback()
            return 0 