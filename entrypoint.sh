#!/bin/bash
# Grokputer Docker entrypoint script
# Starts Xvfb and runs the main application

set -e

# Create empty Xauthority file to prevent import errors
touch /root/.Xauthority
chmod 600 /root/.Xauthority

# Start Xvfb in the background
echo "[DOCKER] Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac > /dev/null 2>&1 &

# Wait for Xvfb to be ready
sleep 3

echo "[OK] Xvfb initialization complete"

# Execute the main command
echo "[DOCKER] Running: $@"
exec "$@"
