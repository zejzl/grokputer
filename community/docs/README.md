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
- 🤖 **9-Agent Pantheon**: Phase 3.5 complete - Full AI orchestration with safety validation and self-improvement

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

### Pantheon Mode (Phase 3.5 - LATEST)

```bash
# Run with Pantheon mode (9 agents: Observer, Reasoner, Actor, Validator, Learner, Memory, Executor, Analyzer, Improver)
python main.py --pantheon --task "analyze system and generate report"

# View Pantheon statistics
python view_sessions.py show <session_id> --format metrics
```

**Pantheon Features**:
- **9 Specialized Agents**: Full AI orchestration with consensus voting
- **Safety Validation**: All actions validated before execution
- **Self-Improvement**: Continuous learning and optimization
- **Multi-Modal Processing**: Vision, audio, and text analysis
- **Hierarchical Memory**: Three-tier memory system with knowledge graph
- **Performance**: Advanced metrics collection and bottleneck detection
- **Tests**: Core components tested, expanding coverage

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
  -m, --max-iterations INTEGER Maximum loop iterations - single-agent (default: 10)
  -d, --debug                  Enable debug logging
  --skip-boot                  Skip boot sequence
  -mb, --messagebus            Enable collaboration mode (Claude + Grok)
  --max-rounds INTEGER         Maximum collaboration rounds (default: 5)
  --help                       Show help message
```

### Single-Agent Mode (Default)

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

### Collaboration Mode (Claude + Grok)

**NEW**: Enable dual-agent collaboration where Claude and Grok work together to solve tasks!

```bash
# Design and planning tasks
python main.py -mb --task "Design a REST API for a todo app with best practices"

# Code review and analysis
python main.py -mb --task "Review the messagebus system and suggest improvements"

# Implementation planning
python main.py -mb --task "Create implementation plan for MCP dice roller server"

# With custom rounds
python main.py --messagebus --task "Analyze async vs sync programming" --max-rounds 3
```

**How it works**:
1. Both Claude (Anthropic) and Grok (xAI) receive the task
2. They exchange proposals and feedback over multiple rounds
3. Consensus detection analyzes agreement/disagreement patterns
4. Final unified plan saved to `docs/collaboration_plan_<timestamp>.md`

**Requirements**:
- `ANTHROPIC_API_KEY` in `.env` (for Claude)
- `XAI_API_KEY` in `.env` (for Grok)
- Both agents need active API credits

**Features**:
- ✅ Graceful degradation if one agent fails
- ✅ Consensus detection with confidence scoring
- ✅ Parallel API calls for speed
- ✅ Full conversation history preserved
- ✅ Structured markdown output

See `docs/COLLABORATION_SYSTEM.md` for detailed documentation.

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

## 🚀 Phase 3.5 Progress - Multi-Modal Understanding Complete

**Status**: Advanced AI capabilities with semantic understanding and multi-modal processing

### ✅ Completed Features (2025-11-11)

#### 1. Multi-Modal Understanding System
Comprehensive processing of vision, audio, and text modalities:

```bash
# Multi-modal analysis capabilities
python main.py --pantheon --task "analyze image and describe audio context"
```

**Features**:
- **Vision Processor**: OCR integration, object detection, scene classification
- **Audio Processor**: Speech-to-text, feature extraction, voice activity detection
- **Multi-Modal Processor**: Cross-modal correlation and unified analysis
- **Knowledge Graph**: Semantic entity/relationship mapping

#### 2. Hierarchical Memory System
Three-tier memory architecture with intelligent fusion:

**Features**:
- Short-term LRU cache
- Context decay memory
- Long-term Redis persistence
- Knowledge graph integration
- Relevance-weighted retrieval

#### 3. 9-Agent Pantheon Architecture
Full AI orchestration with advanced coordination:

**Agents**:
- Observer, Reasoner, Actor, Validator, Learner, Memory, Executor, Analyzer, Improver
- Safety validation and consensus voting
- Self-improvement and continuous learning
- Performance monitoring and bottleneck detection

**Performance**:
- AsyncIO architecture for concurrent operations
- MessageBus with priority queuing
- Docker containerization with Redis persistence

### 🎯 Current Status
- **Test Coverage**: 3% overall (core modules: 66-83%)
- **API Integration**: Requires XAI_API_KEY for full functionality
- **Documentation**: Updated with current architecture

### 📋 Next Priorities (Phase 3.6)
- [ ] Reinforcement learning for agent optimization
- [ ] Natural language interfaces for human-AI collaboration
- [ ] Expand test coverage to 80%+
- [ ] Performance tuning and scalability enhancements

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
