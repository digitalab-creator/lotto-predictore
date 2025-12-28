FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY worker/requirements.txt /app/worker-requirements.txt
COPY backend/requirements.txt /app/backend-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/worker-requirements.txt && \
    pip install --no-cache-dir -r /app/backend-requirements.txt

# Copy application code
COPY backend /app
COPY shared /app/shared

# Set Python path
ENV PYTHONPATH=/app:/app/scripts

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Default command: run RQ worker
# Import the workers module so tasks are registered
CMD ["sh", "-c", "cd /app && python -c 'import services.queue.workers' && rq worker --url redis://redis:6379/0 default --path /app"]

