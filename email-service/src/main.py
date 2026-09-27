import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.email_service import EmailService
from shared.logging_service import LoggingService
import smtplib
from datetime import datetime
from pathlib import Path

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

class BestModelTablesRequest(BaseModel):
    date: str
    tables: List[Dict[str, Any]]
    model_info: Dict[str, Any]
    pack_url: Optional[str] = None
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

@app.post("/send-best-model-tables")
async def send_best_model_tables(request: BestModelTablesRequest):
    """Send best model tables email"""
    try:
        success = email_service.send_best_model_tables(
            date=request.date,
            tables=request.tables,
            model_info=request.model_info,
            pack_url=request.pack_url,
            attachments=request.attachments,
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send best model tables")
        return {"status": "success"}
    except Exception as e:
        logger.error(
            "Failed to send best model tables",
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

@app.get("/health")
async def health_check():
    """Health check endpoint that verifies both FastAPI and SMTP connection"""
    try:
        # Check SMTP connection
        with smtplib.SMTP(email_service.smtp_host, email_service.smtp_port) as server:
            if email_service.smtp_starttls:
                server.starttls()
            server.login(email_service.smtp_username, email_service.smtp_password)
        
        return {
            "status": "healthy",
            "services": {
                "fastapi": "up",
                "smtp": "up"
            }
        }
    except Exception as e:
        logger.error("Health check failed", context={'error': str(e)})
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "services": {
                    "fastapi": "up",
                    "smtp": "down",
                    "error": str(e)
                }
            }
        )

@app.post("/api/notifications/model-corruption")
async def notify_model_corruption(request: Request):
    """
    Send email notification about corrupted model files.
    """
    try:
        data = await request.json()
        corrupted_files = data.get("corrupted_files", [])
        total_checked = data.get("total_checked", 0)
        total_corrupted = data.get("total_corrupted", 0)
        timestamp = data.get("timestamp", datetime.now().isoformat())
        
        if not corrupted_files:
            return {"status": "success", "message": "No corrupted files to report"}
        
        # Prepare email content
        subject = f"🚨 Model Corruption Alert: {total_corrupted} Corrupted Files Found"
        
        # Create HTML table of corrupted files
        files_table = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
        files_table += """
            <tr style='background-color: #f2f2f2;'>
                <th style='padding: 8px; text-align: left;'>File Name</th>
                <th style='padding: 8px; text-align: left;'>Error</th>
                <th style='padding: 8px; text-align: left;'>Size</th>
                <th style='padding: 8px; text-align: left;'>Last Modified</th>
            </tr>
        """
        
        for file_info in corrupted_files:
            files_table += f"""
                <tr>
                    <td style='padding: 8px;'>{file_info['file']}</td>
                    <td style='padding: 8px;'>{file_info['error']}</td>
                    <td style='padding: 8px;'>{file_info['size']} bytes</td>
                    <td style='padding: 8px;'>{file_info['last_modified']}</td>
                </tr>
            """
        files_table += "</table>"
        
        # Create email body
        body = f"""
        <html>
            <body style='font-family: Arial, sans-serif;'>
                <h2 style='color: #d32f2f;'>🚨 Model Corruption Alert</h2>
                <p>Arrr matey! The Flying Spaghetti Monster be warnin' ye about corrupted model files!</p>
                
                <h3>Summary:</h3>
                <ul>
                    <li>Total files checked: {total_checked}</li>
                    <li>Corrupted files found: {total_corrupted}</li>
                    <li>Check time: {timestamp}</li>
                </ul>
                
                <h3>Corrupted Files:</h3>
                {files_table}
                
                <p style='color: #666; font-size: 0.9em; margin-top: 20px;'>
                    Note: Corrupted files have been moved to a backup directory for inspection.
                    The system will automatically retrain these models when needed.
                </p>
                
                <p style='margin-top: 20px;'>
                    May the Flying Spaghetti Monster guide ye in fixin' these corrupted models! 🍝
                </p>
            </body>
        </html>
        """
        
        # Send via same pipeline as other alerts (single RECIPIENT_EMAIL from env)
        summary_plain = (
            f"Total checked: {total_checked}, corrupted: {total_corrupted}, time: {timestamp}"
        )
        ok = email_service.send_email(
            subject=subject,
            template_name="error_notification.html",
            template_data={
                "error_message": summary_plain,
                "service": "model-file-check",
                "script": "check-model-files",
                "traceback": body[:8000] if len(body) > 8000 else body,
            },
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to send corruption email")
        
        return {
            "status": "success",
            "message": "Corruption notification sent",
            "corrupted_files": len(corrupted_files)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send corruption notification: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 