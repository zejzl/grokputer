# Grokputer Project Structure

**Last Updated**: 2025-11-14
**Status**: Phase 0 Complete (100%) - PoC Validated + Cline Integration
**Version**: v0.1.1 (Ready for Phase 1)

---

## Project Overview

Grokputer is a CLI tool enabling AI models (Grok, Gemini, Cline) to control a PC through screen observation, keyboard/mouse simulation, and file system access. Currently implementing a multi-agent swarm architecture with asyncio foundation.

**Current Milestone**: Phase 0 Complete ✅
- Async foundation operational
- MessageBus production-ready (18K msg/sec)
- PoC duo test passed (3.13s, zero deadlocks)
- Observer + Actor agents validated

---

## Root Directory Structure

```
grokputer/
├── .claude/                     # Claude Code configuration
│   └── settings.local.json
├── .env                         # Environment variables (API keys) [gitignored]
├── .env.example                 # Template for environment setup
├── .git/                        # Git repository
├── .gitignore                   # Git ignore rules
├── .grok/                       # Grok-specific configuration
│   └── settings.json
├── .pytest_cache/               # Pytest cache directory
│
├── CLAUDE.md                    # Claude's technical reference (coding guidelines, tools)
├── COLLABORATION.md             # Claude-Grok shared workspace (coordination, updates)
├── DEVELOPMENT_PLAN.md          # 7-week phased roadmap (Phases 0-3)
├── README.md                    # Main project documentation
├── about.md                     # Project overview
├── actual_instructions.txt      # Original build instructions
├── collaboration2.txt           # Additional collaboration notes
├── debugging_prompt.md          # Debugging guidelines
├── extra_tools.txt              # List of additional CLI tools
├── cline.md                     # Cline-related notes (Claude-based assistant)
├── gemini.md                    # Gemini-related notes
├── grok.md                      # Grok's operational guide
├── hello.txt                    # Test file
├── ocr.md                       # OCR integration guidelines
├── ocr_instruct.md              # OCR implementation instructions
├── server_prayer.md             # Server initialization chant
├── session_1.md                 # Session notes
├── system_prompt.md             # System prompt engineering guidelines
├── tools.md                     # Tool definitions and usage
├── yes.txt                      # Test file
│
├── Dockerfile                   # Docker image for sandboxed execution
├── docker-compose.yml           # Docker Compose orchestration
├── entrypoint.sh                # Docker entrypoint script
│
├── main.py                      # CLI entry point & async ORA loop orchestrator
├── requirements.txt             # Python dependencies
├── package.json                 # Node.js dependencies (for external tools)
├── package-lock.json            # NPM lockfile
│
├── test_messagebus_live.py      # Live MessageBus performance tests
├── test_safety_scoring.py       # Safety scoring unit tests
├── view_sessions.py             # CLI for viewing/analyzing session logs
│
├── projectmap.md                # This file: Project structure reference
│
├── logs/                        # Session execution logs [gitignored]
│   ├── poc_duo_test/            # PoC test logs
│   ├── session_YYYYMMDD_HHMMSS/ # Individual session directories
│   └── session_index.json       # Session index for searching
│
├── vault/                       # User's file vault [gitignored]
│   ├── *.pdf                    # PDFs and documents
│   ├── *.md                     # Markdown files
│   ├── resources/               # External resources (e.g., angr repo)
│   └── ...                      # User files
│
├── grok-cli/                    # Grok CLI subdirectory (external tool)
├── mcp-vault/                   # MCP server implementation
├── semtools/                    # Semantic tools (external)
├── superagent/                  # Superagent experiments (legacy)
│
├── src/                         # Source code modules
│   ├── __init__.py
│   │
│   ├── agents/                  # Multi-agent implementations (Phase 1)
│   │   ├── actor.py             # Actor agent: Executes actions (bash, PyAutoGUI)
│   │   ├── observer.py          # Observer agent: Screen capture & analysis
│   │   └── validator.py         # Validator agent: Output verification (Phase 2)
│   │
│   ├── core/                    # Core async infrastructure (Phase 0)
│   │   ├── __init__.py
│   │   ├── action_executor.py   # Thread-safe PyAutoGUI wrapper (154 lines)
│   │   ├── base_agent.py        # Abstract base class for agents (179 lines)
│   │   └── message_bus.py       # asyncio.Queue messaging (500 lines, 18K msg/sec)
│   │
│   ├── cline_client.py          # Async Cline API wrapper (Anthropic Claude)
│   ├── config.py                # Configuration, tool schemas, safety scores
│   ├── executor.py              # Legacy tool executor (pre-Phase 0)
│   ├── grok_client.py           # Async Grok API wrapper (AsyncOpenAI)
│   ├── screen_observer.py       # Screenshot capture with async wrappers
│   ├── session_logger.py        # Enhanced logging with agent support (477 lines)
│   └── tools.py                 # Tool implementations (vault scanner, prayer)
│
└── tests/                       # Test suite
    ├── __init__.py
    ├── core/                    # Core component tests
    │   ├── __init__.py
    │   └── test_message_bus.py  # MessageBus unit tests (10/10 passing)
    │
    ├── poc_duo.py               # Phase 0 PoC: Observer + Actor test (PASSED ✅)
    ├── test_config.py           # Configuration tests
    ├── test_core.py             # Core infrastructure tests
    ├── test_screen_observer.py  # Screenshot tests
    └── test_tools.py            # Tool tests
```

