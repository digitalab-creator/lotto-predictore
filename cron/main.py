import os
import sys
from pathlib import Path
from fastapi import FastAPI
import uvicorn
from threading import Thread
from shared.logging_service import get_cron_logger
from .api_endpoints import (
    call_backend_endpoint,
    health_check_endpoint,
    check_model_files_endpoint,
    cleanup_system_endpoint,
    backup_database_endpoint
)
from .scheduler import setup_jobs, run_scheduler

# Add shared directory to Python path
shared_dir = Path('/app/shared')
sys.path.append(str(shared_dir))

# Initialize FastAPI app
app = FastAPI(title="Cron Service")

# Get logger instance
logger = get_cron_logger()

# Global state for health check
last_successful_job = {
    "generate-weekly-combinations": None,
    "fetch-latest-draw": None,
    "generate-weekly-tables": None,
    "update-weekly-winning-combinations": None,
    "cleanup-system": None,
    "backup-database": None
}

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint that verifies cron service and backend connection"""
    return health_check_endpoint(last_successful_job)

@app.post("/api/check-model-files")
async def check_model_files():
    """
    Endpoint that calls the backend service to check model files.
    If any corrupted files are found, sends email notification.
    """
    return check_model_files_endpoint()

@app.post("/api/cleanup-system")
async def cleanup_system():
    """
    Endpoint to manually trigger comprehensive system cleanup.
    This includes log cleanup and Docker system pruning.
    """
    return cleanup_system_endpoint()

@app.post("/api/backup-database")
async def backup_database():
    """
    Endpoint to manually trigger database backup.
    This creates a compressed database dump with timestamp.
    """
    return backup_database_endpoint()

if __name__ == "__main__":
    logger.info("Arrr! Starting cron service...")
    setup_jobs(last_successful_job)
    
    # Start scheduler in a separate thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8002) 