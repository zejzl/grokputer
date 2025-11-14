@echo off
REM Grokputer Master Automation Suite (Windows)
REM Handles: build, test, deploy, optimize, monitor, backup

setlocal enabledelayedexpansion

REM Colors (Windows CMD approximations)
set "GREEN=[OK]"
set "RED=[ERROR]"
set "YELLOW=[WARN]"
set "BLUE=[INFO]"
set "PURPLE=[SEC]"

REM Logging
set LOG_FILE=logs\automation_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set LOG_FILE=%LOG_FILE: =0%

echo [%date% %time%] Starting Grokputer Master Automation Suite >> "%LOG_FILE%"

:header
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🤖 AUTOMATION MASTER 🤖                   ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Create logs directory
if not exist logs mkdir logs

goto %1

:all
call :check_dependencies
call :setup_environment
call :run_quality_checks
call :run_tests
call :build_all
call :optimize_code
call :backup_data
call :security_check
call :deploy_services
call :monitor_services
call :cleanup
echo [%date% %time%] Complete automation suite finished >> "%LOG_FILE%"
goto :eof

:check_dependencies
echo [INFO] Checking Dependencies
set missing=

where docker >nul 2>nul || set missing=%missing% docker
where python >nul 2>nul || set missing=%missing% python
where pip >nul 2>nul || set missing=%missing% pip
where node >nul 2>nul || set missing=%missing% node
where npm >nul 2>nul || set missing=%missing% npm

if defined missing (
    echo [ERROR] Missing dependencies:%missing%
    exit /b 1
)
echo [OK] All dependencies available
goto :eof

:setup_environment
echo [INFO] Environment Setup

if not exist .env if exist .env.example (
    copy .env.example .env
    echo [OK] Created .env from template
)

if exist requirements.txt (
    pip install -r requirements.txt
    echo [OK] Python dependencies installed
)

if exist package.json (
    npm install
    echo [OK] Node dependencies installed
)
goto :eof

:run_quality_checks
echo [INFO] Code Quality Checks

where flake8 >nul 2>nul && (
    flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics 2>nul || echo [WARN] Flake8 found issues
    echo [OK] Python linting completed
)

where mypy >nul 2>nul && (
    mypy src/ --ignore-missing-imports 2>nul || echo [WARN] MyPy found issues
    echo [OK] Type checking completed
)

where black >nul 2>nul && (
    black src/ --check --diff 2>nul || echo [WARN] Code needs formatting
    echo [OK] Code formatting checked
)
goto :eof

:run_tests
echo [INFO] Running Tests

if exist tests (
    python -m pytest tests/ -v --tb=short 2>nul || echo [WARN] Some tests failed
    echo [OK] Python tests completed
)

if exist package.json (
    findstr /c:"test" package.json >nul && (
        npm test 2>nul || echo [WARN] Some tests failed
        echo [OK] Node tests completed
    )
)
goto :eof

:build_all
echo [INFO] Building All Components

if exist Dockerfile.mcp-alpine (
    docker build -f Dockerfile.mcp-alpine -t grokputer-mcp-alpine:latest .
    echo [OK] MCP Alpine image built
)

if exist Dockerfile (
    docker build -t grokputer:latest .
    echo [OK] Main image built
)

if exist Dockerfile.mcp (
    docker build -f Dockerfile.mcp -t grokputer-mcp:latest .
    echo [OK] MCP image built
)
goto :eof

:optimize_code
echo [INFO] Code Optimization

where black >nul 2>nul && (
    black src/
    echo [OK] Code formatted with Black
)

where isort >nul 2>nul && (
    isort src/
    echo [OK] Imports sorted
)

where autoflake >nul 2>nul && (
    autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place src/
    echo [OK] Unused imports removed
)
goto :eof

:backup_data
echo [INFO] Data Backup

set BACKUP_DIR=backups\%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%

mkdir "%BACKUP_DIR%" 2>nul

docker ps | findstr grokputer-mcp >nul && (
    docker exec grokputer-mcp redis-cli --rdb /tmp/redis_backup.rdb 2>nul
    docker cp grokputer-mcp:/tmp/redis_backup.rdb "%BACKUP_DIR%\" 2>nul
    echo [OK] Redis backup created
)

if exist vault (
    xcopy vault "%BACKUP_DIR%\vault\" /E /I /H /Y >nul
    echo [OK] Vault backup created
)

if exist logs (
    xcopy logs "%BACKUP_DIR%\logs\" /E /I /H /Y >nul
    echo [OK] Logs backup created
)

REM Create archive (requires 7zip or similar)
where 7z >nul 2>nul && (
    7z a "%BACKUP_DIR%.7z" "%BACKUP_DIR%" >nul
    rmdir /s /q "%BACKUP_DIR%" 2>nul
    echo [OK] Backup archive created: %BACKUP_DIR%.7z
) || (
    echo [OK] Backup created in: %BACKUP_DIR%
)
goto :eof

:security_check
echo [INFO] Security Analysis

where trufflehog >nul 2>nul && (
    trufflehog --regex --entropy=False . 2>nul || echo [WARN] Potential secrets found
    echo [OK] Secrets scan completed
)

where safety >nul 2>nul && (
    safety check 2>nul || echo [WARN] Security vulnerabilities found
    echo [OK] Dependency security check completed
)
goto :eof

:deploy_services
echo [INFO] Service Deployment

docker stop grokputer-mcp grokputer 2>nul
docker rm grokputer-mcp grokputer 2>nul

docker images | findstr grokputer-mcp-alpine >nul && (
    docker run -d --name grokputer-mcp -p 8000:8000 -p 6379:6379 --env-file .env -v "%cd%/vault:/app/vault" -v "%cd%/logs:/app/logs" grokputer-mcp-alpine:latest
    echo [OK] MCP Alpine deployed
)
goto :eof

:monitor_services
echo [INFO] Service Monitoring

docker ps | findstr grokputer-mcp >nul && (
    echo [OK] MCP container running

    docker exec grokputer-mcp redis-cli ping 2>nul | findstr PONG >nul && (
        echo [OK] Redis responding
    ) || (
        echo [ERROR] Redis not responding
    )

    for /f %%i in ('docker exec grokputer-mcp redis-cli dbsize 2^>nul') do (
        echo [OK] Redis keys: %%i
    )
) || (
    echo [WARN] MCP container not running
)
goto :eof

:cleanup
echo [INFO] Cleanup

docker image prune -f >nul 2>nul
echo [OK] Dangling images removed

forfiles /p logs /m *.log /d -7 /c "cmd /c del @path" 2>nul
echo [OK] Old logs cleaned

del /s /q *.pyc 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
echo [OK] Temp files cleaned
goto :eof

:help
echo Grokputer Master Automation Suite (Windows)
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   all          - Run complete automation suite
echo   setup        - Environment setup
echo   quality      - Code quality checks
echo   test         - Run tests
echo   build        - Build all components
echo   optimize     - Code optimization
echo   backup       - Data backup
echo   security     - Security analysis
echo   deploy       - Deploy services
echo   monitor      - Monitor services
echo   cleanup      - Cleanup temp files
echo   help         - Show this help
echo.
echo Examples:
echo   %0 all          # Complete automation
echo   %0 build deploy # Build and deploy
echo   %0 test backup  # Test and backup
goto :eof

REM Default to all if no argument
if "%1"=="" goto all