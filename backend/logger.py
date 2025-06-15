"""
Backend logger module.
This module exports a single logger instance for the entire backend service.
"""

from shared.logging_service import get_backend_logger

# Use the singleton logger instance for the backend service
logger = get_backend_logger() 