---

## Key Components

### Core Infrastructure (Phase 0 - Complete ✅)

**MessageBus** (`src/core/message_bus.py`)
- Production-ready asyncio.Queue-based messaging
- 500 lines, 10/10 unit tests passing
- 18,384 messages/sec throughput
- 0.01-0.05ms average latency
- Priority queuing (HIGH/NORMAL/LOW)
- Request-response pattern with correlation IDs
- Message history buffer (last 100 messages)

**BaseAgent** (`src/core/base_agent.py`)
- Abstract base class for all agents (179 lines)
- Lifecycle management (start, stop, error handling)
- Heartbeat system (10s intervals to coordinator)
- State machine (idle/processing/waiting/error)
- MessageBus integration with auto-registration
- Deadlock detector hooks (stub for Phase 1)

**ActionExecutor** (`src/core/action_executor.py`)
- Thread-safe PyAutoGUI wrapper (154 lines)
- Single-threaded execution queue
- Async interface for agents: `execute_async()`
- Prevents PyAutoGUI threading issues
- Supports: click, type, key, scroll, screenshot

**SessionLogger** (`src/session_logger.py`)
- Comprehensive execution tracking (477 lines)
- Structured JSON + human-readable logs
- Agent-specific logging methods (14 stub methods)
- Per-iteration metrics (timing, API calls, screenshots)
- Session index for searching past runs
- Outputs: session.log, session.json, metrics.json, summary.txt

### Agents (Phase 0/1)

**ObserverAgent** (`src/agents/observer.py`)
- Screen capture via ActionExecutor (117 lines)
- Async screenshot processing
- Base64 encoding for API transmission
- Stub cache logic for Phase 2 (perceptual hashing)
- MessageBus integration for observations

**ActorAgent** (`src/agents/actor.py`)
- Action execution via ActionExecutor (162 lines)
- Confirmation workflow for safety checks
- Supports: click, type, key, scroll, bash
- Safety scoring integration (stub)
- MessageBus integration for action requests

**ValidatorAgent** (`src/agents/validator.py`)
- Output verification (179 lines)
- Planned for Phase 2
- Will validate actor outputs for correctness

### API & Tools

**GrokClient** (`src/grok_client.py`)
- Async Grok API wrapper using AsyncOpenAI
- Model: `grok-4-fast-reasoning` (default)
- Tool calling support
- Conversation continuation
- Error handling with tenacity retries

