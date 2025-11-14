#!/bin/bash
# Quick verification script for Grokputer MCP Alpine setup

echo "🔍 Verifying Grokputer MCP Alpine Setup"
echo "======================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local command=$2
    local expected=$3

    echo -n "Checking $name... "
    if eval "$command" 2>/dev/null | grep -q "$expected"; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Check container
check_service "Container running" "docker ps" "grokputer-mcp" || exit 1

# Check Redis
check_service "Redis ping" "docker exec grokputer-mcp redis-cli ping" "PONG" || exit 1

# Check Redis keys
KEYS=$(docker exec grokputer-mcp redis-cli dbsize 2>/dev/null)
echo -n "Checking Redis keys... "
if [ "$KEYS" -gt 0 ]; then
    echo -e "${GREEN}✓ ($KEYS keys)${NC}"
else
    echo -e "${YELLOW}⚠ (0 keys - import may have failed)${NC}"
fi

# Check MCP server (basic connectivity)
echo -n "Checking MCP server... "
if curl -f -s --max-time 5 http://localhost:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ (no response - may not have health endpoint)${NC}"
fi

echo ""
echo "Services:"
echo "  • MCP Server: http://localhost:8000"
echo "  • Redis: localhost:6379"
echo ""
echo "Container: grokputer-mcp"