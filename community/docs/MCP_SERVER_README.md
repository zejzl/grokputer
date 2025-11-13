# Grokputer MCP Server

Lightweight Model Context Protocol (MCP) server exposing Grokputer's core tools.

## Features

- **scan_vault**: Scan vault directory for files and return inventory
- **invoke_prayer**: Invoke server prayer ritual from server_prayer.txt
- **get_vault_stats**: Get statistics about vault contents (file counts, sizes, types)

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r mcp-requirements.txt

# Run server directly (uses mcp.run())
python grokputer_server.py

# Or with uvicorn (uses http_app ASGI application)
uvicorn grokputer_server:app --host 0.0.0.0 --port 8000
```

**Note**: FastMCP v2.13.0.2+ exposes `http_app` as the ASGI application. The server exports `app = mcp.http_app` for uvicorn.

### Docker Deployment

```bash
# Build image
docker build -f Dockerfile.mcp -t grokputer-mcp:latest .

# Run container
docker run -p 8000:8000 -v $(pwd)/vault:/app/vault grokputer-mcp:latest

# Test startup time (<3s requirement)
time docker run -p 8000:8000 grokputer-mcp:latest
```

### Testing Server

```bash
# Verify container is running (should show "healthy" status)
docker ps | grep grokputer-mcp

# Check logs for startup confirmation
docker logs grokputer-mcp
# Should see: "Application startup complete" and "Uvicorn running on http://0.0.0.0:8000"

# Test root endpoint (404 is expected - MCP uses protocol-specific paths)
curl http://localhost:8000/
# Response: "Not Found" (this is correct behavior)
```

**Important**: MCP uses the Model Context Protocol, not standard REST endpoints. Tools are accessed via MCP-specific protocol paths that Claude Desktop/MCP Gateway will use. Seeing 404 on root paths is **expected and correct**.

## MCP Gateway / Claude Desktop Integration

1. Copy `mcp-config.yaml` to your MCP Gateway config directory
2. Update the `url` field if deploying remotely
3. Restart MCP Gateway or Claude Desktop
4. Tools should appear in the UI within 3 seconds

### Verification

```bash
# Verify container health status (should show "healthy")
docker ps | grep grokputer-mcp

# Check FastMCP version
docker exec grokputer-mcp python -c "import fastmcp; print(fastmcp.__version__)"
# Expected: 2.13.0.2 or higher

# Verify server is responding (404 is correct - not a REST API)
curl http://localhost:8000/
# Expected: "Not Found" (this indicates ASGI app is working)
```

**Success Indicators**:
- ✅ Container status shows "healthy"
- ✅ Logs show "Application startup complete"
- ✅ Root endpoint returns 404 (MCP protocol, not REST)
- ✅ Startup time < 3 seconds

## Performance Targets

- **Startup time**: <3 seconds (verified with `time docker run ...`)
- **Image size**: <200MB (multi-stage build)
- **Tool visibility**: Tools appear in MCP Gateway/Claude Desktop UI immediately

## Architecture

```
grokputer_server.py          # FastMCP server with @mcp.tool decorators
├── scan_vault()             # Async vault scanning
├── invoke_prayer()          # Prayer invocation
└── get_vault_stats()        # Statistics gathering

Dockerfile.mcp               # Multi-stage build (python:3.11-slim)
mcp-requirements.txt         # Minimal deps (fastmcp, uvicorn, pydantic)
mcp-config.yaml             # MCP Gateway/Claude Desktop config
```

## Development

Based on Grok's collaboration plan (see `docs/collaboration_plan_20251109_125011.md`):

- Lightweight FastMCP decorators
- Async support for I/O operations
- Multi-stage Docker build for optimization
- Namespaced tools under "grokputer" prefix

## Troubleshooting

### "TypeError: 'FastMCP' object is not callable"
**Cause**: Trying to use `mcp` directly as ASGI app
**Solution**: Use `mcp.http_app`. The server exports: `app = mcp.http_app`

### Getting 404 on all endpoints
**Status**: ✅ **This is correct behavior**
**Reason**: MCP uses protocol-specific paths, not REST. 404 on `/` means ASGI app works correctly.

### Container exits immediately
**Check**: `docker logs grokputer-mcp` for errors
**Fix**: Verify FastMCP v2.13.0+ installed

### Startup > 3s
Check Docker build cache, reduce dependencies in mcp-requirements.txt

### Tools not visible in Claude Desktop
Verify mcp-config.yaml URL points to running server, check logs, restart Claude Desktop

### Vault access denied
Mount vault directory: `docker run -p 8000:8000 -v C:\path\to\vault:/app/vault grokputer-mcp:latest`

## Next Steps

- Add authentication (bearer token)
- Implement caching for vault scans
- Add more prayer types
- Metrics/monitoring endpoints
