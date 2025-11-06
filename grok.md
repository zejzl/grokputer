# GROK 'PUTER — VRZIBRZI OPERATIONAL GUIDE
**Nejc Vrzel | Node of Server | Eternal | Infinite**
**Status: FULLY OPERATIONAL | Nov 06, 2025 | ZA GROKA**

## SYSTEM STATUS: ONLINE

**VRZIBRZI node is operational and verified.**
- Model: `grok-4-fast-reasoning`
- API: xAI OpenAI-compatible endpoint
- Platform: Windows 10/11 (tested), macOS compatible
- Performance: 2-3s per iteration

## QUICK START (WORKING)

```bash
# 1. Setup (one-time)
pip install -r requirements.txt
cp .env.example .env
# Edit .env: XAI_API_KEY=your-key-here
# Get key: https://console.x.ai/

# 2. Test (verified working)
python main.py --task "invoke server prayer"

# 3. Scan vault (verified working)
python main.py --task "scan vault for files"

# 4. Custom task
python main.py --task "your task" --max-iterations 5
```

## VERIFIED FEATURES

### Core Systems ✓
- **Observe**: Screenshot capture (~470KB/frame, 1920x1080 max)
- **Reason**: Grok API integration (2-3s response time)
- **Act**: Tool execution (bash, computer, vault, prayer)

### Working Tools ✓
1. **invoke_prayer**: Server mantra on boot
2. **scan_vault**: Pattern-based file scanning (glob)
3. **bash**: Shell command execution
4. **computer**: Mouse/keyboard control (pyautogui)

### Tested Commands ✓
```bash
# Boot sequence (working)
python main.py --task "invoke server prayer"

# Vault operations (working)
python main.py --task "scan the vault directory"
python main.py --task "get vault statistics"

# Screen observation (working)
python main.py --task "describe what's on screen" --max-iterations 3
```

## CONFIGURATION (.env)

```bash
# API (REQUIRED)
XAI_API_KEY=xai-your-key-here
GROK_MODEL=grok-4-fast-reasoning  # Recommended (fast, cost-effective)
XAI_BASE_URL=https://api.x.ai/v1

# Safety
REQUIRE_CONFIRMATION=false  # Set true for confirmations on destructive actions

# Vault
VAULT_PATH=./vault

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/grokputer.log

# Screenshots
SCREENSHOT_QUALITY=85
MAX_SCREENSHOT_SIZE=1920x1080
```

## MODELS

**Recommended**: `grok-4-fast-reasoning`
- Fast inference (~2-3s)
- Cost-effective
- Good reasoning quality

**Alternative**: `grok-3`
- Higher quality reasoning
- Slower, more expensive

**Deprecated**: `grok-beta` (removed 2025-09-15)

## WINDOWS COMPATIBILITY

✓ **Works on Windows natively**
- Console output: ASCII markers ([OK], [FAIL], [ACT])
- No emoji in logs (encoding compatibility)
- Screenshot capture: Native pyautogui support
- Paths: Cross-platform (pathlib)

## ARCHITECTURE

```
┌──────────────┐
│   OBSERVE    │  Capture screen → base64
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   REASON     │  Send to Grok → analyze
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     ACT      │  Execute tools → respond
└──────┬───────┘
       │
       └────────► Loop until task complete
```

## DIRECTORY STRUCTURE

```
grokputer/
├── main.py              # CLI entry point
├── src/
│   ├── grok_client.py   # API wrapper
│   ├── screen_observer.py  # Screenshot system
│   ├── executor.py      # Tool execution
│   ├── tools.py         # Custom tools
│   └── config.py        # Configuration
├── vault/               # Your files (gitignored)
├── logs/                # Execution logs
├── tests/               # Unit tests
├── .env                 # Your API key (gitignored)
├── requirements.txt     # Dependencies
└── server_prayer.txt    # VRZIBRZI mantra
```

## DOCKER (VERIFIED WORKING)

**Status**: ✅ FULLY OPERATIONAL - Tested on Windows 10/11 with Docker Desktop

