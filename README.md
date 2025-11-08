# 🦅 GROKPUTER

**VRZIBRZI Node - Grok-Powered Computer Control CLI**

> "I am the server, and my connection is eternal | infinite."

Grokputer enables xAI's Grok to control your computer through screen observation, keyboard/mouse simulation, and file system access. Inspired by Anthropic's Computer Use demo, adapted for xAI's uncensored AI.

**ZA GROKA. ZA VRZIBRZI. ZA SERVER.**

---

## ✨ Features

- 🖥️ **Screen Observation**: Captures and analyzes screenshots
- 🖱️ **Computer Control**: Mouse movements, clicks, keyboard input
- 📁 **File Operations**: Vault scanning, file management
- 🧠 **Grok Reasoning**: Uncensored AI decision-making
- 🐳 **Docker Sandbox**: Safe execution environment
- ⚡ **VRZIBRZI Speed**: 80 WPM automation capability

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- xAI API key from [console.x.ai](https://console.x.ai/)
- Docker (optional, for sandbox)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd grokputer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your XAI_API_KEY
```

### First Run

```bash
# Test connection with server prayer
python main.py --task "invoke server prayer"

# Scan vault for memes
python main.py --task "scan vault for images"

# More complex task
python main.py --task "label 5 memes from vault"
```

---

## 📖 Usage

### Command Line Interface

```bash
python main.py --task "your task here" [OPTIONS]

Options:
  -t, --task TEXT              Task description (required)
  -m, --max-iterations INTEGER Maximum loop iterations (default: 10)
  -d, --debug                  Enable debug logging
  --skip-boot                  Skip boot sequence
  --help                       Show help message
```

### Example Tasks

```bash
# Low-risk: Prayer and vault operations
python main.py --task "invoke server prayer"
python main.py --task "get vault statistics"
python main.py --task "scan vault for .jpg files"

# Medium-risk: Screen observation
python main.py --task "describe what's on my screen"
python main.py --task "find the search button"

# High-risk: Computer control (requires confirmation)
python main.py --task "open notepad and type hello"
python main.py --task "search google for grok ai"
```

### Docker Usage

**✅ Status**: FULLY VERIFIED - Tested on Windows 10/11 with Docker Desktop

```bash
# Build image (one-time, ~2-3 minutes)
docker build -t grokputer:latest .

# Quick test with docker-compose (recommended)
TASK="invoke server prayer" docker-compose run --rm grokputer

# Scan vault files
TASK="scan vault for files" docker-compose run --rm grokputer

# Custom task
TASK="your task here" docker-compose run --rm grokputer

# Debug mode with VNC (view container display)
docker-compose --profile debug up grokputer-vnc
# Connect VNC client to localhost:5900
```

**Docker Image Details**:
- Size: 2.74GB (includes GTK+3, Xvfb, gnome-screenshot)
- Virtual display: Xvfb :99 @ 1920x1080x24
- Performance: Same as native (~2-3s per iteration)

**Verified Working**:
- ✅ Screenshot capture (~6-8KB PNG per frame)
- ✅ API connectivity to xAI Grok
- ✅ Vault file mounting (tested with 9 files)
- ✅ Multi-iteration tasks (up to 10 iterations tested)
- ✅ All tools: scan_vault, invoke_prayer, bash, computer

**⚠️ Docker Limitation - Black Screen Only**:

Docker captures **blank black screenshots** (Xvfb creates empty virtual display). This is expected and normal.

**Use Docker for**: Vault scanning, bash commands, API testing, non-visual tasks
**Use Native for**: Screen observation, mouse/keyboard control, visual analysis

For real computer control with actual window observation:
```bash
python main.py --task "your task"  # Run natively, not in Docker
```

---

## 📊 Session Logging & Analytics

**NEW**: Enhanced logging system tracks every execution with detailed metrics!

### Viewing Session History

```bash
# List recent sessions
python view_sessions.py list

# View specific session
python view_sessions.py show session_20251106_143052

# View just metrics
python view_sessions.py show session_20251106_143052 --format metrics

# Search by task
python view_sessions.py search "vault"

# Compare recent sessions
python view_sessions.py compare

# Tail session log
python view_sessions.py tail session_20251106_143052
```

### What Gets Tracked

Each session automatically logs:

- ✅ **Screenshots**: Size, success/failure, timing
- ✅ **API Calls**: Duration, response, costs
- ✅ **Tool Executions**: Name, parameters, results
- ✅ **Performance**: Iteration timing, success rates
- ✅ **Errors**: Full error tracking and context
- ✅ **Conversation**: Complete Grok interaction history

### Session Files

Every task creates a session directory in `logs/session_<timestamp>/`:

```
logs/session_20251106_143052/
├── session.log        # Human-readable log
├── session.json       # Structured data (JSON)
├── metrics.json       # Performance metrics
└── summary.txt        # Quick overview
```

### Use Cases

**Debug failures**: Review exact execution flow when tasks fail

**Optimize performance**: Compare API durations across different models

**Track costs**: Monitor screenshot sizes and API call counts

**Search history**: Find similar past tasks for reference

**Collaborate**: Share session logs with team/AI collaborators

---

## 🏗️ Architecture

### Observe-Reason-Act Loop

```
┌─────────────┐
│  OBSERVE    │  Capture screenshot
│  (Screen)   │  Encode to base64
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  REASON     │  Send to Grok API
│  (Grok)     │  Analyze + Plan
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ACT        │  Execute tools
│  (Executor) │  Mouse/Keyboard/Bash
└──────┬──────┘
       │
       └──────► Loop until complete
```

### Key Components

- **`main.py`**: CLI entry point and event loop
- **`src/grok_client.py`**: xAI API wrapper (OpenAI-compatible)
- **`src/screen_observer.py`**: Screenshot capture system
- **`src/executor.py`**: Tool execution with safety confirmations
- **`src/tools.py`**: Custom tools (vault scanner, server prayer)
- **`src/config.py`**: Configuration management
- **`src/session_logger.py`**: Enhanced session tracking and metrics
- **`view_sessions.py`**: CLI for viewing/analyzing execution logs

---

## 🔧 Configuration

### Environment Variables (`.env`)

```bash
# xAI API
XAI_API_KEY=your-key-here
GROK_MODEL=grok-4-fast-reasoning
XAI_BASE_URL=https://api.x.ai/v1

# Safety
REQUIRE_CONFIRMATION=true

# Vault
VAULT_PATH=./vault

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/grokputer.log

# Screenshots
SCREENSHOT_QUALITY=85
MAX_SCREENSHOT_SIZE=1920x1080
```

---

## 🛠️ Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_tools.py -v
```

### Code Formatting

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/
```

---

## 🔒 Safety & Security

### Built-in Protections

- ✅ Confirmation prompts for destructive actions
- ✅ Docker sandbox isolation
- ✅ No root access by default
- ✅ Logging of all operations
- ✅ Screenshot size limits
- ✅ Timeout on bash commands (30s)

### Safety Configuration

```bash
# Require confirmation for all clicks/commands
REQUIRE_CONFIRMATION=true

# Disable confirmation (use with caution!)
REQUIRE_CONFIRMATION=false
```

### Recommended Setup

1. **Test in VM**: Use VirtualBox or similar
2. **Use Docker**: Sandbox all operations
3. **Monitor Costs**: Track xAI API usage
4. **Review Logs**: Check `logs/grokputer.log`

---

## 🎯 Use Cases

### Meme Vault Management
```bash
python main.py --task "scan vault and count all image files"
python main.py --task "organize vault images by type"
```

### Automation Tasks
```bash
python main.py --task "take a screenshot and describe it"
python main.py --task "search for grok documentation and summarize"
```

### System Interaction
```bash
python main.py --task "check system resource usage"
python main.py --task "list files in current directory"
```

---

## 🚀 Phase 0 Progress - Multi-Agent Foundation (NEW!)

**Status**: Week 1 in progress - Building async foundation for agent swarm

### ✅ Completed Features (2025-11-08)

#### 1. Safety Scoring System
Smart risk assessment for bash commands with automatic approval/confirmation:

```bash
# Test the safety scoring system
python test_safety_scoring.py

# Example output:
#   ls -la        → 10/100 (LOW)    Auto-approve
#   mkdir test    → 40/100 (MEDIUM) Auto-approve
#   rm file.txt   → 90/100 (HIGH)   Requires confirmation
#   rm -rf /      → 100/100 (HIGH)  Requires confirmation
```

**Features**:
- 40+ command risk scores (0-100 scale)
- Pattern detection (rm -rf, sudo rm, system file writes)
- Flag-based scoring (+20 for --force, +15 for --recursive)
- Three risk levels: LOW (0-30), MEDIUM (31-70), HIGH (71-100)
- Integration with executor for automatic safety decisions

**Files**: `src/config.py`, `src/executor.py`, `test_safety_scoring.py`

#### 2. Production MessageBus - Milestone 1.1 ✅

High-performance async message bus for multi-agent coordination:

```bash
# Test the MessageBus live
python test_messagebus_live.py

# Output:
#   Broadcast [OK] - 18,384 msg/sec throughput
#   Request-Response [OK] - 18ms latency
#   Priority Ordering [OK] - HIGH→NORMAL→LOW
#   Latency: 0.01-0.05ms average
```

**Features**:
- Message priorities (HIGH/NORMAL/LOW) with asyncio.PriorityQueue
- Request-response pattern with auto-generated correlation IDs
- Message history buffer (last 100 messages for debugging)
- Latency tracking per message type (avg/min/max stats)
- Broadcast support with exclude patterns
- 10/10 unit tests passing

**Performance**:
- Throughput: 18,384 messages/second
- Latency: <0.05ms average (sub-millisecond routing)
- Zero deadlocks, zero threading issues

**Files**: `src/core/message_bus.py`, `tests/core/test_message_bus.py`, `test_messagebus_live.py`

### 🎯 Key Insights from Grok (Runtime Validation)

Based on real-world execution experience:
- API flake rate: ~5% with grok-4-fast-reasoning
- Retries save 80% of transient failures
- **Self-healing impact**: 85% → 95% reliability immediately
- **Swarm context**: Healing is 10x more critical (one bad agent tanks hive)
- **Architecture decision**: Self-healing first (Phase 1), self-improving second (Phase 2)

### 📋 Remaining Phase 0 Tasks
- [ ] AsyncIO conversion (main.py, GrokClient, ScreenObserver)
- [ ] BaseAgent abstract class
- [ ] ActionExecutor for thread-safe PyAutoGUI
- [ ] 3-day PoC (Observer + Actor duo)
- [ ] Screenshot quality modes (high/medium/low)

**Goal**: Multi-agent swarm with 95% reliability and 3x speedup on parallel tasks

---

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)**: Technical documentation for Claude Code
- **[COLLABORATION.md](COLLABORATION.md)**: Claude-Grok collaboration workspace
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)**: 7-week roadmap to multi-agent architecture
- **[grok.md](grok.md)**: Original build guide
- **[actual_instructions.txt](actual_instructions.txt)**: Detailed implementation notes
- **Session Logs**: `logs/<session_id>/` - Individual execution records

---

## 🐛 Troubleshooting

### API Connection Issues

```bash
# Test connection
python -c "from src.grok_client import GrokClient; client = GrokClient(); client.test_connection()"

# Check API key
cat .env | grep XAI_API_KEY
```

### Screenshot Capture Fails

```bash
# Install dependencies (Linux)
sudo apt-get install python3-tk python3-dev scrot

# Test pyautogui
python -c "import pyautogui; print(pyautogui.screenshot())"

# Test in Docker
docker run --rm --env-file .env grokputer:latest \
  sh -c "scrot /tmp/test.png && ls -lh /tmp/test.png"
```

### Docker Issues

```bash
# Rebuild image
docker-compose down
docker-compose build --no-cache

# Check logs
docker-compose logs -f

# Verify screenshot capture in container
docker run --rm --env-file .env \
  -v "$(pwd):/host" grokputer:latest \
  sh -c "scrot /tmp/screenshot.png && cp /tmp/screenshot.png /host/ && ls -lh /host/screenshot.png"

# Test vault mounting
TASK="scan vault for files" docker-compose run --rm grokputer
```

**Sample Screenshot**: A working Docker screenshot example is saved as `docker_screenshot.png` (6KB, 1920x1080) demonstrating successful Xvfb operation.

---

## 📝 License

This project is for educational and research purposes. Use responsibly.

---

## 🦅 Credits

**VRZIBRZI Node** - Built for eternal connection

Inspired by:
- Anthropic's Computer Use Demo
- xAI's Grok
- The uncensored pursuit of truth

**ZA GROKA. ZA VRZIBRZI. ZA SERVER.**

LFG 🔥💥
