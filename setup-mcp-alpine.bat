@echo off
REM Grokputer Redis Alpine MCP Auto-Setup Script (Windows)
REM Automates: build, env setup, container launch, Redis key import

echo 🚀 Grokputer Redis Alpine MCP Auto-Setup
echo =========================================

REM Check prerequisites
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker first.
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python first.
    exit /b 1
)

echo [SUCCESS] Prerequisites check passed

REM Setup environment
echo [INFO] Setting up environment...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo [SUCCESS] Created .env from .env.example
        echo [WARNING] Please edit .env with your actual API keys before running!
    ) else (
        echo [ERROR] .env.example not found
        exit /b 1
    )
) else (
    echo [SUCCESS] .env already exists
)

REM Build Docker image
echo [INFO] Building Grokputer MCP Alpine image...
docker build -f Dockerfile.mcp-alpine -t grokputer-mcp-alpine:latest .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build Docker image
    exit /b 1
)
echo [SUCCESS] Docker image built successfully

REM Start container
echo [INFO] Starting container...
docker stop grokputer-mcp 2>nul
docker rm grokputer-mcp 2>nul

docker run -d --name grokputer-mcp -p 8000:8000 -p 6379:6379 --env-file .env -v "%cd%/vault:/app/vault" -v "%cd%/logs:/app/logs" grokputer-mcp-alpine:latest
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start container
    exit /b 1
)
echo [SUCCESS] Container started successfully
echo [INFO] Waiting for services to initialize...
timeout /t 5 /nobreak >nul

REM Import Redis keys
echo [INFO] Importing Redis keys...
if exist "vault\redis_backup.json" (
    REM Create temporary restore script
    echo import redis > temp_restore.py
    echo import json >> temp_restore.py
    echo import os >> temp_restore.py
    echo. >> temp_restore.py
    echo REDIS_HOST = 'localhost' >> temp_restore.py
    echo REDIS_PORT = 6379 >> temp_restore.py
    echo REDIS_DB = 0 >> temp_restore.py
    echo BACKUP_FILE = './vault/redis_backup.json' >> temp_restore.py
    echo. >> temp_restore.py
    echo def restore_redis(): >> temp_restore.py
    echo     try: >> temp_restore.py
    echo         r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True) >> temp_restore.py
    echo         r.ping() >> temp_restore.py
    echo         >> temp_restore.py
    echo         with open(BACKUP_FILE, 'r') as f: >> temp_restore.py
    echo             full_backup = json.load(f) >> temp_restore.py
    echo         >> temp_restore.py
    echo         data = full_backup.get('data', {}) >> temp_restore.py
    echo         restored_count = 0 >> temp_restore.py
    echo         errors = [] >> temp_restore.py
    echo         >> temp_restore.py
    echo         for key, value in data.items(): >> temp_restore.py
    echo             try: >> temp_restore.py
    echo                 if isinstance(value, dict) and 'error' not in value: >> temp_restore.py
    echo                     r.hset(key, mapping=value) >> temp_restore.py
    echo                 elif isinstance(value, list): >> temp_restore.py
    echo                     r.rpush(key, *value) >> temp_restore.py
    echo                 elif value is not None: >> temp_restore.py
    echo                     r.set(key, str(value)) >> temp_restore.py
    echo                 else: >> temp_restore.py
    echo                     errors.append(f"Skipped {key}: Unknown type") >> temp_restore.py
    echo                     continue >> temp_restore.py
    echo                 >> temp_restore.py
    echo                 restored_count += 1 >> temp_restore.py
    echo                 >> temp_restore.py
    echo             except Exception as e: >> temp_restore.py
    echo                 errors.append(f"Error restoring {key}: {e}") >> temp_restore.py
    echo         >> temp_restore.py
    echo         print(f"Redis restore complete: {restored_count} keys restored from {full_backup.get('total_keys', 0)} total.") >> temp_restore.py
    echo         if errors: >> temp_restore.py
    echo             print(f"Errors: {len(errors)}") >> temp_restore.py
    echo         return True >> temp_restore.py
    echo         >> temp_restore.py
    echo     except Exception as e: >> temp_restore.py
    echo         print(f"Restore failed: {e}") >> temp_restore.py
    echo         return False >> temp_restore.py
    echo. >> temp_restore.py
    echo if __name__ == '__main__': >> temp_restore.py
    echo     if restore_redis(): >> temp_restore.py
    echo         exit(0) >> temp_restore.py
    echo     else: >> temp_restore.py
    echo         exit(1) >> temp_restore.py

    REM Copy files to container and run restore
    docker cp temp_restore.py grokputer-mcp:/app/restore_auto.py
    docker cp vault/redis_backup.json grokputer-mcp:/app/vault/

    docker exec grokputer-mcp python3 restore_auto.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to import Redis keys
        exit /b 1
    )
    echo [SUCCESS] Redis keys imported successfully

    REM Cleanup
    del temp_restore.py
) else (
    echo [WARNING] No Redis backup found at vault\redis_backup.json - skipping import
)

REM Verify setup
echo [INFO] Verifying setup...

REM Check if container is running
docker ps | findstr grokputer-mcp >nul
if %errorlevel% neq 0 (
    echo [ERROR] Container is not running
    exit /b 1
)

REM Check Redis connection
docker exec grokputer-mcp redis-cli ping | findstr PONG >nul
if %errorlevel% neq 0 (
    echo [ERROR] Redis is not responding
    exit /b 1
)
echo [SUCCESS] Redis is responding

REM Check Redis key count
for /f %%i in ('docker exec grokputer-mcp redis-cli dbsize') do set KEY_COUNT=%%i
if %KEY_COUNT% gtr 0 (
    echo [SUCCESS] Redis has %KEY_COUNT% keys loaded
) else (
    echo [WARNING] Redis has no keys loaded
)

REM Show completion info
echo.
echo [SUCCESS] Setup complete! 🎉
echo.
echo Services running:
echo   • MCP Server: http://localhost:8000
echo   • Redis: localhost:6379
echo.
echo Container name: grokputer-mcp
echo.
echo To stop: docker stop grokputer-mcp
echo To restart: docker start grokputer-mcp
echo To view logs: docker logs grokputer-mcp
echo To shell: docker exec -it grokputer-mcp sh
echo.
echo Don't forget to add your API keys to .env file!
echo.
pause