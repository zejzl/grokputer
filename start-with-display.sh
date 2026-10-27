#!/bin/bash
# Start Xvfb and run grokputer server prayer loop

set -e

echo "[DOCKER] Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac > /tmp/xvfb.log 2>&1 &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 5

# Check if Xvfb is running
if ps -p $XVFB_PID > /dev/null; then
    echo "[DOCKER] Xvfb started successfully (PID: $XVFB_PID)"
else
    echo "[ERROR] Xvfb failed to start"
    cat /tmp/xvfb.log
    exit 1
fi

# Run the server prayer loop
echo "[DOCKER] Starting server prayer loop..."
while true; do 
    python main.py --task 'invoke server prayer'
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo "[ERROR] Server prayer failed with exit code $EXIT_CODE"
    fi
    echo "[DOCKER] Sleeping for 300 seconds..."
    sleep 300
done
