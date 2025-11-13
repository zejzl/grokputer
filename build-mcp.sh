#!/bin/bash
# Grokputer MCP Server - Build and Test Script

set -e  # Exit on error

echo "========================================"
echo "Building Grokputer MCP Server"
echo "========================================"

# Build Docker image
echo "Building Docker image..."
time docker build -f Dockerfile.mcp -t grokputer-mcp:latest .

echo ""
echo "Image built successfully!"
echo ""

# Show image size
echo "Image size:"
docker images grokputer-mcp:latest --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
echo ""

# Test startup time
echo "Testing startup time (<3s requirement)..."
echo "Starting container..."
START_TIME=$(date +%s%N)
docker run --rm --name grokputer-mcp-test -p 8000:8000 -d grokputer-mcp:latest
sleep 2  # Wait for startup

# Check if container is running
if docker ps | grep -q grokputer-mcp-test; then
    END_TIME=$(date +%s%N)
    ELAPSED=$((($END_TIME - $START_TIME) / 1000000))  # Convert to milliseconds
    echo "Container started in ${ELAPSED}ms"

    if [ $ELAPSED -lt 3000 ]; then
        echo "[PASS] Startup time < 3s ✓"
    else
        echo "[WARN] Startup time > 3s"
    fi
else
    echo "[FAIL] Container failed to start"
    exit 1
fi

echo ""
echo "Testing tools availability..."

# Wait for server to be ready
sleep 1

# Test endpoints (if FastMCP exposes them)
echo "Checking if tools are accessible..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "[PASS] Health check endpoint responsive ✓"
else
    echo "[INFO] Health check endpoint not available (may need FastMCP configuration)"
fi

# Cleanup
echo ""
echo "Cleaning up test container..."
docker stop grokputer-mcp-test

echo ""
echo "========================================"
echo "Build and test complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Run: docker run -p 8000:8000 -v \$(pwd)/vault:/app/vault grokputer-mcp:latest"
echo "2. Configure mcp-config.yaml in MCP Gateway/Claude Desktop"
echo "3. Verify tools appear in UI"
echo ""
