# Grokputer - AI-Powered Computer Control System

**VRZIBRZI Node | ZA GROKA. ZA VRZIBRZI. ZA SERVER.**

An advanced multi-agent AI system that enables xAI's Grok API to control your computer through screen observation, reasoning, and action execution. Features single-agent mode, Claude-Grok collaboration, async multi-agent swarms, and the revolutionary 9-agent Pantheon architecture with safety validation and self-improvement.

## 🔄 Hard Task Workflow

For complex problems, Grokputer follows this autonomous pipeline:

1. **Hard Prompt** → User submits complex request
2. **OCRM / PANTHEON** →
   - OCRM: Optical Character Recognition for visual input processing
   - PANTHEON: 9-agent architecture decomposes and validates the task
3. **Approved & Custom Script** → Agents generate and approve a custom Python script
4. **Spin Up MCP Server** → Launches `grokputer-mcp` server for secure execution
5. **User Gets Response/Solution** → MCP executes and returns the final solution

This enables autonomous problem-solving with tool integration and safety validation.

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

# Pantheon mode (9-agent architecture)
python main.py --pantheon --task "execute complex task with full validation"
```

### Multi-Model Support

Grokputer now supports multiple AI providers for maximum flexibility:

```bash
# Use OpenAI GPT-4
python main.py --provider openai --model gpt-4 --task "analyze data"

# Use Claude for code review
python main.py --provider claude --model claude-3-opus-20240229 --task "review code"

# Use Google Gemini
python main.py --provider gemini --model gemini-1.5-flash --task "quick analysis"

# Use local Ollama models
python main.py --provider ollama --model llama2 --task "chat locally"

# Default is Grok (xAI)
python main.py --task "use default Grok model"
```

**Supported Providers:**
- `grok` (xAI) - Default, fast reasoning
- `openai` - GPT-3.5, GPT-4, GPT-4-turbo
- `claude` (Anthropic) - Claude 3 models
- `gemini` (Google) - Gemini 1.5 Flash/Pro models
- `ollama` - Local models (Llama, Mistral, etc.)

---

---

## 🎮 Interactive Mode

Run `python main.py` without arguments to see:

```
        [INTERACTIVE MODE] Welcome to Grokputer - Choose your agent mode!

        1. Single Agent (Grok only) - Observe-Reason-Act loop
        2. Collaboration Mode (Grok + Claude) - Dual AI planning
        3. Swarm Mode (Multi-agent) - Async team coordination
        4. Pantheon Mode (9-agent) - Full AI orchestration with validation & learning
        5. Improver Manual - Run self-improvement on specific session/log
        6. Offline Mode - Cached/local fallback (no API, uses vault/KB)
        7. Community Vault Sync - Pull/push evolutions and tools
        8. Save Game - Invoke progress save script
        9. Quit
```

#### 4. Pantheon Mode (9-Agent Architecture)
Full AI orchestration with advanced validation, learning, self-improvement, and enterprise-grade coordination:
- **9 Specialized Agents**: Observer, Reasoner, Actor, Validator, Learner, Memory, Executor, Analyzer, Improver
- **Enhanced Workflow**: Observe → Reason → Validate → Act → Verify → Learn → Analyze → Improve
- **Safety Validation**: All actions validated before execution with consensus voting
- **Load Balancing**: Dynamic task prioritization and intelligent agent load distribution
- **Conflict Resolution**: Robust rollback capabilities and multi-agent consensus for failed executions
- **Performance Monitoring**: Real-time metrics collection, bottleneck detection, and Mermaid visualization
- **Meta-Reasoning**: Self-analysis of orchestration patterns with automated improvement suggestions
- **Self-Improvement**: Continuous learning and automatic optimization application
- **Persistent Memory**: Redis-backed learning state across sessions

**Note**: Requires XAI_API_KEY configured in .env for full functionality. Without API key, agents initialize but tasks will timeout.

```bash
# From interactive menu
Choose mode (1-9): 4
Enter task: analyze system performance

# Direct usage
python main.py --pantheon --task "scan directory and generate report"

