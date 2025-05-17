import os
import logging
import json
import traceback
import inspect
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import sys
import shutil
import codecs
import pkg_resources

# Load environment variables
load_dotenv()

# Constants
PIRATE_LOG_PREFIX = "Ye Olde Logger Says: "
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

# Notification settings from environment
NOTIFICATION_METHOD = os.getenv('NOTIFICATION_METHOD', 'none').lower()  # 'email', 'service', or 'none'
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ELASTIC_EMAIL_API_KEY = os.getenv('ELASTIC_EMAIL_API_KEY')
NOTIFICATIONS_SERVICE_URL = os.getenv('NOTIFICATIONS_SERVICE_URL')
DISABLE_LOGGING = os.getenv('DISABLE_LOGGING', 'false').lower() == 'true'

# Get log directory from environment or use default (always absolute)
def get_log_dir() -> str:
    log_dir = os.getenv('BACKEND_LOG_DIR', '/app/logs')
    if not os.path.isabs(log_dir):
        # Warn and normalize to absolute path from project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        abs_log_dir = os.path.abspath(os.path.join(project_root, log_dir))
        print(f"[FSM WARNING] Log dir '{log_dir}' is not absolute. Normalizing to '{abs_log_dir}'!")
        return abs_log_dir
    return log_dir

DEFAULT_LOG_DIR = get_log_dir()

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_log_directory(log_dir: Path, log_file: Path) -> None:
    """Create log directory and log file with proper permissions."""
    print("Attempting to create log directory and file:", log_dir)
    try:
        # Create directory with full permissions
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(log_dir, 0o775)
            print(f"Created log directory at: {log_dir}")
            print(f"Directory permissions: {oct(os.stat(log_dir).st_mode)[-3:]}")
        else:
            os.chmod(log_dir, 0o775)
            print(f"Log directory exists at: {log_dir}")
            print(f"Directory permissions: {oct(os.stat(log_dir).st_mode)[-3:]}")
        # Create log file if it doesn't exist
        if not log_file.exists():
            log_file.touch()
            os.chmod(log_file, 0o664)
            print(f"Created log file at: {log_file}")
            print(f"File permissions: {oct(os.stat(log_file).st_mode)[-3:]}")
        else:
            os.chmod(log_file, 0o664)
            print(f"Log file exists at: {log_file}")
            print(f"File permissions: {oct(os.stat(log_file).st_mode)[-3:]}")
        print("Log directory and file setup complete")
    except Exception as e:
        print(f"Error creating log directory/file: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory exists: {log_dir.exists()}")
        print(f"File exists: {log_file.exists() if log_dir.exists() else 'N/A'}")
        print(f"Full error traceback:\n{traceback.format_exc()}")
        raise

def get_caller_info() -> Dict[str, str]:
    """Get information about the calling function."""
    try:
        # Get the current stack
        stack = inspect.stack()
        # Skip the first two frames (this function and dh_log)
        caller_frame = stack[2]
        return {
            'file': caller_frame.filename,
            'function': caller_frame.function,
            'line': caller_frame.lineno
        }
    except Exception:
        return {}

