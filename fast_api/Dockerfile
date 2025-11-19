# FastAPI Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Docker CLI
# We need Docker CLI to execute docker exec commands
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
# Note: Installing FastAPI and uvicorn for this API container
# Docker CLI is installed above for docker exec commands
# Full dependencies will be in the processor container
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn[standard]

# Copy FastAPI application
COPY fast_api/ /app/fast_api/

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Expose port 8000
EXPOSE 8000

# Run the FastAPI application
# Using uvicorn with host 0.0.0.0 to allow external connections
CMD ["uvicorn", "fast_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
