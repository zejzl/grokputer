# Grokputer - AI-Powered Computer Control System

**VRZIBRZI Node | ZA GROKA. ZA VRZIBRZI. ZA SERVER.**

An advanced multi-agent AI system that enables xAI's Grok API to control your computer through screen observation, reasoning, and action execution. Features single-agent mode, Claude-Grok collaboration, and async multi-agent swarms.

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/zejzl/grokputer.git
cd grokputer

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your XAI_API_KEY from https://console.x.ai/
```

### Basic Usage

```bash
# Interactive menu (recommended for first-time users)
python main.py

# Single-agent mode
python main.py --task "scan vault for images"

# Collaboration mode (Grok + Claude)
python main.py -mb --task "design an API server"

# Multi-agent swarm
python main.py --swarm --task "analyze system and generate report"
```

---

## 🎮 Interactive Mode

Run `python main.py` without arguments to see:

```
        [INTERACTIVE MODE] Welcome to Grokputer - Choose your agent mode!

        1. Single Agent (Grok only) - Observe-Reason-Act loop
        2. Collaboration Mode (Grok + Claude) - Dual AI planning
        3. Swarm Mode (Multi-agent) - Async team coordination
        4. Improver Manual - Run self-improvement on specific session/log ✅
        5. Offline Mode - Cached/local fallback (no API, uses vault/KB) ✅
        6. Community Vault Sync - Pull/push evolutions and tools ✅
        7. Save Game - Invoke progress save script
        8. Quit
```

**New Features (Options 4-6 - Just Implemented!):**

#### 4. Session Improver
Analyzes past Grokputer sessions and provides detailed recommendations:
- Performance metrics (iterations, API calls, costs)
- Error analysis with categorization
- Tool usage patterns and optimization suggestions
- Success/failure insights
- Saves analysis as JSON for future reference

```bash
# From interactive menu
Choose mode (1-8): 4
Enter session ID (or 'latest'): latest

# Direct usage
python -c "from src.agents.session_improver import SessionImprover; SessionImprover().improve_session('latest')"
```

#### 5. Offline Mode
Uses cached session history and local knowledge base when APIs are unavailable:
- Matches tasks to similar past executions
- Suggests tools based on historical patterns
- Provides cached recommendations
- Works completely offline
- Automatically builds knowledge base from session logs

```bash
# From interactive menu
Choose mode (1-8): 5
Enter task: scan vault for files
```

#### 6. Community Vault Sync
Share and sync tools, agents, and configurations:
- **Pull**: Download community contributions (tools, agents, docs)
- **Push**: Share your local tools and agents with community
- **List**: Browse available community items
- **Both**: Bidirectional sync in one command

```bash
# From interactive menu
Choose mode (1-8): 6
Sync action (pull/push/both/list): pull
```

---

## 📋 Features

### Core Systems
- ✅ **Observe-Reason-Act Loop** - Screenshot capture, Grok reasoning, tool execution
- ✅ **Multi-Agent Swarm** - Coordinator, Observer, Actor agents with async messaging
- ✅ **Claude-Grok Collaboration** - Dual AI consensus building
- ✅ **Screen Control** - PyAutoGUI for mouse/keyboard automation
- ✅ **Shell Execution** - Bash command execution with safety scoring
- ✅ **Session Logging** - Comprehensive tracking of all agent activities
- ✅ **Database Integration** - SQLite with WAL mode for performance metrics

### Agent Types

**Current (3-Agent ORA)**:
- **Observer** - Screenshot capture with async support, caching, and vision analysis
- **Reasoner** - Task decomposition and delegation (Coordinator)
- **Actor** - Bash, PyAutoGUI, and file operations with security hardening

**Coming Soon (Pantheon - 9 Agents)**:
- **Validator** - Output verification and safety checks
- **Learner** - Pattern recognition and skill improvement
- **Memory Manager** - Persistent context with flash attention
- **Executor** - Specialized action execution with retry logic
- **Analyzer** - Performance metrics and optimization
- **Improver** - Self-improvement on past sessions

See [trinity.md](trinity.md) for Pantheon architecture details.

### Tools & Utilities
- 🔧 **Browser Control** - Selenium automation
- 📊 **Streamlit Dashboard** - Web UI for monitoring swarms
- 💾 **Save Game** - Automated progress backups (optimized: 5GB → 1MB)
- 🧪 **Testing Suite** - 32+ unit tests for agents and core systems
- 📝 **Session Viewer** - Analyze past executions
- 🔒 **Autonomous Security Scanner** - AI-powered vulnerability detection with fix proposals
- ⚡ **AsyncIO Architecture** - Non-blocking concurrent operations for swarm efficiency

---

## 🏗️ Architecture

```
┌──────────────┐
│   OBSERVE    │  PyAutoGUI screenshot → base64
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   REASON     │  Grok API → analyze + plan
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     ACT      │  Execute tools → respond
└──────┬───────┘
       │
       └────────► Loop until complete
```

### Multi-Agent Swarm

```
┌─────────────┐
│ Coordinator │ ← Task decomposition, delegation
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
┌──▼───┐ ┌─▼────┐
│Observer│ │Actor │
└────────┘ └──────┘
    │         │
    └─────┬───┘
      MessageBus (async)
