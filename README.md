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

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)**: Technical documentation for Claude Code
- **[grok.md](grok.md)**: Original build guide
- **[actual_instructions.txt](actual_instructions.txt)**: Detailed implementation notes

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
