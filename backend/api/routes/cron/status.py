from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import datetime
from services.core.cron_tracker import CronTracker
from logger import logger
from .utils import get_model_prediction_details_count, get_balanced_algorithm_list

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/cron/prediction-balance-status")
async def get_prediction_balance_status(db: Session = Depends(get_db)):
    """Get the current balance status of prediction details across all models"""
    try:
        current_counts = get_model_prediction_details_count(db)
        balanced_algorithms = get_balanced_algorithm_list(db, target_details_per_model=100)
        
        # Calculate statistics
        all_counts = list(current_counts.values())
        min_count = min(all_counts) if all_counts else 0
        max_count = max(all_counts) if all_counts else 0
        avg_count = sum(all_counts) / len(all_counts) if all_counts else 0
        
        # Group by main algorithm
        main_algo_stats = {}
        for key, count in current_counts.items():
            main_algo = key.split('_')[0]  # Extract main algorithm name
            if main_algo not in main_algo_stats:
                main_algo_stats[main_algo] = []
            main_algo_stats[main_algo].append(count)
        
        # Calculate average per main algorithm
        main_algo_averages = {
            algo: sum(counts) / len(counts) 
            for algo, counts in main_algo_stats.items()
        }
        
        return {
            "status": "success",
            "balance_summary": {
                "total_model_combinations": len(current_counts),
                "min_prediction_details": min_count,
                "max_prediction_details": max_count,
                "average_prediction_details": round(avg_count, 2),
                "models_needing_data": len(balanced_algorithms),
                "target_details_per_model": 100
            },
            "top_models_needing_data": [
                {
                    "main_algo": combo['main_algo'],
                    "strong_algo": combo['strong_algo'],
                    "current_details": combo['current_details'],
                    "priority_score": combo['priority_score']
                }
                for combo in balanced_algorithms[:10]
            ],
            "main_algorithm_averages": {
                algo: round(avg, 2) for algo, avg in main_algo_averages.items()
            },
            "all_model_details": current_counts
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Error getting prediction balance status!",
            context={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cron/status")
async def get_cron_status(db: Session = Depends(get_db)):
    """Get detailed status of all cron jobs from the database"""
    try:
        tracker = CronTracker(db)
        job_summary = tracker.get_job_status_summary()
        
        return {
            "status": "success",
            "jobs": job_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(
            "Arrr! Failed to get cron status!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to get cron status: {str(e)}"
            }
        ) 