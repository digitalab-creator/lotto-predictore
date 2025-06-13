FROM python:3.11-slim

WORKDIR /app

# Install only the required packages
COPY cron/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt watchdog[watchmedo]

# Create logs directory with correct permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy cron service code and shared library
COPY cron/ ./cron/
COPY shared/ ./shared/

# Add shared directory to PYTHONPATH
ENV PYTHONPATH=/app

# Run the cron service with watchmedo for hot reloading
CMD ["watchmedo", "auto-restart", "--directory=/app", "--pattern=*.py", "--recursive", "--", "python", "cron/main.py"] 