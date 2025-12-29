import logging
import os
from datetime import datetime, timedelta
import pytz
from pathlib import Path
from typing import Any, Dict, Optional, List
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import shutil
import inspect
import threading
import sys

# Import config constants
sys.path.append('/app')
try:
    from config import LOG_ROTATION_MAX_BYTES, LOG_ROTATION_BACKUP_COUNT, LOG_RETENTION_DAYS
except ImportError:
    # Fallback values if config is not available
    LOG_ROTATION_MAX_BYTES = int(9.5 * 1024 * 1024)  # 9.5MB
    LOG_ROTATION_BACKUP_COUNT = 100
    LOG_RETENTION_DAYS = 14

class CallerAwareFormatter(logging.Formatter):
    """Custom formatter that handles missing caller fields gracefully."""
    
    def format(self, record):
        # Ensure caller fields exist with defaults
        if not hasattr(record, 'caller_file'):
            record.caller_file = 'unknown'
        if not hasattr(record, 'caller_func'):
            record.caller_func = 'unknown'
        if not hasattr(record, 'caller_lineno'):
            record.caller_lineno = 0
            
        return super().format(record)

class LoggingService:
    @staticmethod
    def cleanup_old_logs(base_log_dir: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Clean up log files older than 14 days for all services.
        This method should be called by the cron service.
        
        Args:
            base_log_dir (Optional[str]): Base directory for logs. If None, uses LOG_DIR env var.
            
        Returns:
            Dict[str, List[str]]: Dictionary containing lists of removed files per service
        """
        if base_log_dir is None:
            base_log_dir = os.getenv('LOG_DIR', '/app/logs')
            
        logs_dir = Path(base_log_dir)
        if not logs_dir.exists():
            return {}
            
        # Calculate the cutoff date (based on retention days)
        cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # Track removed files per service
        removed_files = {}
        
        try:
            # Get all service directories
            service_dirs = [d for d in logs_dir.iterdir() if d.is_dir()]
            
            for service_dir in service_dirs:
                service_name = service_dir.name
                removed_files[service_name] = []
                
                # Get all log files in the service directory
                log_files = list(service_dir.glob(f"{service_name}.*"))
                
                # Remove files older than retention period
                for log_file in log_files:
                    if log_file.stat().st_mtime < cutoff_timestamp:
                        log_file.unlink()
                        removed_files[service_name].append(str(log_file))
                        
                # If no files were removed for this service, remove it from the dict
                if not removed_files[service_name]:
                    del removed_files[service_name]
            
            # Also clean up root-level log files (like backup.log)
            root_log_files = list(logs_dir.glob("*.log*"))
            if root_log_files:
                if 'root' not in removed_files:
                    removed_files['root'] = []
                for log_file in root_log_files:
                    if log_file.stat().st_mtime < cutoff_timestamp:
                        log_file.unlink()
                        removed_files['root'].append(str(log_file))
                if not removed_files['root']:
                    del removed_files['root']
                    
            return removed_files
            
        except Exception as e:
            # Log the error using a basic logger since our logging service might be affected
            basic_logger = logging.getLogger('log_cleanup')
            basic_logger.error(f"Error during log cleanup: {str(e)}")
            raise

    def __init__(self, service_name: str):
        """
        Initialize the logging service.
        
        Args:
            service_name (str): Name of the service using this logger
        """
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        
        # Check if logger is already configured to prevent duplicate handlers
        if self.logger.handlers:
            # Logger already configured, just return
            return
        
        # Get log directory from environment or use default
        base_log_dir = os.getenv('LOG_DIR', '/app/logs')
        self.logs_dir = Path(base_log_dir) / service_name
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level))
        
        # Get Israel timezone
        israel_tz = pytz.timezone('Asia/Jerusalem')
        
        # Console handler with Israel timezone
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        console_format = CallerAwareFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(caller_file)s:%(caller_func)s:%(caller_lineno)d] -\n%(message)s\n\n',
            datefmt='%Y-%m-%d %H:%M:%S %Z'
        )
        console_format.converter = lambda *args: datetime.now(israel_tz).timetuple()
        console_handler.setFormatter(console_format)
        
        # File handler with rotation based on size
        log_file = self.logs_dir / f'{service_name}.log'
        
        # Size-based rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_ROTATION_MAX_BYTES,
            backupCount=LOG_ROTATION_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_format = CallerAwareFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(caller_file)s:%(caller_func)s:%(caller_lineno)d] -\n%(message)s\n\n',
            datefmt='%Y-%m-%d %H:%M:%S %Z'
        )
        file_format.converter = lambda *args: datetime.now(israel_tz).timetuple()
        file_handler.setFormatter(file_format)
        
        # Add handlers (only console and file, remove time-based to prevent duplicates)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        # Log that the service is initialized
        self.logger.info(
            f"Logging service initialized - log rotation: {LOG_ROTATION_MAX_BYTES / (1024 * 1024):.1f}MB max, "
            f"backup count: {LOG_ROTATION_BACKUP_COUNT}, "
            f"cleanup scheduled via cron service at 02:00 AM daily ({LOG_RETENTION_DAYS} days retention)"
        )
    
    def log(
        self,
        message: str,
        level: str = "INFO",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a message with optional context.
        
        Args:
            message (str): Message to log
            level (str): Log level (INFO, WARNING, ERROR, DEBUG)
            context (Optional[Dict[str, Any]]): Additional context to log
        """
        log_method = getattr(self.logger, level.lower())
        
        stack = inspect.stack()
        caller_func = caller_file = caller_lineno = None
        
        # Skip logging service internal methods to find the actual caller
        logging_service_methods = {'log', 'info', 'warning', 'error', 'debug'}
        for frame in stack:
            if (frame.function not in logging_service_methods and 
                'logging_service.py' not in frame.filename):
                caller_func = frame.function
                caller_file = frame.filename.split('/')[-1]
                caller_lineno = frame.lineno
                break
        extra = {
            'caller_func': caller_func or '',
            'caller_file': caller_file or '',
            'caller_lineno': caller_lineno or 0
        }
        if context:
            context['timestamp'] = datetime.now().isoformat()
            context_lines = []
            for key, value in context.items():
                if isinstance(value, (list, dict)) and len(str(value)) > 50:
                    context_lines.append(f"  {key}:")
                    if isinstance(value, list):
                        for i, item in enumerate(value):
                            context_lines.append(f"    [{i}]: {item}")
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            context_lines.append(f"    {k}: {v}")
                else:
                    context_lines.append(f"  {key}: {value}")
            context_str = "\n".join(context_lines)
            log_method(f"{message}\nContext:\n{context_str}", extra=extra)
        else:
            log_method(f"{message}", extra=extra)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message"""
        self.log(message, "INFO", context)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message"""
        self.log(message, "WARNING", context)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error message"""
        self.log(message, "ERROR", context)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message"""
        self.log(message, "DEBUG", context)

# Create a singleton instance for each service
_cron_logger = None
_backend_logger = None
_logger_lock = threading.Lock()

def get_cron_logger() -> LoggingService:
    """Get the cron service logger instance"""
    global _cron_logger
    if _cron_logger is None:
        with _logger_lock:
            if _cron_logger is None:
                _cron_logger = LoggingService('cron_service')
    return _cron_logger

def get_backend_logger() -> LoggingService:
    """Get the backend service logger instance"""
    global _backend_logger
    if _backend_logger is None:
        with _logger_lock:
            if _backend_logger is None:
                _backend_logger = LoggingService('backend_service')
    return _backend_logger 