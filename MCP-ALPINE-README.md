# Grokputer Redis Alpine MCP Setup

## 🚀 Automated Setup

**Windows:**
```cmd
setup-mcp-alpine.bat
```

**Linux/Mac:**
```bash
chmod +x setup-mcp-alpine.sh
./setup-mcp-alpine.sh
```

## 📋 What It Does

1. **Prerequisites Check** - Verifies Docker & Python installation
2. **Environment Setup** - Creates `.env` from `.env.example`
3. **Docker Build** - Builds Alpine-based MCP image with Redis
4. **Container Launch** - Starts services on ports 8000 (MCP) & 6379 (Redis)
5. **Redis Import** - Restores 138+ keys from `vault/redis_backup.json`
6. **Verification** - Confirms all services are running

## 🔑 Required Setup

**Edit `.env` with your API keys:**
```bash
XAI_API_KEY=your_actual_xai_key_here
# Optional fallbacks:
ANTHROPIC_API_KEY=sk-ant-your_claude_key
GEMINI_API_KEY=your_gemini_key
```

## 🎯 Services

- **MCP Server**: http://localhost:8000
- **Redis**: localhost:6379
- **Container**: `grokputer-mcp`

## 🛠️ Management Commands

```bash
# Stop container
docker stop grokputer-mcp

# Start container
docker start grokputer-mcp

# View logs
docker logs grokputer-mcp

# Shell access
docker exec -it grokputer-mcp sh

# Remove container
docker rm grokputer-mcp
```

## 📊 Redis Data

**Imported keys include:**
- Episode data (100+ cognitive task results)
- Agent counters (`counter:analyzer`, `counter:coordinator`, etc.)
- Performance summaries (`consolidated:*`)
- Agent episode collections

## 🔍 Verification

After setup, verify with:
```bash
# Check container status
docker ps | grep grokputer-mcp

# Test Redis
docker exec grokputer-mcp redis-cli ping

# Check key count
docker exec grokputer-mcp redis-cli dbsize

# Test MCP server
curl http://localhost:8000
```