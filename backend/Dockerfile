# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic

RUN apt-get update && apt-get install -y supervisor curl && rm -rf /var/lib/apt/lists/*

# Create logs directory with correct permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

COPY backend/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1 