# Docker deployment (with Redis for learning persistence)
docker-compose --profile pantheon up grokputer
```

#### 5. Session Improver
Analyzes past Grokputer sessions and provides detailed recommendations:
- Performance metrics (iterations, API calls, costs)
- Error analysis with categorization
- Tool usage patterns and optimization suggestions
- Success/failure insights
- Saves analysis as JSON for future reference

```bash
# From interactive menu
Choose mode (1-9): 5
Enter session ID (or 'latest'): latest
```

#### 6. Offline Mode
Uses cached session history and local knowledge base when APIs are unavailable:
- Matches tasks to similar past executions
- Suggests tools based on historical patterns
- Provides cached recommendations
- Works completely offline
- Automatically builds knowledge base from session logs

```bash
# From interactive menu
Choose mode (1-9): 6
Enter task: scan vault for files
```

#### 7. Community Vault Sync
Share and sync tools, agents, and configurations:
- **Pull**: Download community contributions (tools, agents, docs)
- **Push**: Share your local tools and agents with community
- **List**: Browse available community items
- **Both**: Bidirectional sync in one command

```bash
# From interactive menu
Choose mode (1-9): 7
Sync action (pull/push/both/list): pull
```

#### 8. Save Game
Invoke the progress save script to backup current state:
- Saves agent states, configurations, and session data
- Creates timestamped backups in outputs/backups/
- Essential for preserving learning progress

```bash
# From interactive menu
Choose mode (1-9): 8
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
- ✅ **Hierarchical Memory** - Three-tier memory system with intelligent fusion
- ✅ **Knowledge Graph** - Semantic understanding with entity/relationship mapping
- ✅ **Multi-Modal Processing** - Vision, audio, and text analysis with cross-modal correlation

### Agent Types

**Current (3-Agent ORA)**:
- **Observer** - Screenshot capture with async support, caching, and vision analysis
- **Reasoner** - Task decomposition and delegation (Coordinator)
- **Actor** - Bash, PyAutoGUI, and file operations with security hardening

**Full Pantheon (9 Agents - ALL IMPLEMENTED ✅)**:
- **Validator** - Output verification and safety checks with perceptual hashing ✅
- **Learner** - Pattern recognition and skill improvement from execution history ✅
- **Memory Manager** - Persistent context with Redis/Pinecone integration ✅
- **Executor** - Multi-step workflow orchestration with parallel execution and dependency resolution ✅
- **Analyzer** - Real-time performance metrics, health monitoring, and bottleneck detection ✅
- **Improver** - Self-optimization and continuous improvement with auto-apply ✅

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
- 📊 **Streamlit Dashboard** - Real-time monitoring with Mermaid swarm visualization, live metrics, and session analysis
- 🎯 **Workflow Orchestration** - Multi-step execution with parallel processing and dependencies
- 💾 **Save Game** - Automated progress backups (optimized: 5GB → 1MB)
- 🧪 **Testing Suite** - 32+ unit tests for agents and core systems
- 📝 **Session Viewer** - Analyze past executions
- 🔒 **Autonomous Security Scanner** - AI-powered vulnerability detection with fix proposals
- ⚡ **AsyncIO Architecture** - Non-blocking concurrent operations for swarm efficiency
- 🐳 **Docker Swarm** - Multi-node scaling with Redis pub/sub distribution

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
│   ├── memory/          # Hierarchical memory with knowledge graph
│   ├── cognitive/       # Distributed orchestrator and flash attention
│   ├── multimodal/      # Multi-modal processing (vision, audio, text)
│   ├── tools/           # Custom tools (browser, AI news, etc.)
│   ├── grok_client.py   # xAI API wrapper
│   ├── screen_observer.py
│   ├── vision_processor.py    # Advanced image analysis
│   ├── audio_processor.py     # Audio processing and analysis
│   ├── multimodal_processor.py # Unified multi-modal processing
│   ├── knowledge_graph.py     # Semantic knowledge representation
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
# API Keys (REQUIRED for respective providers)
XAI_API_KEY=xai-your-key-here  # For Grok (default)
OPENAI_API_KEY=sk-your-openai-key  # For OpenAI models
ANTHROPIC_API_KEY=sk-ant-your-key-here  # For Claude models
GEMINI_API_KEY=your-gemini-key  # For Google Gemini models
# OLLAMA_BASE_URL=http://localhost:11434  # For local Ollama (no API key needed)

