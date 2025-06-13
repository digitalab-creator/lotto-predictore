# Email Service

A microservice for handling email communications in the Lotto Predictor system.

## Features

- Send HTML emails using templates
- Support for attachments
- Error notifications
- Weekly lottery tables
- Logging to both console and file
- FastAPI endpoints for easy integration

## Setup

1. Create a `.env` file with the following variables:
```env
SMTP_HOST=smtp-relay.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
SENDER_EMAIL=your-sender@email.com
RECIPIENT_EMAIL=your-recipient@email.com
```

2. Build and run the service:
```bash
docker-compose up -d email-service
```

## API Endpoints

### Send Email
```http
POST /send-email
Content-Type: application/json

{
    "subject": "Test Subject",
    "template_name": "test_template.html",
    "template_data": {
        "key": "value"
    },
    "attachments": [
        {
            "path": "/path/to/file",
            "filename": "file.pdf"
        }
    ]
}
```

### Send Weekly Tables
```http
POST /send-weekly-tables
Content-Type: application/json

{
    "date": "2024-01-01",
    "tables": [
        {
            "numbers": [1, 2, 3],
            "strong": 4
        }
    ],
    "attachments": [
        {
            "path": "/path/to/file",
            "filename": "file.pdf"
        }
    ]
}
```

### Send Error Notification
```http
POST /send-error-notification
Content-Type: application/json

{
    "error_message": "Test Error",
    "service": "test_service",
    "script": "test_script.py",
    "traceback": "test traceback"
}
```

## Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest
```

3. Run service locally:
```bash
uvicorn src.main:app --reload
```

## Logging

Logs are written to both console and file:
- Console: Standard output
- File: `/app/logs/email_service.log`

## Templates

Email templates are stored in the `/app/templates` directory:
- `weekly_tables.html`: Template for weekly lottery tables
- `error_notification.html`: Template for error notifications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 