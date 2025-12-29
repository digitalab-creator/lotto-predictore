#!/usr/bin/env python3
"""
Schedule weekly combinations job to run in 2 minutes via HTTP.
Praisin' the FSM! 🍝⚓
"""
import sys
import os
import time
import threading
import requests
from datetime import datetime, timedelta

# Set up backend path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger

logger = get_backend_logger()

def trigger_weekly_job():
    """Trigger the weekly combinations job via HTTP"""
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    endpoint = f"{base_url}/cron/generate-weekly-combinations-optimized"
    
    logger.info(
        "Arrr! Triggering weekly combinations job!",
        context={"endpoint": endpoint}
    )
    
    try:
        response = requests.post(endpoint, timeout=3600)  # 1 hour timeout
        logger.info(
            "Arrr! Weekly job triggered successfully!",
            context={
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text[:500]
            }
        )
        return response.json() if response.status_code == 200 else {"status": "error", "message": response.text}
    except Exception as e:
        logger.error(
            "Arrr! Failed to trigger weekly job!",
            context={"error": str(e), "endpoint": endpoint}
        )
        raise

def schedule_in_2_minutes():
    """Schedule job to run in 2 minutes"""
    scheduled_time = datetime.now() + timedelta(minutes=2)
    
    logger.info(
        "Arrr! Scheduling weekly job for 2 minutes from now!",
        context={
            "scheduled_time": scheduled_time.isoformat(),
            "current_time": datetime.now().isoformat()
        }
    )
    
    # Wait 2 minutes (120 seconds)
    time.sleep(120)
    
    # Trigger the job
    return trigger_weekly_job()

if __name__ == "__main__":
    # Run in background thread so script can exit
    thread = threading.Thread(target=schedule_in_2_minutes, daemon=False)
    thread.start()
    
    scheduled_time = datetime.now() + timedelta(minutes=2)
    print(f"Arrr! Weekly job scheduled for {scheduled_time.isoformat()}, praisin' the FSM!")
    print("Script running in background. Job will execute in 2 minutes.")
    
    # Keep main thread alive
    thread.join()

