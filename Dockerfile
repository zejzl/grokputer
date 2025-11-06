# Grokputer Docker Image
# Sandbox environment for safe execution
# Based on Ubuntu with Python 3.11

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    scrot \
    python3-tk \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up virtual display for headless operation
ENV DISPLAY=:99

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/vault /app/logs

# Set Python path
ENV PYTHONPATH=/app

# Start Xvfb and run Grokputer
CMD Xvfb :99 -screen 0 1920x1080x24 & \
    python main.py --task "${TASK:-invoke server prayer}"
