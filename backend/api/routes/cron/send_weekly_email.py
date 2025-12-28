"""
Send weekly combinations email endpoint.
Gets the latest prediction combinations and sends them via email service.
Praise the FSM for automated email sending!
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import requests
import os
from db.base import SessionLocal
from models import Prediction, GeneratedCombination, Model
from logger import logger
import time

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/cron/send-weekly-combinations-email")
async def send_weekly_combinations_email(db: Session = Depends(get_db)):
    """Get latest weekly combinations and send them via email"""
    start_time = time.time()
    logger.info("Arrr! Starting weekly combinations email sending, praisin' the FSM!", context={"start_time": start_time})
    
    try:
        # Get the latest prediction with combinations
        logger.info("Arrr! Querying latest prediction...")
        latest_prediction = db.query(Prediction).order_by(desc(Prediction.id)).first()
        
        if not latest_prediction:
            error_msg = "No predictions found in database"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        logger.info(f"Arrr! Found prediction {latest_prediction.id}")
        
        # Get all combinations for this prediction
        logger.info("Arrr! Querying combinations...")
        combinations = db.query(GeneratedCombination).filter(
            GeneratedCombination.prediction_id == latest_prediction.id
        ).order_by(GeneratedCombination.position).all()
        
        if not combinations:
            error_msg = f"No combinations found for prediction {latest_prediction.id}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        logger.info(f"Arrr! Found {len(combinations)} combinations")
        
        # Get model names
        main_model = db.query(Model).filter(Model.id == latest_prediction.model_id).first()
        strong_model = db.query(Model).filter(Model.id == latest_prediction.strong_model_id).first()
        
        # Format tables for email
        tables = []
        for combo in combinations:
            tables.append({
                "numbers": combo.numbers,
                "strong": combo.strong_number
            })
        
        # Format model info
        model_info = {
            "main_model": main_model.name if main_model else "Unknown",
            "strong_model": strong_model.name if strong_model else "Unknown",
            "roi_ratio": f"{latest_prediction.roi:.2%}" if latest_prediction.roi else "N/A",
            "total_prize": f"₪{latest_prediction.total_prize:,.2f}" if latest_prediction.total_prize else "₪0.00",
            "total_cost": f"₪{latest_prediction.total_cost:,.2f}" if latest_prediction.total_cost else "₪0.00",
            "total_predictions": 1
        }
        
        logger.info(
            "Arrr! Prepared email data",
            context={
                "prediction_id": latest_prediction.id,
                "num_combinations": len(tables),
                "main_model": model_info["main_model"],
                "strong_model": model_info["strong_model"]
            }
        )
        
        # Send to email service
        # Use environment variable or default to localhost:8001 (we know it works from earlier test)
        email_service_url = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:8001')
        logger.info(f"Arrr! Using email service: {email_service_url}")
        
        email_data = {
            "date": datetime.now().date().isoformat(),
            "tables": tables,
            "model_info": model_info
        }
        
        try:
            logger.info(f"Arrr! Sending email to {email_service_url}/send-best-model-tables")
            response = requests.post(
                f"{email_service_url}/send-best-model-tables",
                json=email_data,
                timeout=10  # Reduced timeout
            )
            response.raise_for_status()
            
            total_time = time.time() - start_time
            
            logger.info(
                "Arrr! Weekly combinations email sent successfully!",
                context={
                    "prediction_id": latest_prediction.id,
                    "num_combinations": len(tables),
                    "total_time": f"{total_time:.2f}s"
                }
            )
            
            return {
                "status": "success",
                "message": "Weekly combinations email sent successfully",
                "prediction_id": latest_prediction.id,
                "num_combinations": len(tables),
                "total_time": f"{total_time:.2f}s"
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(
                "Arrr! Failed to send email!",
                context={
                    "error": str(e),
                    "email_service_url": email_service_url,
                    "prediction_id": latest_prediction.id
                }
            )
            raise HTTPException(status_code=500, detail=error_msg)
            
    except Exception as e:
        error_msg = f"Error sending weekly combinations email: {str(e)}"
        logger.error(
            "Arrr! Error in send weekly combinations email endpoint!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        raise HTTPException(status_code=500, detail=str(e))