class HebrewSafeFormatter(logging.Formatter):
    """Custom formatter that properly handles Hebrew text and context"""
    
    def __init__(self):
        super().__init__()
        self._seen_messages = set()  # Instance-level set for tracking seen messages
        self.default_format = '%(asctime)s [%(levelname)s] %(message)s'
        self.error_format = '%(asctime)s [%(levelname)s] %(message)s\n%(exc_info)s'
        # Define system paths to exclude from traceback
        self.system_paths = {
            # Python system paths
            '/usr/local/lib/python',  # Python installation directory
            '/usr/lib/python',        # System Python directory
            '/usr/lib64/python',      # System Python directory (64-bit)
            '/usr/lib32/python',      # System Python directory (32-bit)
            '<frozen importlib',      # Python internals
            '<string>',               # Python internals
            '<module>',               # Python internals
            
            # Docker-specific paths
            '/usr/local/lib/python3.11/',  # Docker Python installation
            '/usr/lib/python3.11/',        # Docker Python system
            '/usr/lib64/python3.11/',      # Docker Python system (64-bit)
            '/usr/lib32/python3.11/',      # Docker Python system (32-bit)
            '/usr/local/bin/',             # Docker binaries
            '/usr/bin/',                   # Docker system binaries
            '/usr/sbin/',                  # Docker system binaries
            '/bin/',                       # Docker core binaries
            '/sbin/',                      # Docker core binaries
            
            # Python package paths in Docker
            '/usr/local/lib/python3.11/site-packages/',  # Docker pip packages
            '/usr/lib/python3.11/site-packages/',        # Docker system packages
            
            # Docker container paths
            '/etc/',                      # Docker configuration
            '/var/',                      # Docker variable data
            '/proc/',                     # Docker process info
            '/sys/',                      # Docker system info
            '/dev/',                      # Docker devices
            '/run/',                      # Docker runtime data
            
            # Common Docker application paths
            '/usr/local/bin/python',      # Python executable
            '/usr/local/bin/pip',         # Pip executable
            '/usr/local/bin/uvicorn',     # Uvicorn executable
            '/usr/local/bin/gunicorn',    # Gunicorn executable
        }
        self.max_context_depth = 6  # Maximum depth for nested context objects
        self.max_string_length = 10000  # Increased from 1000 to 10000 characters
        self.max_list_items = 20  # Maximum number of items to show in lists

    def _format_value(self, value: Any, indent: int = 0, depth: int = 0) -> str:
        """Format a value for logging, handling truncation and special types"""
        if isinstance(value, str) and len(value) > self.max_string_length:
            return f"{value[:self.max_string_length]}... [truncated {len(value)-self.max_string_length} chars, full length: {len(value)}]"
        if value is None:
            return "None"
                
        if depth > self.max_context_depth:
            return "... [max depth reached]"
                
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        # Special case for query vectors - truncate them in logs
        if isinstance(value, (list, tuple)) and len(value) > 0 and all(isinstance(x, (int, float)) for x in value):
            return f"[vector of length {len(value)}]"
        if isinstance(value, (list, tuple)):
            if not value:
                return "[]"
            items = [self._format_value(v, indent + 2, depth + 1) for v in value[:self.max_list_items]]
            if len(items) > 1:
                formatted_items = (",\n" + " " * (indent + 2)).join(items)
                if len(value) > self.max_list_items:
                    formatted_items += f"\n{' ' * (indent + 2)}... [and {len(value) - self.max_list_items} more items]"
                return f"[\n{' ' * (indent + 2)}{formatted_items}\n{' ' * indent}]"
            return "[" + ", ".join(items) + "]"
        if isinstance(value, dict):
            if not value:
                return "{}"
                
            # Format dictionary consistently
            result = "{\n"
            keys = list(value.keys())
            for i, k in enumerate(keys):
                if k.strip() and k not in ('timestamp'):  # Skip timestamp in context
                    v = value[k]
                    v_str = self._format_value(v, indent + 2, depth + 1)
                    
                    # Add key with proper indentation
                    result += " " * (indent + 2) + f"{k}: "
                    
                    # Handle nested structures (lists, dicts)
                    if isinstance(v, (dict, list)) and v:
                        result += "\n" + " " * (indent + 4) + v_str.replace("\n", "\n" + " " * 2)
                    else:
                        result += v_str
                        
                    # Add comma if not the last item
                    if i < len(keys) - 1:
                        result += ","
                        
                    result += "\n"
            
            # Add closing brace with proper indentation
            result += " " * indent + "}"
            return result
                
        if isinstance(value, set):
            if not value:
                return "{}"
            items = [self._format_value(v, indent + 2, depth + 1) for v in value]
            if len(items) > 1:
                formatted_items = (",\n" + " " * (indent + 2)).join(items)
                return f"{{\n{' ' * (indent + 2)}{formatted_items}\n{' ' * indent}}}"
            return "{" + ", ".join(items) + "}"
        if hasattr(value, '__dict__'):
            try:
                return f"{type(value).__name__}({self._format_value(value.__dict__, indent + 2, depth + 1)})"
            except:
                return f"{type(value).__name__}[object]"
        return str(value)

    def format_context(self, context: dict) -> str:
            """Format context with proper Hebrew text handling"""
            if not context:
                return ""
                
            formatted_lines = []
            for key, value in sorted(context.items()):  # Sort keys for consistent output
                try:
                    formatted_value = self._format_value(value)
                    if isinstance(formatted_value, (dict, list)):
                        formatted_value = json.dumps(formatted_value, ensure_ascii=False, indent=2)
                    formatted_lines.append(f"\t{key}: {formatted_value}")
                except Exception as e:
                    formatted_lines.append(f"\t{key}: [Error formatting value: {str(e)}]")
                    
            return "\n" + "\n".join(formatted_lines)
        
    def format(self, record):
        try:
            # Generate a unique key for the message to detect duplicates
            msg_key = f"{record.created}:{record.levelname}:{record.msg}"
            
            # Skip if we've seen this exact message recently
            if msg_key in self._seen_messages:
                return None
                
            # Add to seen messages and maintain a reasonable size
            self._seen_messages.add(msg_key)
            if len(self._seen_messages) > 1000:  # Keep last 1000 messages
                self._seen_messages.pop()
            
            # Format the message
            if hasattr(record, 'context'):
                base_message = record.msg
                context_str = self.format_context(record.context)
                record.msg = f"{base_message}{context_str}"
                
            if record.exc_info:
                fmt = self.error_format + "\n"  # Add extra newline after error messages
            else:
                fmt = self.default_format + "\n"  # Add extra newline after regular messages
                
            formatter = logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')
            formatted_msg = formatter.format(record)
            
            # Ensure proper encoding for Hebrew text
            return formatted_msg.encode('utf-8').decode('utf-8')
            
        except Exception as e:
            return f"[Logging Error: {str(e)}]"

