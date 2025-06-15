FROM python:3.9-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY email-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory with correct permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy the source code
COPY email-service/src /app/src
COPY email-service/templates /app/templates
COPY shared /app/shared

# Add src to Python path
ENV PYTHONPATH=/app

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service with uvicorn hot reloading
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"] 