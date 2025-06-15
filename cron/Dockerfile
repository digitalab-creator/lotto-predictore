FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

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

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the cron service with watchmedo for hot reloading
CMD ["watchmedo", "auto-restart", "--directory=/app", "--pattern=*.py", "--recursive", "--", "python", "cron/main.py"] 