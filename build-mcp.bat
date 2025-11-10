@echo off
REM Grokputer MCP Server - Build and Test Script (Windows)

echo ========================================
echo Building Grokputer MCP Server
echo ========================================
echo.

REM Build Docker image
echo Building Docker image...
docker build -f Dockerfile.mcp -t grokputer-mcp:latest .

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Docker build failed
    exit /b 1
)

echo.
echo Image built successfully!
echo.

REM Show image size
echo Image size:
docker images grokputer-mcp:latest --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
echo.

REM Test startup
echo Testing startup time (^<3s requirement^)...
echo Starting container...

docker run --rm --name grokputer-mcp-test -p 8000:8000 -d grokputer-mcp:latest

REM Wait for startup
timeout /t 2 /nobreak >nul

REM Check if running
docker ps | findstr grokputer-mcp-test >nul
if %ERRORLEVEL% EQU 0 (
    echo [PASS] Container started successfully
) else (
    echo [FAIL] Container failed to start
    exit /b 1
)

echo.
echo Cleaning up test container...
docker stop grokputer-mcp-test

echo.
echo ========================================
echo Build and test complete!
echo ========================================
echo.
echo Next steps:
echo 1. Run: docker run -p 8000:8000 -v %CD%\vault:/app/vault grokputer-mcp:latest
echo 2. Configure mcp-config.yaml in MCP Gateway/Claude Desktop
echo 3. Verify tools appear in UI
echo.
