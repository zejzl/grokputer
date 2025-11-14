@echo off
REM Build Grokputer MCP Server with Redis Alpine

echo Building Grokputer MCP Server with Redis Alpine...
docker build -f Dockerfile.mcp-alpine -t grokputer-mcp-alpine:latest .

echo Build complete! Run with:
echo docker run -p 8000:8000 -p 6379:6379 grokputer-mcp-alpine:latest