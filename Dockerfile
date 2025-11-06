# Grokputer Docker Image
# Sandbox environment for safe execution
# Based on Ubuntu with Python 3.11

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    scrot \
    gnome-screenshot \
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

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN apt-get update && apt-get install -y dos2unix && dos2unix /entrypoint.sh && apt-get remove -y dos2unix && rm -rf /var/lib/apt/lists/*
RUN chmod +x /entrypoint.sh

# Set Python path
ENV PYTHONPATH=/app

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "main.py", "--task", "invoke server prayer"]
