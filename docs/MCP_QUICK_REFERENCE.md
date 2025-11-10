# Grokputer MCP Server - Quick Reference

## ✅ Server Status

**Container**: grokputer-mcp (running and healthy)
**Port**: 8000
**Startup**: ~2 seconds
**FastMCP**: v2.13.0.2+

## Quick Commands

```bash
# Check status
docker ps | grep grokputer-mcp

# View logs
docker logs grokputer-mcp

# Restart
docker restart grokputer-mcp

# Stop
docker stop grokputer-mcp

# Rebuild after changes
docker build -f Dockerfile.mcp -t grokputer-mcp:latest .
docker run -d -p 8000:8000 --name grokputer-mcp grokputer-mcp:latest
```

## Critical Implementation Details

### ASGI App Exposure (MUST USE)

```python
from fastmcp import FastMCP

mcp = FastMCP("grokputer")

# ✅ CORRECT - Use http_app attribute
app = mcp.http_app

# ❌ WRONG - FastMCP object not callable
app = mcp
```

### Expected Behavior

**Root Endpoint Returns 404**: ✅ **This is correct!**
- MCP uses protocol-specific paths, not REST
- 404 on `/` means ASGI app is working
- Don't expect standard REST API endpoints

**Success Indicators**:
- Container shows "healthy" status
- Logs: "Application startup complete"
- Logs: "Uvicorn running on http://0.0.0.0:8000"
- Root endpoint returns 404 (not 500)

## Tool Definitions

### scan_vault
```python
@mcp.tool()
async def scan_vault(vault_path: str = "vault") -> Dict[str, Any]:
    """Scan vault directory for files and return inventory"""
```

### invoke_prayer
```python
@mcp.tool()
async def invoke_prayer(prayer_type: str = "server_prayer") -> Dict[str, str]:
    """Invoke prayer ritual from server_prayer.txt"""
```

### get_vault_stats
```python
@mcp.tool()
async def get_vault_stats(vault_path: str = "vault") -> Dict[str, Any]:
    """Get statistics about vault contents"""
```

## MCP Configuration

**mcp-config.yaml**:
```yaml
mcpServers:
  grokputer:
    url: http://localhost:8000
    name: "Grokputer MCP Server"
    toolPrefix: "grokputer"
    timeout:
      startup: 3000  # 3s
      request: 10000 # 10s
    tools:
      - scan_vault
      - invoke_prayer
      - get_vault_stats
```

## Troubleshooting

### TypeError: 'FastMCP' object is not callable
**Fix**: Use `app = mcp.http_app` (not `app = mcp`)

### Container exits immediately
**Check**: `docker logs grokputer-mcp`
**Common**: Missing `http_app` attribute

### Getting 500 errors
**Cause**: Wrong ASGI app exposure
**Fix**: Update to `app = mcp.http_app`

### Getting 404 on root
**Status**: ✅ This is correct behavior for MCP protocol

## Next Steps

1. Configure Claude Desktop with mcp-config.yaml
2. Restart Claude Desktop
3. Verify tools appear in UI
4. Test each tool:
   - scan_vault: Check vault file scanning
   - invoke_prayer: Verify prayer text returned
   - get_vault_stats: Confirm stats calculation

## Performance Targets

- ✅ Startup: <3s (achieved ~2s)
- ⚠️ Image size: 331MB (target was <200MB, can optimize)
- ✅ Container health: Passing
- ⏳ Tool visibility: Pending Claude Desktop test

## Files to Know

```
grokputer_server.py     # Main server (app = mcp.http_app)
Dockerfile.mcp          # Multi-stage build
mcp-requirements.txt    # Dependencies
mcp-config.yaml        # Claude Desktop config
MCP_SERVER_README.md   # Full documentation
```

## Important Notes

1. FastMCP v2.13.0+ is required
2. Must use `mcp.http_app` for ASGI
3. 404 responses are expected (MCP protocol)
4. Windows volume mounts need special handling
5. Health check passes but tools need Claude Desktop to verify

---

**Last Updated**: 2025-11-09
**Container Status**: Running and healthy
**Ready For**: Claude Desktop integration testing
