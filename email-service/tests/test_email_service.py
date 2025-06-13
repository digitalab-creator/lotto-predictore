import os
import pytest
from unittest.mock import patch, MagicMock
from src.email_service import EmailService

@pytest.fixture
def mock_env_vars():
    """Mock environment variables"""
    with patch.dict(os.environ, {
        'SMTP_HOST': 'smtp.test.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@test.com',
        'SMTP_PASSWORD': 'test_password',
        'SENDER_EMAIL': 'sender@test.com',
        'RECIPIENT_EMAIL': 'recipient@test.com'
    }):
        yield

@pytest.fixture
def email_service(mock_env_vars):
    """Create email service instance"""
    return EmailService()

def test_init_missing_config():
    """Test initialization with missing configuration"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            EmailService()

def test_send_email_success(email_service):
    """Test successful email sending"""
    with patch('smtplib.SMTP') as mock_smtp:
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Send email
        result = email_service.send_email(
            subject='Test Subject',
            template_name='test_template.html',
            template_data={'test': 'data'}
        )
        
        # Verify
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            'test@test.com',
            'test_password'
        )
        mock_server.send_message.assert_called_once()

def test_send_email_failure(email_service):
    """Test failed email sending"""
    with patch('smtplib.SMTP') as mock_smtp:
        # Setup mock to raise exception
        mock_smtp.side_effect = Exception('SMTP Error')
        
        # Send email
        result = email_service.send_email(
            subject='Test Subject',
            template_name='test_template.html',
            template_data={'test': 'data'}
        )
        
        # Verify
        assert result is False

def test_send_weekly_tables(email_service):
    """Test sending weekly tables"""
    with patch.object(email_service, 'send_email') as mock_send:
        # Send weekly tables
        email_service.send_weekly_tables(
            date='2024-01-01',
            tables=[{'numbers': [1, 2, 3], 'strong': 4}]
        )
        
        # Verify
        mock_send.assert_called_once_with(
            subject='Weekly Lottery Tables - 2024-01-01',
            template_name='weekly_tables.html',
            template_data={
                'date': '2024-01-01',
                'tables': [{'numbers': [1, 2, 3], 'strong': 4}]
            },
            attachments=None
        )

def test_send_error_notification(email_service):
    """Test sending error notification"""
    with patch.object(email_service, 'send_email') as mock_send:
        # Send error notification
        email_service.send_error_notification(
            error_message='Test Error',
            service='test_service',
            script='test_script.py',
            traceback='test traceback'
        )
        
        # Verify
        mock_send.assert_called_once_with(
            subject='Error Notification - test_service',
            template_name='error_notification.html',
            template_data={
                'error_message': 'Test Error',
                'service': 'test_service',
                'script': 'test_script.py',
                'traceback': 'test traceback'
            }
        ) 