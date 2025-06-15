import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader
from shared.logging_service import LoggingService
from datetime import datetime
import re

class EmailService:
    def __init__(self):
        """Initialize email service"""
        self.logger = LoggingService('email_service')
        
        # Load environment variables
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_name = os.getenv('SENDER_NAME', 'Lotto Predictor')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        # Validate configuration
        if not all([self.smtp_username, self.smtp_password, self.sender_email, self.recipient_email]):
            self.logger.error("Missing required email configuration")
            raise ValueError("Missing required email configuration")
        
        # Setup Jinja2 environment
        template_dir = Path('/app/templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.env.globals['now'] = datetime.now  # Add now() function to templates
        
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
            # Render HTML template
            template = self.env.get_template(template_name)
            html_content = template.render(**template_data)
            
            # Create plain text version by stripping HTML
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text)  # Remove extra newlines
            plain_text = plain_text.strip()
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = self.recipient_email
            
            # Add unsubscribe footer to HTML content if not present
            if "unsubscribe" not in html_content.lower():
                unsubscribe_html = f"""
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                    <p>This is an automated notification from {self.sender_name}.</p>
                    <p>To unsubscribe from these notifications, reply to this email with the subject "unsubscribe".</p>
                </div>
                """
                html_content += unsubscribe_html
                plain_text += f"\n\nThis is an automated notification from {self.sender_name}.\nTo unsubscribe from these notifications, reply to this email with the subject 'unsubscribe'."
            
            # Attach both HTML and plain text versions
            msg.attach(MIMEText(plain_text, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Enable TLS
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            self.logger.info(
                "Email sent successfully",
                context={
                    'subject': subject,
                    'template': template_name,
                    'attachments': len(attachments) if attachments else 0,
                    'timestamp': datetime.now().isoformat()
                }
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to send email",
                context={
                    'error': str(e),
                    'subject': subject,
                    'template': template_name,
                    'timestamp': datetime.now().isoformat()
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