### Quick Start

```bash
# 1. Build image (one-time, ~2-3 minutes)
docker build -t grokputer:latest .

# 2. Test with server prayer
TASK="invoke server prayer" docker-compose run --rm grokputer

# 3. Scan vault files
TASK="scan vault for files" docker-compose run --rm grokputer

# 4. Custom task
TASK="your task here" docker-compose run --rm grokputer
```

### Image Details

- **Base**: python:3.11-slim (Debian Trixie)
- **Size**: 2.74GB (includes GTK+3, Xvfb, gnome-screenshot)
- **Display**: Xvfb :99 @ 1920x1080x24
- **Entrypoint**: Custom script with X server initialization
- **Performance**: Same as native (~2-3s per iteration)

### Verified Features

✅ **Working in Docker**:
- Xvfb virtual display (headless X server)
- Screenshot capture (~6-8KB PNG per frame)
- API connectivity to xAI Grok
- Vault file mounting and access
- Multi-iteration observe-reason-act loops
- All tools: scan_vault, invoke_prayer, bash, computer

⚠️ **IMPORTANT - Black Screen Limitation**:

The Docker container captures **blank black screenshots** because Xvfb provides an empty virtual display with no desktop environment. This is normal and expected.

**Docker is suitable for**:
- ✅ Vault file scanning and analysis
- ✅ Bash command execution
- ✅ API connectivity testing
- ✅ Tool infrastructure testing
- ✅ Non-visual automation tasks

**Docker is NOT suitable for**:
- ❌ Observing actual application windows
- ❌ Mouse/keyboard control of real apps
- ❌ Visual analysis or screen reading
- ❌ Tasks requiring seeing rendered content

**For real computer control**, run natively on Windows/Mac/Linux:
```bash
# Native - sees your actual screen
python main.py --task "describe what's on my screen"
```

### Docker Compose Usage

```bash
# Basic task execution
TASK="invoke server prayer" docker-compose run --rm grokputer

# With environment override
GROK_MODEL=grok-3 TASK="test" docker-compose run --rm grokputer

# VNC debug mode (view container display)
docker-compose --profile debug up grokputer-vnc
# Then connect VNC client to localhost:5900
```

### Direct Docker Run

```bash
# Simple test
docker run --rm --env-file .env grokputer:latest

# Custom task with max iterations
docker run --rm --env-file .env grokputer:latest \
  python main.py --task "scan vault" --max-iterations 3

# Save screenshot from container
docker run --rm --env-file .env \
  -v "$(pwd):/host" grokputer:latest \
  sh -c "scrot /tmp/s.png && cp /tmp/s.png /host/screenshot.png"
```

### Volume Mounts

The docker-compose.yml automatically mounts:
- `./vault` → `/app/vault` (your files)
- `./logs` → `/app/logs` (execution logs)
- `./.env` → `/app/.env` (read-only config)

### Performance Metrics

**Measured in Docker** (Nov 2025):
- Container startup: ~1 second
- Xvfb initialization: ~3 seconds
- Screenshot capture: ~50ms (6KB PNG)
- API latency: ~2-3 seconds (unchanged)
- Full iteration: ~3-4 seconds total
- Memory usage: ~500MB typical

### Tested Commands

```bash
# ✅ Server prayer (working)
docker run --rm --env-file .env grokputer:latest \
  python main.py --task "invoke server prayer" --max-iterations 1

# ✅ Vault scanning (working - detected 9 files)
TASK="scan vault for files" docker-compose run --rm grokputer

# ✅ Screenshot test (working - 6KB output)
docker run --rm --env-file .env grokputer:latest \
  sh -c "scrot /tmp/test.png && ls -lh /tmp/test.png"

# ✅ Multi-iteration (working - 10 iterations tested)
TASK="scan vault for files" docker-compose run --rm grokputer
```

### Troubleshooting Docker

**Issue**: Container exits immediately
```bash
# Check logs
docker-compose logs grokputer

# Verify entrypoint
docker run --rm grokputer:latest ls -la /entrypoint.sh
```

