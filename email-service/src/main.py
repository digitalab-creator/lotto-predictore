import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.email_service import EmailService
from shared.logging_service import LoggingService

# Initialize FastAPI app
app = FastAPI(title="Email Service")

# Initialize services
logger = LoggingService('email_service')
email_service = EmailService()

# Request models
class EmailRequest(BaseModel):
    subject: str
    template_name: str
    template_data: Dict[str, Any]
    attachments: Optional[List[Dict[str, Any]]] = None

class WeeklyTablesRequest(BaseModel):
    date: str
    tables: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = None

class ErrorNotificationRequest(BaseModel):
    error_message: str
    service: str
    script: Optional[str] = None
    traceback: Optional[str] = None

@app.post("/send-email")
async def send_email(request: EmailRequest):
    """Send a generic email using a template"""
    try:
        success = email_service.send_email(
            subject=request.subject,
            template_name=request.template_name,
            template_data=request.template_data,
            attachments=request.attachments
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")
        return {"status": "success"}
    except Exception as e:
        logger.error(
            "Failed to send email",
            context={
                'error': str(e),
                'subject': request.subject,
                'template': request.template_name
            }
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-weekly-tables")
async def send_weekly_tables(request: WeeklyTablesRequest):
    """Send weekly lottery tables email"""
    try:
        success = email_service.send_weekly_tables(
            date=request.date,
            tables=request.tables,
            attachments=request.attachments
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send weekly tables")
        return {"status": "success"}
    except Exception as e:
        logger.error(
            "Failed to send weekly tables",
            context={
                'error': str(e),
                'date': request.date
            }
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-error-notification")
async def send_error_notification(request: ErrorNotificationRequest):
    """Send error notification email"""
    try:
        success = email_service.send_error_notification(
            error_message=request.error_message,
            service=request.service,
            script=request.script,
            traceback=request.traceback
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send error notification")
        return {"status": "success"}
    except Exception as e:
        logger.error(
            "Failed to send error notification",
            context={
                'error': str(e),
                'service': request.service
            }
        )
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 