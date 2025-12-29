# Grokputer - AI-Powered Computer Control System

**VRZIBRZI Node | ZA GROKA. ZA VRZIBRZI. ZA SERVER.**

An advanced multi-agent AI system that enables xAI's Grok API to control your computer through screen observation, reasoning, and action execution. Features single-agent mode, Claude-Grok collaboration, and async multi-agent swarms.


![action_screenshot](https://github.com/zejzl/grokputer/blob/main/infinitiyandbyeond.PNG)

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

**Full Pantheon (9 Agents - ALL IMPLEMENTED ✅)**:
- **Validator** - Output verification and safety checks with perceptual hashing
- **Learner** - Pattern recognition and skill improvement from execution history
- **Memory Manager** - Persistent context with Redis/Pinecone integration
- **Executor** - Specialized action execution with circuit breakers and retry logic
- **Analyzer** - Real-time performance metrics, health monitoring, and bottleneck detection
- **Improver** - Self-optimization and continuous improvement with auto-apply

**Enhanced Workflow**:
```
┌─────────────┐
│  Learner    │ ← Check for learned optimizations
└──────┬──────┘
       ↓
┌──────────────┐
│  Reasoner    │ ← Decompose task
└──────┬───────┘
       ↓
┌──────────────┐
│  Observer    │ ← Capture initial state
└──────┬───────┘
       ↓
┌──────────────┐
│  Validator   │ ← Safety validation
└──────┬───────┘
       ↓
┌──────────────┐
│  Executor    │ ← Execute with retry/circuit breaker
└──────┬───────┘
       ↓
┌──────────────┐
│  Observer    │ ← Post-execution validation
└──────┬───────┘
       ↓
┌──────────────┐
│  Learner     │ ← Record pattern
└──────┬───────┘
       ↓
┌──────────────┐
│  Analyzer    │ ← Log metrics
└──────┬───────┘
       ↓
┌──────────────┐
│  Improver    │ ← Suggest optimizations (every 10 tasks)
└──────────────┘
```

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

### Pantheon Mode (9-Agent Architecture)
```bash
# Execute with enhanced workflow: Observe → Reason → Validate → Act → Verify
python main.py --pantheon --task "execute complex task with safety validation"

# Short flag with debug
python main.py -p --task "scan files and create report" --debug

# All actions are validated before execution, with learning and metrics tracking
```

---

## 📈 Development Status

**Version:** 1.8 - AsyncIO Foundation + ORAM Implementation (Phase 0 Complete, Phase 1 Starting)

### ✅ Recently Completed (Nov 10, 2025)

**Phase 0: AsyncIO Foundation ✅ (100% Complete)**:
- **Full Async Conversion**: GrokClient, ScreenObserver, main.py all fully async
- **BaseAgent Class**: Abstract base for all agent implementations
- **MessageBus**: AsyncIO.Queue-based inter-agent communication
- **ActionExecutor**: Thread-safe PyAutoGUI wrapper with async interface
- **Swarm Infrastructure**: Successfully spawns 3-agent teams (Coordinator, Observer, Actor)
- **Security Audit**: Comprehensive scan completed, API key exposure fixed
- **Implementation Plan**: Detailed 4-week, 97-hour roadmap created

**Planning & Documentation**:
- **next.md**: Summary of three development tracks (ORAM, Combo Mode, Daemon)
- **oram.md**: Full ORAM (Observe-Reason-Act-Memory) 9-agent Pantheon roadmap
- **async.md**: Combo mode execution with parallel agents and analytics
- **daemon.md**: Autonomous daemon for continuous monitoring and AI-driven improvements
- **IMPLEMENTATION_PLAN.md**: Week-by-week breakdown with 21 tasks, effort estimates, and acceptance criteria
- **SECURITY_AUDIT_REPORT.md**: Complete security findings and remediation steps

**Previous Milestones**:
- **Pantheon Architecture (9-Agent System)**: Learner, Analyzer, Executor, Improver agents implemented
- **Security Hardening**: Fixed 5 critical vulnerabilities (shell injection, unsafe eval detection)
- **Autonomous Improvement**: AI-powered code scanner with proposal generation
- **Model Migration**: Updated to grok-4-fast-reasoning (from deprecated grok-beta)
- Interactive menu mode with 8 options
- Session Improver, Offline Mode, Community Vault Sync
- Save game functionality (optimized backups: 5GB → 1MB)

### 🚧 In Progress (Phase 1 - Week 1)
**Goal**: Working 3-Agent ORA Loop (22 hours, 2-3 days)
- **Observer Agent Enhancement**: Real screen capture logic with async screenshot handling
- **Actor Agent Enhancement**: ActionExecutor integration with bash/PyAutoGUI actions
- **Coordinator Enhancement**: Task decomposition and intelligent routing
- **Integration Testing**: End-to-end tests for 3-agent workflows
- **Error Recovery**: Retry logic and graceful degradation

### 📅 Roadmap

**Phase 1 - Week 1** (Current): Working 3-Agent ORA Loop
- Enhance Observer, Actor, Coordinator with real implementations
- Integration testing and error recovery
- **Deliverable**: Simple tasks work end-to-end (<5s)

**Phase 2 - Week 2**: 6-Agent Swarm + Memory (25 hours)
- Memory Manager (SQLite/Redis persistence)
- Validator Agent (safety checks and consensus)
- Analyzer Agent (OCR, pattern recognition)
- **Deliverable**: Production-ready with memory and safety

**Phase 3 - Week 3**: Full 9-Agent Pantheon (26 hours)
- Learner Agent (self-improvement from experience)
- Executor Agent (complex multi-step workflows)
- Resource Manager (agent optimization and allocation)
- **Deliverable**: Autonomous evolution and optimization

**Phase 4 - Week 4**: Production Hardening (24 hours)
- 80%+ test coverage with comprehensive test suite
- Documentation, deployment guides, and diagrams
- Performance tuning and optimization
- **Deliverable**: Community-ready release

**Total Effort**: 97 hours over 4 weeks (21 tasks)

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed breakdown with dependencies, acceptance criteria, and risk mitigation.

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

### Core Documentation
- **[next.md](next.md)** - **START HERE** - Summary of three development tracks and immediate next steps
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Detailed 4-week plan with 21 tasks, effort estimates, and acceptance criteria
- **[grok.md](grok.md)** - Comprehensive operational guide
- **[COLLABORATION.md](COLLABORATION.md)** - Claude-Grok coordination workspace

### Planning Documents
- **[oram.md](oram.md)** - ORAM (Observe-Reason-Act-Memory) 9-agent Pantheon roadmap
- **[async.md](async.md)** - Combo mode execution with parallel agents and analytics
- **[daemon.md](daemon.md)** - Autonomous daemon for continuous monitoring and AI improvements

### Security & Reports
- **[SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)** - Complete security audit findings and remediation steps
- **[docs/](docs/)** - 40+ additional documentation files

---

## 🛡️ Safety & Security

### Built-in Safety Features
- Command safety scoring (0-100 risk scale)
- Confirmation prompts for destructive operations
- Docker sandbox for untrusted tasks
- Logging of all operations
- Shell injection protection (3-layer defense: sanitize → parse → execute)

### Security Audit (Nov 10, 2025)
**Status**: Security scan completed, issues remediated

A comprehensive security audit was conducted. See **[SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)** for full details.

**Key Findings**:
- ✅ API key exposure fixed (removed from current files)
- ✅ `.gitignore` updated to prevent future leaks
- ✅ Sensitive files un-tracked from git
- ⚠️ **Action Required Before Going Public**: Clean git history with BFG Repo-Cleaner

**If Making Repository Public**:
1. Revoke exposed API key at https://console.x.ai/
2. Generate new API key
3. Clean git history using BFG (see security report)
4. Verify key removal from all commits
5. Test with new key before pushing

**Recommendations**:
- Never commit API keys or secrets to version control
- Use `.env` for sensitive configuration (already in `.gitignore`)
- Test in VM for high-risk operations
- Monitor API costs and usage
- Review logs regularly
- Use `REQUIRE_CONFIRMATION=true` initially
- Run security scans before making repository public

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