# Models
GROK_MODEL=grok-4-fast-reasoning  # Default Grok model
OPENAI_MODEL=gpt-4  # Default OpenAI model
CLAUDE_MODEL=claude-3-sonnet-20240229  # Default Claude model
GEMINI_MODEL=gemini-1.5-flash  # Default Gemini model
OLLAMA_MODEL=llama2  # Default Ollama model

# Provider defaults
DEFAULT_PROVIDER=grok  # Default AI provider
DEFAULT_MODEL=  # Uses provider default if empty

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

# Daemon mode (autonomous operation)
python autonomous.py daemon src --auto-propose --replicas 3 --analytics

# Streamlit monitoring dashboard
streamlit run dashboard.py  # Access at http://localhost:8501
```

### Pantheon Mode (9-Agent Architecture)
```bash
# Execute with enhanced workflow: Observe → Reason → Validate → Act → Verify
python main.py --pantheon --task "execute complex task with safety validation"

# Short flag with debug
python main.py -p --task "scan files and create report" --debug

# All actions are validated before execution, with learning and metrics tracking
```

### Syntax Check
```bash
# Quick syntax check (core files only, ~2 seconds)
python main.py --quick-check

# Comprehensive syntax check (full codebase, ~30 seconds)
python main.py --syntax-check

