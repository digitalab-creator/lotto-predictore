import os
import sys
import schedule
import time
import requests
from datetime import datetime
from pathlib import Path

# Add shared directory to Python path
shared_dir = Path('/app/shared')
sys.path.append(str(shared_dir))

# Import shared logging service
from shared.logging_service import get_cron_logger

# Get logger instance
logger = get_cron_logger()

def call_backend_endpoint(endpoint: str) -> None:
    """
    Call a backend API endpoint.
    
    Args:
        endpoint (str): The endpoint to call (e.g., '/cron/generate-weekly-combinations')
    """
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
        url = f"{backend_url}{endpoint}"
        logger.info(f"Arrr! Attempting to call backend endpoint: {url}")
        
        # Test backend connection first
        try:
            health_check = requests.get(f"{backend_url}/docs")
            health_check.raise_for_status()
            logger.info("Arrr! Backend health check successful!")
        except Exception as health_error:
            logger.error(
                "Arrr! Backend health check failed!",
                context={
                    "error": str(health_error),
                    "url": f"{backend_url}/docs"
                }
            )
            raise
        
        # Call the actual endpoint
        logger.info(f"Arrr! Sending POST request to: {url}")
        response = requests.post(url)
        response.raise_for_status()
        
        logger.info(f"Arrr! Successfully called {endpoint}: {response.json()}")
    except requests.exceptions.ConnectionError as e:
        logger.error(
            "Arrr! Connection error calling endpoint!",
            context={
                "error": str(e),
                "endpoint": endpoint,
                "backend_url": backend_url
            }
        )
    except requests.exceptions.Timeout as e:
        logger.error(
            "Arrr! Timeout calling endpoint!",
            context={
                "error": str(e),
                "endpoint": endpoint,
                "backend_url": backend_url
            }
        )
    except Exception as e:
        logger.error(
            f"Arrr! Error calling endpoint {endpoint}!",
            context={
                "error": str(e),
                "endpoint": endpoint,
                "backend_url": backend_url
            }
        )
        # Notify via API
        try:
            requests.post(
                f"{backend_url}/api/notifications/error",
                json={
                    "error": str(e),
                    "endpoint": endpoint,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as notify_error:
            logger.error(
                "Arrr! Failed to send error notification!",
                context={
                    "error": str(notify_error),
                    "original_error": str(e)
                }
            )

def setup_jobs():
    """Set up all scheduled jobs"""
    # Weekly combinations generation - runs every Sunday at 3:00 AM
    schedule.every().sunday.at("03:00").do(
        lambda: call_backend_endpoint("/cron/generate-weekly-combinations")
    )
    
    # Daily latest draw fetch - runs every day at 3:00 AM
    schedule.every().day.at("03:00").do(
        lambda: call_backend_endpoint("/cron/fetch-latest-draw")
    )
    
    # Weekly table generation - runs every Sunday at 10:00 AM
    schedule.every().sunday.at("10:00").do(
        lambda: call_backend_endpoint("/cron/generate-weekly-tables")
    )
    
    logger.info("Arrr! All jobs scheduled successfully!")

if __name__ == "__main__":
    logger.info("Arrr! Starting cron service...")
    setup_jobs()
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(
                "Arrr! Error in main loop!",
                context={"error": str(e)}
            )
            time.sleep(60)  # Wait before retrying 