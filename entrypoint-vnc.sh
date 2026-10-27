#!/bin/bash

# Start Xvfb
export DISPLAY=:1
Xvfb :1 -screen 0 1024x768x16 -ac +extension GLX +render -noreset &

# Wait for Xvfb
sleep 2

# Start VNC server
vncserver :1 -geometry 1024x768 -depth 16 -localhost no -passwd $VNC_PASSWORD

# Start XFCE desktop
startxfce4 &

# Run the app
exec python main.py --task "${TASK:-invoke server prayer}"