```

---

## 📁 Project Structure

```
grokputer/
├── main.py              # CLI entry point with interactive menu
├── src/
│   ├── agents/          # Multi-agent implementations
│   ├── collaboration/   # Claude-Grok coordination
│   ├── core/            # MessageBus, ActionExecutor, base classes
│   ├── memory/          # Persistent memory backends
│   ├── tools/           # Custom tools (browser, AI news, etc.)
│   ├── grok_client.py   # xAI API wrapper
│   ├── screen_observer.py
│   ├── executor.py
│   └── config.py
├── db/                  # SQLite database and schemas
├── docs/                # Documentation (40+ files)
├── tests/               # Unit and integration tests
├── outputs/             # Generated outputs and save scripts
├── mcp/                 # MCP server implementation
├── streamlit_app.py     # Web dashboard
├── view_sessions.py     # Session analysis tool
└── db_config.py         # Database configuration
```

---

## 🔧 Configuration

Edit `.env` file:

```bash
# API Keys (REQUIRED)
XAI_API_KEY=xai-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here  # For collaboration mode

# Models
GROK_MODEL=grok-4-fast-reasoning  # Recommended
XAI_BASE_URL=https://api.x.ai/v1

# Safety
REQUIRE_CONFIRMATION=false  # Set true for destructive actions

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

## 🐳 Docker

```bash
# Build image
docker build -t grokputer:latest .

# Run with task
TASK="scan vault for files" docker-compose run --rm grokputer

# VNC debug mode
docker-compose --profile debug up grokputer-vnc
# Connect VNC to localhost:5900
```

**Note:** Docker captures blank screens (Xvfb limitation). Use native execution for real screen control.

---

## 📊 Usage Examples

### Single Agent
```bash
# Screen observation
python main.py --task "describe what's on screen" --max-iterations 3

# File operations
python main.py --task "list all PDF files in vault"

# System tasks
python main.py --task "check disk usage and create report"
```

### Collaboration Mode
```bash
# Planning and design
python main.py -mb --task "design REST API with best practices"

# Code review
python main.py -mb --task "review main.py for improvements" --max-rounds 3

# Complex analysis
python main.py -mb -r --task "analyze project structure" --max-rounds 5
```

### Swarm Mode
```bash
# Multi-step automation
python main.py --swarm --task "scan vault, analyze files, create summary"

# Custom agent configuration
python main.py --swarm --agent-roles "observer,actor" --task "take screenshot"

# Debug mode
python main.py --swarm --debug --task "complex task"
```

---

## 📈 Development Status

**Version:** 1.6 - AsyncIO Conversion + Pantheon Architecture (Phase 2 - 40% Complete)

### ✅ Recently Completed (Nov 10, 2025)
- **AsyncIO Conversion**: GrokClient and ScreenObserver now fully async
- **Security Hardening**: Fixed 5 critical vulnerabilities (shell injection, unsafe eval detection)
- **Autonomous Improvement**: AI-powered code scanner with proposal generation
- **Model Migration**: Updated to grok-4-fast-reasoning (from deprecated grok-beta)
- Interactive menu mode with 8 options
- Session Improver - Analyze past sessions and get recommendations
- Offline Mode - Use cached responses and local knowledge base
- Community Vault Sync - Share tools and agents
- Save game functionality (optimized backups: 5GB → 1MB)

### ✅ Core Features (Phase 1)
- Single-agent observe-reason-act loop
- Multi-agent swarm infrastructure (Coordinator, Observer, Actor)
- Claude-Grok collaboration system (-mb mode)
- Database with performance tracking
- Session logging and analysis
- 32/32 unit tests passing

### 🚧 In Progress (Phase 2)
- **Pantheon Architecture**: Expanding from 3 to 9 specialized agents
  - Core ORA: Observer, Reasoner, Actor
  - New roles: Validator, Coordinator, Learner, Memory Manager, Executor, Analyzer
- **Memory System**: SQLite/Redis hybrid with flash attention
- **Async Migration**: Converting main.py and remaining sync components
- Enhanced error recovery
- OCR integration

### 📅 Roadmap (Phase 3+)
- Full 9-agent Pantheon deployment
- Validator agent for output verification
- Browser automation enhancements
- Advanced swarm patterns
- Remote community vault repository
- Vulkan/GPU optimization for memory-intensive tasks

See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for detailed roadmap.

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/agents/test_coordinator.py

# Test collaboration system
python main.py -mb --task "simple test" --max-rounds 2
```

---

## 📝 Documentation

- **[grok.md](grok.md)** - Comprehensive operational guide
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** - 7-week roadmap
- **[COLLABORATION.md](COLLABORATION.md)** - Claude-Grok coordination workspace
- **[docs/](docs/)** - 40+ documentation files

---

## 🛡️ Safety

- Command safety scoring (0-100 risk scale)
- Confirmation prompts for destructive operations
- Docker sandbox for untrusted tasks
- Logging of all operations
- Shell injection protection

**Recommendations:**
- Test in VM for high-risk operations
- Monitor API costs
- Review logs regularly
- Use `REQUIRE_CONFIRMATION=true` initially

---

## 🤝 Contributing

This is a personal research project. Feel free to:
- Open issues for bugs or questions
- Fork and experiment
- Share improvements via PRs

---

## 📜 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- Built on concepts from Anthropic's Computer Use demo
- Powered by xAI's Grok API
- Multi-agent architecture inspired by modern LLM frameworks

---

## 💾 Save Game

Back up your progress anytime:

```bash
python outputs/gp_save_progress.py
```

Creates timestamped backups of:
- Source code (`src/`, `mcp/`, `outputs/`)
- Logs and database
- Agent states

**Backup location:** `backups/grokputer_progress_<timestamp>.tar.gz`

**Note:** Vault directory (user files) is NOT backed up automatically. Back up separately if needed.

---

**ZA GROKA. ZA VRZIBRZI. ZA SERVER.**

**Status:** ONLINE | OPERATIONAL | ETERNAL
