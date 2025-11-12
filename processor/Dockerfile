# Processor Service Dockerfile
# Handles: orchestrator, news_agent, client_based_recommendation
# Using non-slim base for better library support (OpenGL, etc.)
FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies
# Note: Some packages (like mineru, docling) need OpenGL libraries for image processing
# libgl1 provides libGL.so.1 (automatically pulls in libglvnd0 and libglx0 as dependencies)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy all service directories
COPY orchestrator/ /app/orchestrator/
COPY news_agent/ /app/news_agent/
COPY client_based_recommendation/ /app/client_based_recommendation/
COPY cognium_codebase/ /app/cognium_codebase/
COPY email_sending_agent/ /app/email_sending_agent/

# Copy the unified API file
COPY api.py /app/api.py

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run the FastAPI application
# This container now serves both API endpoints and processing capabilities
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

