with open('docker-compose.yml', 'w', encoding='utf-8') as f:
    f.write('''version: '3.8'

services:
  grokputer:
    build: .
    container_name: grokputer-main
    env_file:
      - .env
    volumes:
      - ./vault:/app/vault
      - ./logs:/app/logs
      - ./saves:/app/saves
    ports:
      - "8000:8000"  # API if needed
    profiles:
      - default
    environment:
      - DISPLAY=:99
    depends_on:
      - redis
    command: python main.py --task "${TASK:-invoke server prayer}" --max-iterations 1

  grokputer-vnc:
    build:
      context: .
      dockerfile: Dockerfile.vnc  # Assume updated Dockerfile with VNC
    container_name: grokputer-vnc
    env_file:
      - .env
    volumes:
      - ./vault:/app/vault
      - ./logs:/app/logs
      - ./saves:/app/saves
    ports:
      - "5900:5900"  # VNC port
      - "8000:8000"
    profiles:
      - debug
    environment:
      - DISPLAY=:1
      - VNC_PASSWORD=secret  # Set in .env or here
    depends_on:
      - redis
    command: /entrypoint-vnc.sh  # Start VNC + Xvfb + app

  redis:
    image: redis:alpine
    container_name: grokputer-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:

# Usage:
# Basic: TASK="your task" docker-compose up
# Debug VNC: docker-compose --profile debug up grokputer-vnc
# Connect VNC: vncviewer localhost:5900 (password: secret)
''')

print('docker-compose.yml updated for cross-platform VNC/visual support')