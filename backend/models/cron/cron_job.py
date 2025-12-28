from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, Enum
from sqlalchemy.sql import func
import datetime
from db.base import Base
import enum

class JobStatus(enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class CronJob(Base):
    __tablename__ = "cron_jobs"
    
    id = Column(Integer, primary_key=True)
    job_name = Column(String(100), nullable=False, index=True)
    status = Column(Enum(JobStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    job_type = Column(String(50), nullable=False, server_default='scheduled')  # scheduled, manual
    job_metadata = Column(JSON, nullable=True)  # Additional job-specific data (renamed from metadata)
    
    def __repr__(self):
        return f"<CronJob(id={self.id}, job_name='{self.job_name}', status='{self.status.value}', started_at='{self.started_at}')>"
    
    @property
    def is_running(self):
        return self.status == JobStatus.RUNNING.value
    
    @property
    def is_completed(self):
        return self.status == JobStatus.COMPLETED.value
    
    @property
    def is_failed(self):
        return self.status == JobStatus.FAILED.value
    
    def mark_completed(self, duration_seconds=None):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED.value
        self.completed_at = datetime.datetime.utcnow()
        if duration_seconds is not None:
            self.duration_seconds = duration_seconds
        elif self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def mark_failed(self, error_message=None, duration_seconds=None):
        """Mark job as failed"""
        self.status = JobStatus.FAILED.value
        self.completed_at = datetime.datetime.utcnow()
        if error_message:
            self.error_message = error_message
        if duration_seconds is not None:
            self.duration_seconds = duration_seconds
        elif self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds() 