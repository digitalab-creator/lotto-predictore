FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks and Docker CLI
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Add Docker's official GPG key
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the Docker repository
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker CLI
RUN apt-get update && apt-get install -y docker-ce-cli && rm -rf /var/lib/apt/lists/*

# Install only the required packages
COPY cron/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt watchdog[watchmedo]

# Create logs directory with correct permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy cron service code and shared library
COPY cron/ ./cron/
COPY shared/ ./shared/

# Copy and setup backup script
COPY scripts/backup_db.sh ./scripts/backup_db.sh
RUN chmod +x ./scripts/backup_db.sh

# Add shared directory to PYTHONPATH
ENV PYTHONPATH=/app

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the cron service with watchmedo for hot reloading
CMD ["watchmedo", "auto-restart", "--directory=/app", "--pattern=*.py", "--recursive", "--", "python", "cron/main.py"] 