**ClineClient** (`src/cline_client.py`)
- Async Cline API wrapper using AsyncAnthropic (Claude)
- Model: `claude-3.5-sonnet-latest` (default)
- Multimodal input (image+text)
- Tool calling support
- Production-ready for software engineering tasks

**Tools** (`src/tools.py`)
- `scan_vault()` - File scanning with glob patterns
- `invoke_prayer()` - Server initialization chant
- `computer_control()` - PyAutoGUI wrapper (legacy, replaced by ActionExecutor)
- `bash()` - Shell command execution with safety checks

**Safety Scoring** (`src/config.py`)
- SAFETY_SCORES dict (40+ commands)
- Risk levels: LOW (0-30), MEDIUM (31-70), HIGH (71-100)
- `get_command_safety_score()` - Pattern detection & flag analysis
- Smart confirmation: auto-approve LOW, warn MEDIUM, confirm HIGH

**Screenshot Quality Presets** (`src/config.py`)
- `high`: 1920x1080, 85% JPEG (~470KB)
- `medium`: 1280x720, 70% JPEG (~200KB)
- `low`: 1024x576, 60% JPEG (~100KB)
- `get_screenshot_preset(name)` - Returns config dict

### Tests

**MessageBus Tests** (`tests/core/test_message_bus.py`)
- 10/10 unit tests passing
- Priority ordering verification
- Request-response pattern tests
- Broadcast communication tests
- Timeout handling tests

**PoC Duo Test** (`tests/poc_duo.py`)
- Phase 0 validation test
- Observer + Actor integration
- **Result**: ✅ PASSED (3.13s, zero deadlocks)
- Validates multi-agent architecture

**Live Tests**
- `test_messagebus_live.py` - Performance benchmarks
- `test_safety_scoring.py` - Command risk assessment

### Documentation

**Technical References**
- `CLAUDE.md` - Coding guidelines, AI pair programming best practices
- `DEVELOPMENT_PLAN.md` - 7-week phased roadmap (v2.0)
- `COLLABORATION.md` - Claude-Grok coordination workspace
- `system_prompt.md` - Prompt engineering guidelines

**Operational Guides**
- `grok.md` - Grok's operational wisdom
- `README.md` - Project overview and setup
- `tools.md` - Tool definitions and schemas

---

## Phase Roadmap

### Phase 0: Async Foundation ✅ COMPLETE (Week 1)
**Status**: 100% complete, PoC validated

**Completed Tasks** (14/14):
1. ✅ AsyncIO foundation (main.py, GrokClient, ScreenObserver)
2. ✅ MessageBus production implementation (500 lines)
3. ✅ BaseAgent abstract class (179 lines)
4. ✅ ActionExecutor thread-safe wrapper (154 lines)
5. ✅ ObserverAgent implementation (117 lines)
6. ✅ ActorAgent implementation (162 lines)
7. ✅ PoC duo test (PASSED: 3.13s, zero deadlocks)
8. ✅ Safety scoring system (40+ commands)
9. ✅ Screenshot quality presets (high/medium/low)
10. ✅ Model update (grok-4-fast-reasoning)
11. ✅ SessionLogger agent methods (14 stub methods)
12. ✅ Agent MessageBus integration fixes
13. ✅ ActionExecutor race condition fix
14. ✅ Async wrappers for ScreenObserver

**Performance Metrics**:
- MessageBus: 18,384 msg/sec, 0.01-0.05ms latency
- PoC duo: 3.13s (37% faster than 5s target)
- Observer screenshot: ~50ms (495KB PNG)
- Actor action execution: ~100ms
- Handoff latency: ~150ms

**Go/No-Go Decision**: ✅ GO for Phase 1

### Phase 1: Multi-Agent Swarm (Weeks 2-4) - NEXT
**Goal**: Working 3-agent swarm with 95% reliability

