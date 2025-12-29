"""
Schedule weekly combinations job to run in 2 minutes.
Praisin' the FSM! 🍝⚓
"""
import sys
import os
from datetime import datetime, timedelta

# Set up backend path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.path_setup import setup_backend_path
setup_backend_path()

from rq import Queue
from services.queue.redis_client import get_redis_client
from shared.logging_service import get_backend_logger
import requests
import time

logger = get_backend_logger()

def schedule_weekly_job_in_2_minutes():
    """Schedule the weekly combinations job to run in 2 minutes"""
    # Calculate time 2 minutes from now
    scheduled_time = datetime.now() + timedelta(minutes=2)
    
    logger.info(
        "Arrr! Scheduling weekly combinations job!",
        context={
            "scheduled_time": scheduled_time.isoformat(),
            "minutes_from_now": 2
        }
    )
    
    # Option 1: Use RQ scheduler if available
    try:
        from rq_scheduler import Scheduler
        scheduler = Scheduler(connection=get_redis_client())
        
        # Schedule the job
        job = scheduler.enqueue_at(
            scheduled_time,
            'api.routes.cron.combinations.optimized_combinations.generate_weekly_combinations_optimized'
        )
        
        logger.info(
            "Arrr! Weekly job scheduled using RQ Scheduler!",
            context={
                "job_id": job.id,
                "scheduled_time": scheduled_time.isoformat()
            }
        )
        return job.id
    except ImportError:
        logger.warning("RQ Scheduler not available, using HTTP endpoint instead")
    except Exception as e:
        logger.warning(
            "Arrr! Failed to use RQ Scheduler, falling back to HTTP",
            context={"error": str(e)}
        )
    
    # Option 2: Use HTTP endpoint with a delay (if scheduler not available)
    # We'll use a simple approach: make HTTP call in 2 minutes
    import threading
    
    def call_endpoint():
        time.sleep(120)  # Wait 2 minutes
        try:
            # Get base URL from environment or use default
            base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
            response = requests.post(f"{base_url}/cron/generate-weekly-combinations-optimized")
            logger.info(
                "Arrr! Weekly job triggered via HTTP!",
                context={
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
            )
        except Exception as e:
            logger.error(
                "Arrr! Failed to trigger weekly job via HTTP!",
                context={"error": str(e)}
            )
    
    thread = threading.Thread(target=call_endpoint, daemon=True)
    thread.start()
    
    logger.info(
        "Arrr! Weekly job scheduled via HTTP thread!",
        context={"scheduled_time": scheduled_time.isoformat()}
    )
    
    return "http_thread"

if __name__ == "__main__":
    schedule_weekly_job_in_2_minutes()

