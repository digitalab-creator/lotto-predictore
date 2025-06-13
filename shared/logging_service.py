import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

class LoggingService:
    def __init__(self, service_name: str):
        """
        Initialize the logging service.
        
        Args:
            service_name (str): Name of the service using this logger
        """
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        
        # Get log directory from environment or use default
        log_dir = os.getenv('LOG_DIR', '/app/logs')
        logs_dir = Path(log_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        
        # File handler - always log to file
        file_handler = logging.FileHandler(
            logs_dir / f'{service_name}.log'
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        
        # Add both handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

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
        
        if context:
            # Add timestamp to context
            context['timestamp'] = datetime.now().isoformat()
            log_method(f"{message} | Context: {context}")
        else:
            log_method(message)

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

def get_cron_logger() -> LoggingService:
    """Get the cron service logger instance"""
    global _cron_logger
    if _cron_logger is None:
        _cron_logger = LoggingService('cron_service')
    return _cron_logger

def get_backend_logger() -> LoggingService:
    """Get the backend service logger instance"""
    global _backend_logger
    if _backend_logger is None:
        _backend_logger = LoggingService('backend_service')
    return _backend_logger 