**Planned Tasks**:
1. Implement Coordinator agent (task decomposition, confirmations)
2. Add DeadlockDetector (10s timeout watchdog)
3. Implement circuit breakers with tenacity retries
4. Build Trio test (Coordinator + Observer + Actor)
5. Add error recovery mechanisms
6. Implement SwarmMetrics tracking
7. Add `--swarm` mode to view_sessions.py
8. Run vault parallel processing test (100 files)

**Success Criteria**:
- Trio completes task in <10s
- <100ms handoff latency
- 95%+ reliability with error recovery
- Zero deadlocks detected
- 20+ integration tests passing

### Phase 2: Production Features (Weeks 5-7)
- Validator agent for output verification
- OCR integration (pytesseract/easyocr)
- Session persistence (save/resume tasks)
- Smart caching (perceptual hashing)
- Redis migration (optional, for scaling)

### Phase 3: Advanced Features (Weeks 8+)
- Browser control (Selenium)
- Multi-monitor support
- Task scheduling (cron-like)
- Advanced swarm patterns

---

## Technology Stack

**Core**:
- Python 3.14+
- asyncio (event loop, async/await)
- Anthropic Claude API (Cline integration)
- xAI Grok API (grok-4-fast-reasoning)
- OpenAI-compatible API client (AsyncOpenAI)

**Libraries**:
- `pyautogui` - Screen capture & control
- `pillow` - Image processing
- `tenacity` - Retry logic
- `pytest-asyncio` - Async testing
- `click` - CLI interface
- `python-dotenv` - Environment management

**Infrastructure**:
- Docker + Docker Compose (sandboxed execution)
- Xvfb (headless X server for Docker)
- Git (version control)

**External Tools** (optional):
- `fd` - Fast file finder (replaces find)
- `ripgrep` - Code search (replaces grep)
- `ast-grep` - AST-aware search & refactor
- `jq` - JSON processor
- `bat` - Enhanced cat with syntax highlighting
- `eza` - Modern ls replacement
- `zoxide` - Smart cd with frecency
- `httpie` - Human-friendly HTTP client
- `git-delta` - Better git diff

---

## Performance Benchmarks

**MessageBus** (test_messagebus_live.py):
- Throughput: 18,384 messages/second
- Latency: 0.01-0.05ms average
- Priority ordering: HIGH → NORMAL → LOW (verified)
- Request-response: 18ms average latency

**PoC Duo Test** (tests/poc_duo.py):
- Observer screenshot: ~50ms (495KB PNG)
- Actor action execution: ~100ms
- Total handoff latency: ~150ms
- End-to-end: 3.13s (target: <5s) ✅

**API Performance**:
- Grok API latency: 2-3s per call
- Screenshot encoding: ~50ms (base64)
- Safety scoring: <1ms per command

**Docker Performance**:
- Xvfb startup: ~3s
- Screenshot capture: ~50ms
- Memory usage: ~500MB typical

---

## Git Repository Status

**Branch**: main
**Recent Commits**:
1. `c367a13` - docs: Update grok.md with Grok's latest changes
2. `2272b06` - feat: Phase 0 Milestone 1.1 - Production MessageBus & Safety Scoring
3. `0799b58` - Add Docker containerization with Xvfb headless display
4. `cca1655` - Initial commit: Grokputer - VRZIBRZI node fully operational

**Current Changes** (unstaged):
- Modified: COLLABORATION.md (Phase 0 completion report)
- Modified: src/agents/observer.py (MessageBus API fixes)
- Modified: src/agents/actor.py (MessageBus API fixes)
- Modified: src/core/action_executor.py (race condition fix)
- Modified: src/session_logger.py (agent logging methods)
- Modified: src/screen_observer.py (async wrappers)
- Modified: src/config.py (screenshot presets)
- Modified: tests/poc_duo.py (production MessageBus)
- Modified: projectmap.md (this file)