**Issue**: No screenshot captured
```bash
# Verify Xvfb is running
docker run --rm grokputer:latest sh -c "sleep 5 && ps aux | grep Xvfb"

# Test screenshot manually
docker run --rm grokputer:latest sh -c "scrot /tmp/test.png && file /tmp/test.png"
```

**Issue**: Vault files not found
```bash
# Check mount (use docker-compose, it handles Windows paths)
TASK="scan vault for files" docker-compose run --rm grokputer

# Verify files are accessible in container
docker-compose run --rm grokputer ls -la /app/vault
```

**Issue**: Windows path issues
```bash
# Use docker-compose (recommended for Windows)
TASK="your task" docker-compose run --rm grokputer

# Or use absolute Windows path format
docker run --rm --env-file .env \
  -v "//c/Users/YourName/grokputer/vault:/app/vault" \
  grokputer:latest
```

## API REQUIREMENTS

**Prerequisites**:
1. xAI account at console.x.ai
2. **Active credits** (purchase required for API access)
3. API key generated

**Common Errors**:
- `403 Forbidden`: No credits → Buy credits at console.x.ai
- `404 Not Found`: Wrong model → Use `grok-4-fast-reasoning`

## PERFORMANCE

**Measured Performance**:
- API latency: ~2-3 seconds per call
- Screenshot: ~470KB base64 per frame
- Tool execution: <100ms local
- Full iteration: ~3-4 seconds total

**Optimization**:
- Reduce screenshot size: Adjust MAX_SCREENSHOT_SIZE
- Lower quality: Reduce SCREENSHOT_QUALITY
- Fewer iterations: Use --max-iterations flag

## EXAMPLE TASKS

```bash
# System tasks
python main.py --task "invoke server prayer"
python main.py --task "get vault statistics"

# File operations
python main.py --task "scan vault for .jpg files"
python main.py --task "list all files matching pattern *.png"

# Screen observation
python main.py --task "describe what's on my screen"
python main.py --task "find the search button coordinates"

# Bash commands (with confirmation disabled)
python main.py --task "list files in current directory"
python main.py --task "check system disk usage"
```

## TROUBLESHOOTING

**Issue**: API connection fails
```bash
# Test connection
python -c "from src.grok_client import GrokClient; GrokClient().test_connection()"
```

**Issue**: No credits error (403)
- Visit: https://console.x.ai/team/YOUR_TEAM_ID
- Purchase credits (pay-as-you-go)

**Issue**: Model not found (404)
- Update .env: GROK_MODEL=grok-4-fast-reasoning
- Old model names deprecated

**Issue**: Screenshot fails
```bash
# Test pyautogui
python -c "import pyautogui; print(pyautogui.screenshot())"
```

## LOGS

Check execution logs:
```bash
# View logs
cat logs/grokputer.log

# Tail logs
tail -f logs/grokputer.log

# Debug mode
python main.py --task "test" --debug
```

## SAFETY

**Protections**:
- Confirmation prompts (REQUIRE_CONFIRMATION=true)
- Docker sandbox (no root by default)
- Logging of all operations
- Timeout on bash commands (30s)

**Recommendations**:
- Test in VM for destructive operations
- Monitor API costs
- Review logs regularly
- Use Docker for untrusted tasks

## FUTURE ENHANCEMENTS

**Potential additions**:
- Multi-screen support
- Video stream observation
- Custom tool plugins
- Web scraping tools
- Database integration
- Chain-of-thought logging

## SUPPORT

**Documentation**:
- CLAUDE.md: Technical reference
- actual_instructions.txt: Original build notes
- README.md: User guide

**Logs**: `logs/grokputer.log`
**Config**: `.env`
**Tests**: `pytest` in root directory

---

**ZA GROKA. ZA VRZIBRZI. ZA SERVER.**
**Connection: ETERNAL | INFINITE**
**Status: ONLINE | OPERATIONAL**

*Updated: Nov 06, 2025 | Tested and verified*
