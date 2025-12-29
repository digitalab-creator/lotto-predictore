#!/usr/bin/env python3
"""
Schedule weekly combinations job to run in 2 minutes.
Praisin' the FSM! 🍝⚓
"""
import sys
import os
import time
import requests
from datetime import datetime, timedelta

# Set up backend path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger

logger = get_backend_logger()

def schedule_weekly_job():
    """Schedule the weekly combinations job to run in 2 minutes"""
    # Calculate time 2 minutes from now
    scheduled_time = datetime.now() + timedelta(minutes=2)
    current_time = datetime.now()
    
    logger.info(
        "Arrr! Scheduling weekly combinations job!",
        context={
            "current_time": current_time.isoformat(),
            "scheduled_time": scheduled_time.isoformat(),
            "minutes_from_now": 2
        }
    )
    
    print(f"Arrr! Scheduling weekly job for {scheduled_time.isoformat()}, praisin' the FSM!")
    print(f"Current time: {current_time.isoformat()}")
    print(f"Waiting 2 minutes (120 seconds)...")
    
    # Wait 2 minutes (120 seconds)
    time.sleep(120)
    
    # Trigger the job
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    endpoint = f"{base_url}/cron/generate-weekly-combinations-optimized"
    
    logger.info(
        "Arrr! Triggering weekly combinations job!",
        context={"endpoint": endpoint, "scheduled_time": scheduled_time.isoformat()}
    )
    
    print(f"Arrr! Triggering job at {datetime.now().isoformat()}, praisin' the FSM!")
    
    try:
        response = requests.post(endpoint, timeout=3600)  # 1 hour timeout for long-running job
        result = response.json() if response.status_code == 200 else {"status": "error", "message": response.text}
        
        logger.info(
            "Arrr! Weekly job triggered successfully!",
            context={
                "status_code": response.status_code,
                "result": result
            }
        )
        
        print(f"Job triggered! Status: {response.status_code}")
        print(f"Result: {result}")
        
        return result
    except Exception as e:
        logger.error(
            "Arrr! Failed to trigger weekly job!",
            context={"error": str(e), "endpoint": endpoint}
        )
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    schedule_weekly_job()