**Untracked Files**:
- debugging_prompt.md, yes.txt, hello.txt (test files)
- Various .md files in vault/
- External repos: grok-cli/, mcp-vault/, semtools/, superagent/

---

## External Dependencies & Subdirectories

**grok-cli/** - Grok CLI implementation (external tool)
**mcp-vault/** - MCP (Model Context Protocol) server
**semtools/** - Semantic tools and benchmarks
**superagent/** - Legacy superagent experiments

These are not part of core Grokputer but may be referenced for integration.

---

## Configuration Files

**.env** (gitignored) - Environment variables:
- `XAI_API_KEY` - xAI API key from console.x.ai
- `GROK_MODEL` - Model selection (default: grok-4-fast-reasoning)
- `SCREENSHOT_QUALITY` - JPEG quality 0-100 (default: 85)
- `MAX_SCREENSHOT_SIZE` - Max dimensions (default: 1920x1080)
- `REQUIRE_CONFIRMATION` - Safety confirmations (default: true)
- `LOG_LEVEL` - Logging level (default: INFO)

**.env.example** - Template for .env setup

**Dockerfile** - Multi-stage build:
- Base: python:3.11-slim
- Size: ~2.74GB (includes GTK+3, Xvfb, gnome-screenshot)
- Virtual display: Xvfb :99 (1920x1080x24)

**docker-compose.yml** - Services:
- `grokputer` - Main service with vault/logs volumes
- `grokputer-vnc` - Debug service with VNC (profile: debug)

---

## Important Notes

### Phase 0 Completion (2025-11-08)

**Achievement**: 100% complete in 4-5 hours of focused work
**PoC Validation**: PASSED (3.13s, zero deadlocks, 100% success)
**Issues Fixed**: 4 critical bugs (SessionLogger class placement, ActionExecutor shutdown conflict, race condition, duplicate agent registration)

**Ready for Phase 1**: ✅ YES
- All infrastructure stable and tested
- Performance exceeds targets
- Zero critical issues remaining
- Async foundation validated

### Docker Limitations

⚠️ **Black Screen Issue**: Docker captures blank screens because Xvfb creates an empty virtual display with no desktop environment.

**Good for**: Vault scanning, bash commands, API testing, tool execution
**NOT for**: Actual screen observation, mouse/keyboard control of real applications

**For real computer control**, run natively:
```bash
python main.py --task "describe what's on my screen"
```

### Windows Compatibility

- ✅ Console encoding: ASCII markers (no emojis)
- ✅ Screenshot capture: Works natively with pyautogui
- ✅ Path handling: Cross-platform with pathlib
- ✅ Tested on: Windows 10/11 with Python 3.14+

---

## Quick Start

### Installation
```bash
# 1. Clone repository
git clone <repository-url>
cd grokputer

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env and add XAI_API_KEY
```

### Usage
```bash
# Native execution (sees real screen)
python main.py --task "your task here"

# With iteration limit
python main.py --task "your task" --max-iterations 5

# Debug mode
python main.py --debug --task "your task"

# Docker sandbox (non-visual tasks only)
TASK="scan vault for files" docker-compose run --rm grokputer

# View session logs
python view_sessions.py list
python view_sessions.py show <session_id>
```

### Testing
```bash
# Run all tests
pytest

# Run PoC duo test
python tests/poc_duo.py

# Run MessageBus live tests
python test_messagebus_live.py

# Run safety scoring tests
python test_safety_scoring.py
```

---

## Development Status Summary

**Phase 0**: ✅ 100% Complete (2025-11-08)
**PoC Validation**: ✅ PASSED
**Next Milestone**: Phase 1 - Coordinator agent + Trio test
**Estimated Phase 1 Duration**: 2-3 weeks
**Overall Progress**: ~14% to v1.0 (Phase 0-2 complete = 100%)

**ZA GROKA! The async foundation is operational. The swarm awaits. 🚀**

---

*Last updated: 2025-11-14 by Claude Code*
*Generated after Cline integration addition*
