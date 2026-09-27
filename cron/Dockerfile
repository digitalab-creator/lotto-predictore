FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY cron/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory with correct permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy cron service code and shared library
COPY cron/ ./cron/
COPY shared/ ./shared/

# Copy and setup backup script
COPY scripts/backup_db.sh ./scripts/backup_db.sh
RUN chmod +x ./scripts/backup_db.sh

ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["python", "cron/main.py"]
