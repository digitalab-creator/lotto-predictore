FROM python:3.11-slim

WORKDIR /app

# Install required packages
COPY db-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy database service code
COPY db-service /app/db-service
COPY shared /app/shared
COPY backend/alembic /app/alembic
COPY backend/alembic.ini /app/alembic.ini

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from db_service.health import check_db_health; check_db_health()" || exit 1

CMD ["python", "-m", "db_service.main"] 