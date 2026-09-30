import os
import requests
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from shared.logging_service import get_cron_logger

logger = get_cron_logger()

_DEFAULT_ERROR_EMAIL_COOLDOWN_SECONDS = 3600


class CronErrorHandler:
    """Centralized error handling and notification for cron jobs"""
    
    def __init__(self):
        self.backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        self.email_url = os.getenv('EMAIL_SERVICE_URL', 'http://email-service:8000')
        self._error_email_cooldown = timedelta(
            seconds=int(
                os.getenv(
                    "CRON_ERROR_EMAIL_COOLDOWN_SECONDS",
                    str(_DEFAULT_ERROR_EMAIL_COOLDOWN_SECONDS),
                )
            )
        )
        self._last_error_email_at: Dict[str, datetime] = {}
    
    def handle_job_error(self, job_name: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle a cron job error by logging it and sending an email notification.
        
        Args:
            job_name: Name of the job that failed
            error: The exception that occurred
            context: Additional context about the job execution
        """
        try:
            # Log the error
            logger.error(
                f"Arrr! Cron job '{job_name}' failed!",
                context={
                    "job_name": job_name,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "traceback": traceback.format_exc(),
                    "context": context or {},
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Send email notification
            self._send_error_notification(job_name, error, context)
            
        except Exception as notification_error:
            # If sending notification fails, log it but don't raise
            logger.error(
                f"Arrr! Failed to send error notification for job '{job_name}'!",
                context={
                    "original_error": str(error),
                    "notification_error": str(notification_error)
                }
            )
    
    def _should_send_error_email(self, job_name: str) -> bool:
        last_sent = self._last_error_email_at.get(job_name)
        if last_sent is None:
            return True
        return datetime.now() - last_sent >= self._error_email_cooldown

    def _send_error_notification(self, job_name: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Send email notification about the failed job"""
        if not self._should_send_error_email(job_name):
            logger.info(
                f"Arrr! Skipping error email for job '{job_name}' (cooldown active)",
                context={
                    "job_name": job_name,
                    "cooldown_seconds": int(self._error_email_cooldown.total_seconds()),
                },
            )
            return
        try:
            # Prepare error notification data in the format expected by email service
            error_data = {
                "error_message": str(error),
                "service": "cron-service",
                "script": job_name,
                "traceback": traceback.format_exc()
            }
            
            # Send to email service
            response = requests.post(
                f"{self.email_url}/send-error-notification",
                json=error_data,
                timeout=30
            )
            response.raise_for_status()
            self._last_error_email_at[job_name] = datetime.now()

            logger.info(
                f"Arrr! Error notification sent for job '{job_name}'",
                context={"job_name": job_name}
            )
            
        except Exception as e:
            logger.error(
                f"Arrr! Failed to send error notification!",
                context={
                    "job_name": job_name,
                    "notification_error": str(e)
                }
            )
            raise
    
    def _format_error_email(self, job_name: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """Format the error email body"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        email_body = f"""
🏴‍☠️ **Cron Job Failure Alert** 🏴‍☠️

**Job:** {job_name}
**Time:** {timestamp}
**Error Type:** {type(error).__name__}
**Error Message:** {str(error)}

**Full Traceback:**
```
{traceback.format_exc()}
```

**Context:**
{self._format_context(context) if context else "No additional context provided"}

**What to do:**
1. Check the logs for more details
2. Verify the job configuration
3. Check external dependencies (APIs, databases, etc.)
4. Restart the service if needed

**System Status:**
- Cron Service: Running
- Backend Service: {self._check_backend_status()}
- Email Service: {self._check_email_status()}

---
*This is an automated alert from the Lotto Predictor Cron Service*
*May the Flying Spaghetti Monster guide you to fix this issue! 🍝*
        """
        
        return email_body.strip()
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the email"""
        if not context:
            return "No context provided"
        
        formatted = []
        for key, value in context.items():
            if isinstance(value, dict):
                formatted.append(f"**{key}:** {self._format_context(value)}")
            else:
                formatted.append(f"**{key}:** {value}")
        
        return "\n".join(formatted)
    
    def _check_backend_status(self) -> str:
        """Check if backend service is responding"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            return "✅ Healthy" if response.status_code == 200 else "❌ Unhealthy"
        except Exception as e:
            logger.debug("Backend health check failed: %s", e)
            return "❌ Unreachable"

    def _check_email_status(self) -> str:
        """Check if email service is responding"""
        try:
            response = requests.get(f"{self.email_url}/health", timeout=5)
            return "✅ Healthy" if response.status_code == 200 else "❌ Unhealthy"
        except Exception as e:
            logger.debug("Email service health check failed: %s", e)
            return "❌ Unreachable"

# Global error handler instance
error_handler = CronErrorHandler()

def handle_cron_error(job_name: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Convenience function to handle cron job errors.
    
    Args:
        job_name: Name of the job that failed
        error: The exception that occurred
        context: Additional context about the job execution
    """
    error_handler.handle_job_error(job_name, error, context) 