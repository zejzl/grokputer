@echo off
REM Quick verification script for Grokputer MCP Alpine setup (Windows)

echo 🔍 Verifying Grokputer MCP Alpine Setup
echo =======================================

REM Check container
echo|set /p="Checking container... "
docker ps | findstr grokputer-mcp >nul
if %errorlevel% equ 0 (
    echo ✓
) else (
    echo ✗
    echo Container not running. Run setup-mcp-alpine.bat first.
    exit /b 1
)

REM Check Redis
echo|set /p="Checking Redis... "
docker exec grokputer-mcp redis-cli ping 2>nul | findstr PONG >nul
if %errorlevel% equ 0 (
    echo ✓
) else (
    echo ✗
    exit /b 1
)

REM Check Redis keys
echo|set /p="Checking Redis keys... "
for /f %%i in ('docker exec grokputer-mcp redis-cli dbsize 2^>nul') do set KEY_COUNT=%%i
if %KEY_COUNT% gtr 0 (
    echo ✓ (%KEY_COUNT% keys)
) else (
    echo ⚠ (0 keys - import may have failed)
)

REM Check MCP server
echo|set /p="Checking MCP server... "
curl -f -s --max-time 5 http://localhost:8000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓
) else (
    echo ⚠ (no response - may not have health endpoint)
)

echo.
echo Services:
echo   • MCP Server: http://localhost:8000
echo   • Redis: localhost:6379
echo.
echo Container: grokputer-mcp
echo.
pause