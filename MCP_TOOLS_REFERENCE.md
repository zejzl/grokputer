# Grokputer MCP Server - Tools Reference

Complete reference for all available tools in the Grokputer MCP server.

## Tool Categories

- **Vault Operations**: File scanning and management
- **Computer Control**: System interaction and screen capture
- **Session Management**: Execution logs and history
- **AI Integration**: Local Qwen Coder integration (experimental)

---

## Vault Operations

### scan_vault
Scan vault directory for files and return inventory.

**Parameters**:
- `vault_path` (string, optional): Path to vault directory (default: "vault")

**Returns**:
```json
{
  "success": true,
  "vault_path": "vault",
  "total_files": 50,
  "files": [
    {"path": "file.pdf", "size": 1024, "modified": 1699999999}
  ]
}
```

**Use Cases**:
- Discover vault contents
- Get file metadata for processing
- Track vault changes over time

---

### invoke_prayer
Invoke server prayer ritual from server_prayer.txt.

**Parameters**:
- `prayer_type` (string, optional): Type of prayer (default: "server_prayer")

**Returns**:
```json
{
  "success": true,
  "prayer_type": "server_prayer",
  "prayer": "I am the server...",
  "message": "Prayer invoked successfully. VRZIBRZI node eternal."
}
```

**Use Cases**:
- Initialize VRZIBRZI node state
- Server boot rituals
- Connection affirmations

---

### get_vault_stats
Get statistics about vault contents.

**Parameters**:
- `vault_path` (string, optional): Path to vault directory (default: "vault")

**Returns**:
```json
{
  "success": true,
  "vault_path": "vault",
  "stats": {
    "total_files": 150,
    "total_size": 1048576,
    "by_extension": {
      ".pdf": {"count": 50, "total_size": 512000},
      ".jpg": {"count": 100, "total_size": 536576}
    }
  }
}
```

**Use Cases**:
- Analyze vault composition
- Track storage usage
- File type distribution analysis

---

## Computer Control

### execute_bash_safe
Execute bash commands with safety scoring (0-100 risk scale).

**Parameters**:
- `command` (string, required): Bash command to execute
- `require_confirm` (boolean, optional): Force confirmation (default: false)

**Returns**:
```json
{
  "success": true,
  "command": "ls -la",
  "stdout": "total 64\ndrwxr-xr-x ...",
  "stderr": "",
  "exit_code": 0,
  "safety_score": 10,
  "safety_level": "low"
}
```

**Safety Scoring**:
- **0-30**: Low risk - Auto-approve (ls, pwd, cat, echo)
- **31-70**: Medium risk - Warn but proceed
- **71-100**: High risk - Require manual confirmation (rm, shutdown, format)

**Risk Factors**:
- Destructive keywords: `rm`, `del`, `format`, `shutdown`, `reboot`
- Output redirection: `>`
- Command length: >100 characters adds +10 points

**Use Cases**:
- Safe system inspection
- File operations with safety checks
- Automated maintenance tasks

**Security Notes**:
- ⚠️ Commands with safety_score > 70 require manual execution
- ✓ 30-second timeout prevents hanging
- ✓ Captures both stdout and stderr

---

### capture_screenshot_region
Capture specific screen region as base64-encoded PNG.

**Parameters**:
- `left` (int, required): Left coordinate (pixels)
- `top` (int, required): Top coordinate (pixels)
- `width` (int, required): Width of region (pixels)
- `height` (int, required): Height of region (pixels)

**Returns**:
```json
{
  "success": true,
  "base64_image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "region": {"left": 100, "top": 100, "width": 200, "height": 200},
  "size_bytes": 8192,
  "format": "PNG"
}
```

**Use Cases**:
- Targeted UI element capture
- OCR on specific regions
- UI testing and validation
- Focused screenshot analysis

**Requirements**:
- Requires `pyautogui` and `pillow` packages
- Native execution only (Docker captures empty display)

---

### get_screen_info
Get display dimensions and center coordinates.

**Parameters**: None

**Returns**:
```json
{
  "success": true,
  "width": 1920,
  "height": 1080,
  "center_x": 960,
  "center_y": 540
}
```

**Use Cases**:
- Calculate click coordinates
- Adjust UI element positions
- Display-aware automation
- Multi-monitor detection

---

## Session Management

### list_recent_sessions
List recent Grokputer execution sessions.

**Parameters**:
- `limit` (int, optional): Maximum sessions to return (default: 10)