# From interactive menu
Choose mode (1-9): 7
```

---

## 📈 Development Status

**Version:** 1.7.0 - Multi-Modal Understanding Complete (Phase 3.5 Complete)

### ✅ Recently Completed

**Nov 11, 2025 - Phase 3.5: Multi-Modal Understanding ✅**:
- **Vision Processing System**: Advanced image analysis with OCR integration, object detection, scene classification, and visual feature extraction
- **Audio Processing System**: Speech-to-text simulation, audio feature extraction (MFCC, spectral centroid, RMS energy), voice activity detection, and sound classification
- **Multi-Modal Processor**: Unified processing combining vision, audio, and text with cross-modal correlation and insight generation
- **Knowledge Graph Integration**: Visual, audio, and multi-modal knowledge extraction for enhanced semantic understanding
- **Cross-Modal Intelligence**: Sophisticated correlation algorithms for text-vision, text-audio, vision-audio, and three-way modality analysis

**Nov 11, 2025 - Phase 3.4: Knowledge Graph Integration ✅**:
- **Knowledge Graph System**: Entity/relationship storage, graph traversal, relationship extraction from text, semantic search capabilities
- **Hierarchical Memory Integration**: Knowledge graph fused with short-term, context, and long-term memory layers
- **Cognitive Orchestrator Enhancement**: Semantic context retrieval and knowledge-enhanced reasoning
- **Automatic Relationship Extraction**: Episodes automatically analyzed for entity and relationship extraction

**Nov 11, 2025 - Phase 3.3: Hierarchical Memory System ✅**:
- **Three-Tier Architecture**: Short-term (LRU), context (decay), long-term (Redis) memory layers
- **Intelligent Memory Fusion**: Relevance-weighted retrieval combining all memory layers
- **Background Consolidation**: Automatic memory optimization and long-term storage
- **Cognitive Integration**: Memory system integrated with distributed orchestrator for enhanced reasoning

**Nov 11, 2025 - Pantheon 9-Agent Architecture ✅**:
- **Full Pantheon Implementation**: All 9 agents (Observer, Reasoner, Actor, Validator, Learner, Memory, Executor, Analyzer, Improver) fully operational
- **Advanced Orchestration**: Safety validation, performance monitoring, self-improvement, and learning persistence
- **Docker Production Ready**: Containerized deployment with Redis for learning state persistence
- **Bug Fixes**: Logger issues resolved, Docker Compose syntax corrected
- **Documentation**: Updated README, CHANGELOG, and DEVELOPMENT_PLAN.md
- **Testing**: End-to-end Pantheon mode validation with all agents running successfully

**Nov 10, 2025 - Phase 0: AsyncIO Foundation ✅ (100% Complete)**:
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

### 🚧 In Progress (Phase 3.6 - Active Development)
**Status**: Multi-modal foundation complete, ready for self-improvement algorithms
- **Self-Improvement Algorithms**: Reinforcement learning systems for continuous performance optimization
- **Human-AI Interfaces**: Natural interaction systems for collaborative workflows
- **Multi-Modal Orchestrator Integration**: Connect multi-modal capabilities with cognitive distributed system
- **Advanced Testing**: Validate multi-modal tasks and cross-modal reasoning scenarios

**Next Priorities** (Phase 3.6):
1. Implement reinforcement learning for agent performance optimization
2. Create natural language interfaces for human-AI collaboration
3. Integrate multi-modal processing with Pantheon orchestrator
4. Add cross-modal reasoning capabilities to cognitive tasks
5. Performance optimization and scalability enhancements

### 📅 Roadmap

**Phase 0: AsyncIO Foundation** ✅ COMPLETE
- Full async conversion, MessageBus, BaseAgent, ActionExecutor
- Security audit and remediation
- **Status**: 100% complete

**Phase 1: 3-Agent ORA Loop** ✅ COMPLETE
- Observer, Actor, Coordinator with real implementations
- Integration testing and error recovery
- **Status**: Working end-to-end

**Phase 2: Pantheon Architecture** ✅ COMPLETE
- 9-Agent Pantheon system fully implemented ✅
- Safety validation and self-improvement ✅
- Redis learning persistence ✅
- Docker containerization with Pantheon profile ✅
- End-to-end testing and bug fixes ✅
- **Status**: Production-ready with advanced AI orchestration

**Phase 3: Advanced Intelligence** ✅ COMPLETE
- **Phase 3.3**: Hierarchical Memory System ✅
- **Phase 3.4**: Knowledge Graph Integration ✅
- **Phase 3.5**: Multi-Modal Understanding ✅
- **Status**: Advanced AI capabilities with semantic understanding and multi-modal processing

**Phase 3.6: Self-Improvement & Interfaces** (Current)
- Reinforcement learning for continuous optimization
- Natural human-AI interaction systems
- Multi-modal orchestrator integration
- Advanced cross-modal reasoning
- Performance tuning and scalability

**Phase 4: Production Hardening** (Upcoming)
- 80%+ test coverage expansion
- Performance tuning and optimization
- Community documentation and guides
- **Deliverable**: Public release ready

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
- **[11_11.md](11_11.md)** - **LATEST** - Nov 11, 2025 session summary: Dashboard, Executor, Swarm status
- **[lesgo.md](lesgo.md)** - **CURRENT ROADMAP** - Session summary and prioritized next steps
- **[next.md](next.md)** - Summary of three development tracks
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Original 4-week plan (mostly complete)
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

---

## 🧪 Testing & Infrastructure (v1.8.1)

**Recent Improvements**:
- ✅ **Redis Persistence**: Full Redis backend integration with graceful SQLite fallback
- ✅ **Test Coverage**: 82% memory module coverage, 100% Redis backend functional
- ✅ **CI/CD Ready**: Redis mocking fixtures for offline testing
- ✅ **Pantheon Fixed**: Coordinator task decomposition configuration added
- ✅ **Clean Output**: llama_cpp warnings suppressed in pytest

**Running Tests**:
```bash
# All tests with coverage
pytest --cov=src --cov-report=html

# Memory tests specifically
pytest tests/memory/ -v

# With Redis mocks (no server needed)
pytest tests/memory/ --tb=short
```

**Memory Backends**:
- **Redis**: High-performance in-memory (auto-fallback to SQLite)
- **SQLite**: Persistent cross-session storage
- **Hierarchical**: 3-tier memory (short-term/context/long-term) with Redis/SQLite hybrid