class HebrewSafeFileHandler(logging.FileHandler):
    """Custom file handler that properly handles Hebrew text"""
    
    def __init__(self, filename, mode='a', encoding='utf-8'):
        super().__init__(filename, mode, encoding)
        self.setFormatter(HebrewSafeFormatter())

logger = None  # Arrr, global logger for the FSM!

def setup_logger(service_name: str = "backend", log_dir: str = DEFAULT_LOG_DIR) -> logging.Logger:
    global logger  # Arrr, make sure we set the global logger!
    try:
        if DISABLE_LOGGING:
            noop_logger = logging.getLogger('noop_logger')
            noop_logger.addHandler(logging.NullHandler())
            noop_logger.setLevel(logging.CRITICAL)
            logger = noop_logger
            return noop_logger
        print("Setting up logger...")
        log_dir_path = Path(log_dir)
        log_file_path = log_dir_path / f"{service_name}.log"
        create_log_directory(log_dir_path, log_file_path)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        logger = logging.getLogger(f'dh_logger_{service_name}')
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        file_handler = HebrewSafeFileHandler(str(log_file_path), mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()))
        console_handler.setFormatter(HebrewSafeFormatter())
        logger.addHandler(console_handler)
        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(logging.DEBUG)
        openai_logger.addHandler(file_handler)
        langchain_logger = logging.getLogger("langchain")
        langchain_logger.setLevel(logging.DEBUG)
        langchain_logger.addHandler(file_handler)
        logger.propagate = False
        print(f"Logger initialization complete for service: {service_name}")
        print(f"Logger handlers: {logger.handlers}")
        logger.info("Arrr! Test log entry for the FSM, file logging should work! (setup_logger)")
        return logger
    except Exception as e:
        print(f"Error setting up logger: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        basic_logger = logging.getLogger(f'dh_logger_fallback_{service_name}')
        basic_logger.setLevel(logging.DEBUG)
        if not basic_logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            basic_logger.addHandler(console_handler)
        logger = basic_logger
        return basic_logger

def dh_log(
    message: str,
    level: str = "INFO",
    context: Optional[Dict[str, Any]] = None,
    show_trace: bool = False
) -> None:
    """
    Log a message with proper level validation and context handling.
    
    Args:
        message: The message to log
        level: Log level (must be one of: INFO, DEBUG, WARNING, ERROR)
        context: Optional dictionary of contextual information
        show_trace: Whether to include stack trace
    
    Raises:
        ValueError: If level is not one of the valid log levels
    """
    try:
        # Validate and normalize log level
        valid_levels = {"INFO", "DEBUG", "WARNING", "ERROR"}
        level = level.upper() if isinstance(level, str) else "INFO"
        if level not in valid_levels:
            raise ValueError(f"Invalid log level: {level}. Must be one of: {', '.join(valid_levels)}")

        # Ensure context is a dictionary
        context = context or {}
        
        # Add caller information to context if not present and not from frontend
        if not any(key in context for key in ['file', 'function', 'line']) and context.get('source') != 'frontend':
            caller_info = get_caller_info()
            context.update({
                "file": caller_info.get('file'),
                "function": caller_info.get('function'),
                "line": caller_info.get('line')
            })

        # Get log level from string
        log_level = getattr(logging, level, logging.INFO)
        
        # For ERROR level or when show_trace is True, get the full call stack
        if level == "ERROR" or show_trace:
            stack = inspect.stack()
            # Skip the first two frames (this function and the caller)
            call_stack = []
            for frame_info in stack[2:]:
                frame = frame_info.frame
                code = frame.f_code
                # Only include frames from our application code
                if code.co_filename.startswith('/app/backend/'):
                    # Filter out query_vector from locals
                    locals_dict = {k: str(v) for k, v in frame.f_locals.items() 
                                 if k not in ['self', 'cls', 'query_vector', 'query_embedding']}
                    call_stack.append({
                        'file': code.co_filename,
                        'function': code.co_name,
                        'line': frame_info.lineno,
                        'locals': locals_dict
                    })
            context["call_stack"] = call_stack
        
        # Create log record with context
        record = logging.LogRecord(
            name='dh_logger',
            level=log_level,
            pathname=context.get('file', ''),
            lineno=context.get('line', 0),
            msg=message,
            args=(),
            exc_info=None  # Remove exc_info to prevent traceback
        )
        
        # Try to serialize context, but don't fail if we can't
        try:
            record.context = context
        except Exception:
            # If we can't serialize the context, just use a minimal context
            record.context = {
                "error": "Failed to serialize context",
                "message": message,
                "level": level
            }

        # Log using logger
        if logger is not None:
            logger.handle(record)
        else:
            print(f"[EARLY LOG] {level}: {message}")

    except Exception as e:
        # Fallback logging in case of errors
        error_msg = f"Error in dh_log: {str(e)}"
        print(error_msg)
        print(f"Original message: {message}")
        print(f"Error traceback: {traceback.format_exc()}")
        
        # Try basic logging as last resort
        try:
            logging.error(error_msg)
        except:
            pass

async def send_email_notification(error: str) -> None:
    """Send error notification via Elastic Email API."""
    try:
        if not all([ADMIN_EMAIL, ELASTIC_EMAIL_API_KEY]):
            dh_log('Missing Elastic Email configuration. Skipping email notification.', 'WARNING')
            return

        api_url = 'https://api.elasticemail.com/v2/email/send'
        
        payload = {
            'apikey': ELASTIC_EMAIL_API_KEY,
            'subject': f'Error Notification from {os.getenv("SERVICE_NAME", "unknown-service")}',
            'from': ADMIN_EMAIL,  # Using admin email as sender
            'to': ADMIN_EMAIL,
            'bodyText': f"""
An error occurred in the system:

{error}

Time: {datetime.now().isoformat()}
Service: {os.getenv("SERVICE_NAME", "unknown-service")}
Environment: {os.getenv("NODE_ENV", "development")}
Server: {os.getenv("SERVER_NAME", "unknown-server")}
"""
        }

        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if result.get('success'):
            dh_log('Error notification email sent successfully via Elastic Email API.')
        else:
            dh_log(f'Error sending email via Elastic Email API: {result.get("error")}', 'ERROR')
        
    except Exception as email_error:
        error_details = {
            'message': str(email_error),
            'stack': traceback.format_exc(),
            'api_url': api_url
        }
        dh_log('Error sending email notification via Elastic Email API', 'ERROR', error_details)

async def send_error_notification(error: str) -> None:
    """Send error notification based on configured method."""
    try:
        if os.getenv('NODE_ENV') != 'production':
            dh_log('Skipping error notification in non-production environment.', 'INFO')
            return

        if NOTIFICATION_METHOD == 'service' and NOTIFICATIONS_SERVICE_URL:
            # Send to notification service
            payload = {
                'source': os.getenv('SERVICE_NAME', 'unknown-service'),
                'message': 'An error occurred in the system',
                'error': error
            }
            
            response = requests.post(
                NOTIFICATIONS_SERVICE_URL,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            dh_log('Error notification sent successfully to service.')
            
        elif NOTIFICATION_METHOD == 'email':
            # Send email notification
            await send_email_notification(error)
            
        else:
            dh_log(
                f'Invalid notification method ({NOTIFICATION_METHOD}) or missing configuration. Skipping notification.',
                'WARNING'
            )
        
    except Exception as notification_error:
        error_details = {
            'message': str(notification_error),
            'stack': traceback.format_exc(),
            'notification_method': NOTIFICATION_METHOD
        }
        dh_log('Error sending notification', 'ERROR', error_details)

def dh_handle_error(
    error: Exception,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None
) -> None:
    """Handle errors and send notifications."""
    context = context or {}
    source = source or os.getenv('SERVICE_NAME', 'unknown-service')
    
    full_message = f"{message}: {str(error)}"
    error_details = {
        'stack': traceback.format_exc(),
        'source': source,
        **context
    }
    
    dh_log(full_message, 'ERROR', error_details)
    
    # Send notification
    send_error_notification(full_message)

def log_imported_packages():
    """Log all imported packages at startup"""
    dh_log(
        message="Imported packages at startup",
        level="INFO",
        context={
            "packages": [
                {"name": dist.key, "version": dist.version}
                for dist in pkg_resources.working_set
            ]
        }
    )

