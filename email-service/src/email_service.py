import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader
from shared.logging_service import LoggingService

class EmailService:
    def __init__(self):
        """Initialize email service"""
        self.logger = LoggingService('email_service')
        
        # Load environment variables
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp-relay.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        # Validate configuration
        if not all([self.smtp_username, self.smtp_password, self.sender_email, self.recipient_email]):
            self.logger.error("Missing required email configuration")
            raise ValueError("Missing required email configuration")
        
        # Setup Jinja2 environment
        template_dir = Path('/app/templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        self.logger.info("Email service initialized")

    def send_email(
        self,
        subject: str,
        template_name: str,
        template_data: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send an email using a template"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            # Render template
            template = self.env.get_template(template_name)
            html_content = template.render(**template_data)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    with open(attachment['path'], 'rb') as f:
                        part = MIMEApplication(f.read(), Name=attachment['filename'])
                        part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
                        msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            self.logger.info(
                "Email sent successfully",
                context={
                    'subject': subject,
                    'template': template_name,
                    'attachments': len(attachments) if attachments else 0
                }
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to send email",
                context={
                    'error': str(e),
                    'subject': subject,
                    'template': template_name
                }
            )
            return False

    def send_weekly_tables(
        self,
        date: str,
        tables: List[Dict[str, Any]],
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send weekly lottery tables email"""
        return self.send_email(
            subject=f"Weekly Lottery Tables - {date}",
            template_name='weekly_tables.html',
            template_data={
                'date': date,
                'tables': tables
            },
            attachments=attachments
        )

    def send_error_notification(
        self,
        error_message: str,
        service: str,
        script: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> bool:
        """Send error notification email"""
        return self.send_email(
            subject=f"Error Notification - {service}",
            template_name='error_notification.html',
            template_data={
                'error_message': error_message,
                'service': service,
                'script': script,
                'traceback': traceback
            }
        ) 