**Returns**:
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "session_20251109_123456",
      "task": "scan vault for files",
      "timestamp": "2025-11-09T12:34:56",
      "status": "completed"
    }
  ],
  "total": 5
}
```

**Use Cases**:
- Debug recent failures
- Track execution history
- Monitor task patterns
- Performance analysis

---

### get_session_details
Get detailed information about a specific session.

**Parameters**:
- `session_id` (string, required): Session ID to retrieve

**Returns**:
```json
{
  "success": true,
  "session_id": "session_20251109_123456",
  "data": {
    "task": "scan vault",
    "iterations": 3,
    "tools_used": ["scan_vault", "get_vault_stats"],
    "api_calls": 3,
    "duration": 12.5,
    "errors": [],
    "metrics": {...}
  }
}
```

**Use Cases**:
- Deep dive debugging
- Performance profiling
- API usage tracking
- Error analysis

**Session Data Includes**:
- Task description
- Iteration count
- Tool execution history
- API call metrics
- Error traces
- Conversation history

---

## AI Integration (Experimental)

### ask_qwen
Query local Qwen Coder model for code assistance.

**Parameters**:
- `question` (string, required): Question to ask Qwen
- `context_files` (array, optional): File paths for context

**Returns**:
```json
{
  "success": false,
  "error": "Qwen model not downloaded",
  "message": "Download model: huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF..."
}
```

**Status**: Placeholder - Full integration pending

**Setup Requirements**:
1. Install llama-cpp-python:
   ```bash
   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu118
   ```

2. Download Qwen model (~4GB):
   ```bash
   huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
     qwen2.5-coder-7b-instruct-q4_k_m.gguf \
     --local-dir ./models
   ```

3. Test with `run_qwen.py` directly

**Future Use Cases**:
- Code analysis without API costs
- Local code suggestions
- File-aware assistance
- Privacy-preserving AI

**Note**: Currently returns placeholder response. Use `run_qwen.py` directly until MCP integration is complete.

---

## Usage Examples

### Claude Desktop Integration

1. Configure `mcp-config.yaml`:
```yaml
mcpServers:
  grokputer:
    url: http://localhost:8000
    tools:
      - scan_vault
      - execute_bash_safe
      - capture_screenshot_region
      - list_recent_sessions
```

2. Restart Claude Desktop

3. Use tools in conversation:
```
User: Scan my vault and show me the latest files
Claude: [Uses scan_vault tool]

User: Get info about my screen
Claude: [Uses get_screen_info tool]

User: Run 'df -h' safely
Claude: [Uses execute_bash_safe tool]
```

### Direct API Usage (Testing)

Tools are exposed via FastMCP protocol. For testing:

```bash
# Start server
docker run -p 8000:8000 grokputer-mcp:latest

# Server will respond to MCP protocol requests
# Use Claude Desktop or MCP Gateway to interact
```

---

## Tool Availability Matrix

| Tool | Native | Docker | Safety | Notes |
|------|--------|--------|--------|-------|
| scan_vault | ✅ | ✅ | Safe | Read-only |
| invoke_prayer | ✅ | ✅ | Safe | Read-only |
| get_vault_stats | ✅ | ✅ | Safe | Read-only |
| execute_bash_safe | ✅ | ✅ | Scored | Risk-aware |
| capture_screenshot_region | ✅ | ⚠️ | Safe | Docker=blank |
| get_screen_info | ✅ | ⚠️ | Safe | Docker=virtual |
| list_recent_sessions | ✅ | ✅ | Safe | Read-only |
| get_session_details | ✅ | ✅ | Safe | Read-only |
| ask_qwen | ⏳ | ⏳ | Safe | Placeholder |

**Legend**:
- ✅ Fully functional
- ⚠️ Limited functionality
- ⏳ Coming soon

---

## Performance Characteristics

| Tool | Latency | Payload Size | Notes |
|------|---------|--------------|-------|
| scan_vault | <100ms | ~1-5KB | Limited to 50 files |
| invoke_prayer | <50ms | ~500B | Cached after first read |
| get_vault_stats | <200ms | ~1KB | Recursive scan |
| execute_bash_safe | Variable | Variable | 30s timeout |
| capture_screenshot_region | ~100ms | 5-50KB | Depends on region size |
| get_screen_info | <10ms | <100B | Instant |
| list_recent_sessions | <100ms | ~1-10KB | Depends on limit |
| get_session_details | <100ms | 10-100KB | Full session data |

---

## Security Considerations

### execute_bash_safe
- **Risk Scoring**: Automated safety assessment
- **Timeout**: 30-second maximum
- **High-Risk**: Returns error for manual execution
- **Logging**: All commands logged

### Screen Capture
- **Read-Only**: No system modification
- **Privacy**: Consider sensitive data in screenshots
- **Docker**: Empty display (intentional limitation)

### Session Access
- **Read-Only**: Logs are immutable
- **Privacy**: Session data may contain sensitive info
- **Access**: Local filesystem only

### Qwen Integration
- **Local**: No external API calls
- **Privacy**: Data stays on machine
- **Resources**: Requires ~8GB RAM for 7B model

---

## Troubleshooting

### pyautogui not installed
**Error**: "pyautogui not installed"
**Solution**: `pip install pyautogui pillow`

### Qwen model not found
**Error**: "Qwen model not downloaded"
**Solution**: Follow setup instructions in `ask_qwen` documentation

### High safety score preventing bash execution
**Error**: "Command requires manual confirmation"
**Solution**: Execute manually if trusted, or split into safer commands

### Empty screenshot in Docker
**Expected**: Docker captures virtual display (blank)
**Solution**: Run natively for real screen capture

---

## Development Notes

**Total Tools**: 9 (3 vault + 3 computer control + 2 session + 1 AI)
**Lines of Code**: ~300 (tool implementations)
**Dependencies**: fastmcp, uvicorn, pydantic, aiofiles, pyautogui, pillow
**Startup Time**: <3s (maintains requirement)

**Recent Changes**:
- 2025-11-09: Added 6 new tools (computer control, sessions, Qwen)
- Safety scoring implementation
- Async file operations for sessions
- Conditional imports for optional dependencies

---

## Future Enhancements

- [ ] Full Qwen integration (async wrapper)
- [ ] Mouse control tools (click, drag, move)
- [ ] Keyboard control tools (type, press)
- [ ] Multi-monitor support
- [ ] Session search/filtering
- [ ] Vault content search
- [ ] OCR integration with Qwen-VL
- [ ] Authentication for execute_bash_safe

---

**Last Updated**: 2025-11-09
**Version**: 2.0.0 (Expanded Tools)
**Server Status**: Running and healthy
