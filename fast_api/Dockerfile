# FastAPI Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
# Note: Only installing FastAPI and uvicorn for this lightweight API container
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
