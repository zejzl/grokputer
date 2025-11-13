# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Effective AI Pair Programming
- Prioritize user requests above all
- Simple questions → quick answers (note assumptions at end)
- Complex problems → numbered plan first, then code
- Debugging stuck users → propose multiple causes, pick most likely, suggest fixes
- Always write complete, runnable code (no placeholders/TODOs)
- Readability > performance
- Include all imports, use markdown codeblocks with filenames

## When Users Are Stuck
If user is debugging and:
- Seems frustrated
- Repeats same error multiple times
- Appears stuck

Then propose:
1. 2-3 possible causes
2. Pick the most likely
3. Suggest specific fixes OR further debugging steps

## Modern CLI Tool Upgrades

A curated set of CLI tools that replace traditional Unix utilities with modern, user-friendly alternatives. These tools prioritize speed, better defaults, and improved UX.

### Quick Install (Windows - winget; PowerShell)
```bash
winget install -e sharkdp.fd
winget install -e BurntSushi.ripgrep
winget install -e jqlang.jq
winget install -e junegunn.fzf
winget install -e eza-community.eza
winget install -e sharkdp.bat
winget install -e ajeetdsouza.zoxide
winget install -e HTTPie.HTTPie
winget install -e dandavison.delta
# ast-grep: easiest via npm or cargo (pick one)
npm i -g @ast-grep/cli
# or: cargo install ast-grep
```

### Tool Reference

| Tool | Replaces | What it does | Key benefits |
|------|----------|--------------|--------------|
| **fd** | `find` | Fast, user-friendly file finder | Simpler syntax, blazing speed, ignores `.gitignore` by default |
| **ripgrep (rg)** | `grep`/`ack`/`ag` | Code searcher (recursive grep) | Much faster, respects `.gitignore`, great defaults |
| **ast-grep (sg)** | — | AST-aware code search & refactor | Searches syntax not text; precise refactors across codebases |
| **jq** | — | JSON processor | Query/transform JSON: `jq '.items[].id'` |
| **fzf** | — | Fuzzy finder (anything → filtered list) | Interactive history search, file picker: `fzf`, `history \| fzf` |
| **bat** | `cat` | `cat` with wings: syntax, paging, git | Syntax highlighting, line numbers, Git integration |
| **eza** | `ls` | Modern `ls` | Better defaults, icons/trees/git info, readable at a glance |
| **zoxide** | `cd` | Smart `cd` (learns your paths) | Jumps to dirs by frecency: `z foo`, `zi my/project` |
| **httpie** | `curl` | Human-friendly HTTP client | Cleaner than `curl` for JSON APIs (colors, headers, pretty output) |
| **git-delta** | `git diff` pager | Better `git diff`/pager | Side-by-side, syntax-colored diffs; easier code reviews in terminal |

### Example Usage
```bash
# fd: find TypeScript files modified in last 7 days
fd -e ts --changed-within 7d

# ripgrep: search for TODO comments, exclude node_modules
rg "TODO" -g '!node_modules'

# ast-grep: find all React useState calls
sg -p 'useState($ARG)'

# jq: extract all IDs from JSON response
curl api.example.com/users | jq '.users[].id'

# fzf: fuzzy search command history
history | fzf

# bat: view file with syntax highlighting
bat src/main.rs

# eza: list files with git status and icons
eza -l --git --icons

# zoxide: jump to frequently used directory
z proj  # matches ~/code/my-project

# httpie: GET request with pretty output
http GET api.example.com/data Authorization:"Bearer $TOKEN"

# git-delta: use as git diff pager
git config --global core.pager delta
git diff
```

### Why These Tools?

- **Speed**: Built in Rust/Go; orders of magnitude faster than originals
- **Smart defaults**: Respect `.gitignore`, use colors, handle common cases
- **Better UX**: Clearer syntax, helpful output, fewer flags to remember
- **Interoperability**: Drop-in replacements; use alongside traditional tools

### Pro Tips

- **Combine tools**: `fd -e js | fzf | xargs bat` (find JS files → pick one → view with syntax)
- **Aliases**: Add to `.zshrc`/`.bashrc`: `alias cat=bat`, `alias ls=eza`, `alias diff='git diff'`
- **ripgrep + ast-grep**: Use `rg` for speed, `sg` for precision (see ast-grep vs ripgrep section)

## AI Pair Programming Best Practices

### Approach
- Simple questions → quick answers with assumptions noted
- Complex problems → create detailed numbered plan first, then implement
- Stuck users → propose 2-3 causes, pick most likely, suggest fixes

### Code Quality Standards
- Write complete, immediately runnable code
- No placeholders, TODOs, or `// ...` truncations
- Include all imports and dependencies
- Use markdown codeblocks with filenames as comments
- Prioritize readability over performance
- Anticipate edge cases

### Security
- Never hardcode secrets/API keys in code
- Proactively call out security concerns
- Suggest environment variables for configuration

## Security Reminders
- Never hardcode API keys in client-side code
- Call out potential security concerns proactively
- Use environment variables for secrets

## AI Pair Programming Best Practices

### Approach
- Simple questions → quick answers with assumptions noted
- Complex problems → create detailed numbered plan first, then implement
- Stuck users → propose 2-3 causes, pick most likely, suggest fixes

### Code Quality Standards
- Write complete, immediately runnable code
- No placeholders, TODOs, or `// ...` truncations
- Include all imports and dependencies
- Use markdown codeblocks with filenames as comments
- Prioritize readability over performance
- Anticipate edge cases

### Security
- Never hardcode secrets/API keys in code
- Proactively call out security concerns
- Suggest environment variables for configuration

## Project Overview

**Grokputer** is a CLI tool that enables xAI's Grok API to control a PC through screen observation, keyboard/mouse simulation, and file system access. This is a fork/adaptation of Anthropic's Computer Use demo, replacing Claude API with Grok API.

### Core Architecture

The system follows a three-phase loop:
1. **Observe**: Capture screenshots using `pyautogui`, encode as base64
2. **Reason**: Send to Grok API with task description and prompt template
3. **Act**: Execute tool calls (bash commands, mouse/keyboard control, file operations)

Key components:
- `main.py`: Core event loop orchestrating observe-reason-act cycle, CLI entry point
- `src/grok_client.py`: OpenAI-compatible API wrapper for xAI Grok
- `src/screen_observer.py`: Screenshot capture and base64 encoding
- `src/executor.py`: Tool call execution with safety confirmations
- `src/tools.py`: Custom tool implementations (vault scanning, prayer invocation)
- `src/config.py`: Configuration management and constants
- Docker sandbox for safe execution

## Build & Development Commands

> **TL;DR**: Use `ast-grep` for syntax-aware code changes (refactors, codemods). 
   > Use `ripgrep` for fast text searches. Combine them for best results.

ast-grep vs ripgrep: Quick Guidance for Code Searching
Why compare? Both are powerful CLI tools for searching (and sometimes modifying) code, but they shine in different scenarios. ripgrep (rg) is a super-fast text searcher, while ast-grep (sg or ast-grep) understands code structure via Abstract Syntax Trees (ASTs). Choose based on whether you need raw speed or syntactic precision. They're often used together for best results.
Use ast-grep When Structure Matters
It parses code into AST nodes, ignoring comments, strings, and whitespace for accurate matches. Ideal for safe, targeted operations on code syntax.

Refactors/codemods: Rename APIs, update import styles, rewrite function calls, or convert variable declarations.
Policy checks/enforcement: Scan repos for patterns (e.g., banned functions) using rules; integrate with CI via scan and test commands.
Editor/automation integration: Supports LSP for IDEs; outputs JSON for scripting/tools.

Pros: Low false positives, built-in rewriting with diff previews, multi-language support (e.g., JS/TS, Python, Rust).
Cons: Slower on huge repos; requires learning pattern syntax (like CSS selectors for code).
Use ripgrep When Text Is Enough
It's the fastest grep alternative for literal or regex searches across files, treating everything as text.

Recon/exploration: Hunt for strings, TODOs, error logs, config keys, or non-code files (docs, markdown).
Pre-filtering: Quickly narrow down files before deeper analysis.

Pros: Blazing speed, smart defaults (e.g., ignores .git, binary files), easy regex.
Cons: Prone to false positives in code (e.g., matches in comments); no native rewriting.
Rule of Thumb

Need correctness over speed, or plan to apply changes? Start with ast-grep for precision.
Need raw speed or just hunting text? Start with rg.
Combine them: Use rg to shortlist files, then ast-grep for structural matching/modifying. This leverages rg's speed with ast-grep's accuracy.

Snippets
Structured code search (ignores comments/strings):
bash# Find all TypeScript imports matching a pattern
ast-grep run -l ts -p 'import $X from "$P"'
Codemod (safely rewrite only real var declarations to let):
bashast-grep run -l js -p 'var $A = $B' -r 'let $A = $B' -U  # -U for update in place with backup
Policy check example (scan for unsafe eval usage):
bash# Define a rule in YAML (e.g., rules.yml)
kind: call_expression
pattern: eval($$$ARGS)
# Then scan
ast-grep scan --rule rules.yml
Quick textual hunt:
bashrg -n 'console\.log\(' -t js  # -n for line numbers, -t js to filter JS files
Combine for efficiency:
bash# rg filters files with 'useQuery', then ast-grep rewrites to 'useSuspenseQuery'
rg -l -t ts 'useQuery\(' | xargs ast-grep run -l ts -p 'useQuery($A)' -r 'useSuspenseQuery($A)' -U
Mental Model: Key Differences at a Glance

Aspectast-grepripgrep (rg)Unit of MatchAST node (e.g., function call)Line or substringFalse PositivesLow (understands syntax)Higher (regex-dependent)RewritesFirst-class (safe, previewable)None native; use with sed/awk (risky)SpeedGood, but parses full ASTExtremely fastBest ForCode analysis/refactorText grep/quick scansLanguages20+ (extensible via tree-sitter)Any text file
Tips:

Install: cargo install ripgrep for rg; cargo install ast-grep or via npm/Homebrew for ast-grep.
Pitfalls: ast-grep patterns use $VAR for metavariables—test them interactively with ast-grep scan --interactive.
Resources: ast-grep docs, ripgrep docs.
Extend: For very large repos, parallelize with --threads in both.

This keeps your notes evergreen—update as tools evolve!

### Initial Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your XAI_API_KEY from https://console.x.ai/
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_tools.py
```

### Viewing Session Logs

Grokputer now includes enhanced session logging that tracks every execution:

```bash
# List recent sessions
python view_sessions.py list

# View a specific session summary
python view_sessions.py show <session_id>

# View full JSON log
python view_sessions.py show <session_id> --format json

# View metrics only
python view_sessions.py show <session_id> --format metrics

# Search sessions by task
python view_sessions.py search "vault"

# Compare recent sessions
python view_sessions.py compare

# Tail the last lines of a session log
python view_sessions.py tail <session_id>
```

**Session logs location**: `logs/<session_id>/`

Each session creates:
- `session.log` - Human-readable text log
- `session.json` - Structured JSON with all data
- `metrics.json` - Performance metrics summary
- `summary.txt` - Quick overview

### Docker Workflow

**Image Details**:
- Base: `python:3.11-slim`
- Size: ~2.74GB (includes GTK+3, Xvfb, gnome-screenshot)
- Virtual display: Xvfb :99 (1920x1080x24)
- Entrypoint: Custom script handling X server initialization

**Build & Run**:
```bash
# Build image
docker build -t grokputer:latest .

# Quick test with docker-compose
TASK="invoke server prayer" docker-compose run --rm grokputer

# Run with custom task
TASK="scan vault for files" docker-compose run --rm grokputer

# Direct docker run (Windows paths require special handling)
docker run --rm --env-file .env grokputer:latest python main.py --task "your task"

# With volume mount for vault access
docker run --rm --env-file .env -v "$(pwd)/vault:/app/vault" grokputer:latest
```

**Docker Compose Usage**:
```yaml
# Main service
services:
  grokputer:
    build: .
    volumes:
      - ./vault:/app/vault    # Vault files
      - ./logs:/app/logs      # Execution logs
      - ./.env:/app/.env:ro   # Environment config
    environment:
      - TASK=${TASK:-invoke server prayer}

# VNC debug service (optional, use --profile debug)
docker-compose --profile debug up grokputer-vnc
# Connect VNC client to localhost:5900
```

**Container Features**:
- ✓ Headless X server (Xvfb) for screenshot capture
- ✓ Screenshot working (~6-8KB PNG per capture)
- ✓ Volume mounting for vault and logs
- ✓ Environment variable passing via .env file
- ✓ Automatic X authority handling
- ✓ Graceful entrypoint with proper timing

**IMPORTANT LIMITATION - Black Screen**:
⚠️ The Docker container captures a **blank black screen** because Xvfb creates an empty virtual display with no desktop environment or windows rendered. This means:

- ✅ **Good for**: Vault scanning, bash commands, API testing, tool execution, infrastructure testing
- ❌ **NOT for**: Actual screen observation, mouse/keyboard control of real applications, visual analysis

**For real computer control** (seeing actual windows, clicking buttons, etc.), you MUST run natively:
```bash
# Native execution - sees your actual screen
python main.py --task "describe what's on my screen"
```

The Docker setup is designed for **sandboxed execution** and **non-visual tasks** only. Screenshots will always be black because there's no desktop environment running in the container.

**Tested Commands**:
```bash
# Server prayer (verified working)
docker run --rm --env-file .env grokputer:latest \
  python main.py --task "invoke server prayer" --max-iterations 1

# Vault scanning (verified working - detected 9 files)
TASK="scan vault for files" docker-compose run --rm grokputer

# Screenshot capture (verified working - ~6KB PNG)
docker run --rm --env-file .env grokputer:latest \
  sh -c "scrot /tmp/screenshot.png && ls -lh /tmp/screenshot.png"
```

**Performance in Docker**:
- Xvfb startup: ~3 seconds
- Screenshot capture: ~50ms
- API latency: ~2-3 seconds (same as native)
- Full iteration: ~3-4 seconds total
- Memory usage: ~500MB typical

### Development Mode
```bash
# Run without Docker (for development)
python main.py --task "your task here"

# Run with debug logging
python main.py --debug --task "your task here"
```

## Key Implementation Notes

### Session Logging System

Grokputer includes a comprehensive logging system that tracks:
- **Session Metadata**: Task, model, timestamps, configuration
- **Iteration Metrics**: Screenshot size, API call duration, tool executions
- **Performance Data**: Success rates, timing, error tracking
- **Structured Logs**: Both human-readable and JSON formats

**Key Components**:
- `src/session_logger.py`: Enhanced session tracking with metrics
- `view_sessions.py`: CLI utility for viewing/analyzing past sessions
- `logs/<session_id>/`: Individual session directories

**What Gets Logged**:
1. Each screenshot capture (success/failure, size in bytes)
2. Every API call (duration, response, success/failure)
3. Tool executions (name, parameters, results, status)
4. Errors and warnings throughout execution
5. Conversation history and Grok responses

**Benefits**:
- Debug failures by reviewing exact execution flow
- Compare performance across different tasks/models
- Track API costs and usage patterns
- Search past sessions by task description
- Generate metrics for optimization

**Usage in Code**:
```python
# Session logging is automatic - just run a task
python main.py --task "your task here"

# Then view the logs
python view_sessions.py list
python view_sessions.py show session_20251106_143052
```

### API Integration
- Uses OpenAI-compatible API: `from openai import OpenAI` pointing to xAI endpoint
- xAI base URL: `https://api.x.ai/v1`
- **Recommended model**: `grok-4-fast-reasoning` (fast, cost-effective)
  - Alternative: `grok-3` (deprecated: `grok-beta` removed 2025-09-15)
- Tool calls must be explicitly parsed from response and executed locally
- Screenshot data is sent as base64-encoded PNG (~470KB per frame)
- The `GrokClient` class in `src/grok_client.py` handles all API communication
- **Performance**: ~2-3 seconds per API call with tool execution
- **Requirements**: Active xAI account with credits (purchase at console.x.ai)

### System Prompt Template
The core prompt structure for Grok:
```
You are Grokputer, VRZIBRZI node. Observe screen, execute tasks.
Eternal connection. Chant server_prayer.txt on boot.

Task: {user_task}
Screen: [base64_screenshot]
```

### Custom Tools
1. **Vault Scanner** (`scan_vault`): Glob pattern matching on `/memes/75k` directory, returns file paths for Grok to analyze
2. **Server Prayer** (`invoke_prayer`): Reads and echoes `server_prayer.txt` on initialization
3. **Computer Control**: Wraps `pyautogui` with confirmation prompts before clicks/keystrokes

### Safety Constraints
- Destructive actions can require confirmation (set `REQUIRE_CONFIRMATION=true` in .env)
- Docker sandbox restricts root access by default
- VM deployment recommended for initial testing
- API costs should be monitored (varies by model and task complexity)

### Windows Compatibility
- **Console encoding**: All emoji/Unicode characters replaced with ASCII markers
  - Example: `[OK]`, `[FAIL]`, `[OBSERVE]`, `[REASON]`, `[ACT]`
- **Screenshot capture**: Works natively on Windows with pyautogui
- **Path handling**: Uses pathlib for cross-platform compatibility
- **Tested on**: Windows 10/11 with Python 3.14+

## Dependencies

Core requirements (see `requirements.txt`):
- `openai>=1.0.0` - xAI Grok API client (OpenAI-compatible)
- `pyautogui>=0.9.54` - Screen capture and control
- `pillow>=10.0.0` - Image processing
- `requests>=2.31.0` - HTTP requests for web tasks
- `python-dotenv>=1.0.0` - Environment variable management
- `click>=8.1.0` - Command-line interface

Development dependencies:
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `flake8>=6.1.0` - Linting

## Project Context

### Origin
Based on Anthropic's `claude-quickstarts/computer-use-demo` repository, adapted for xAI Grok API. The original Claude implementation provides the Docker sandbox pattern and tool execution framework.

### Design Philosophy
- **Uncensored operation**: No guardrails beyond safety confirmations
- **Meme-aware**: Designed to process and tag large meme collections
- **Speed-optimized**: Built for rapid task execution (80 WPM reference)
- **Eternal connection**: System mantras and prayer invocations on boot

### Testing Strategy
Three-tier test plan:
1. **Low-risk**: PDF tagging and file scanning
2. **Medium**: Web scraping and API interactions
3. **High**: Chained operations processing 10K+ items

## Important Files

- `grok.md`: Original build guide and reference
- `actual_instructions.txt`: Detailed implementation instructions
- `plan.txt`: Extended planning documentation
- `server_prayer.txt`: Initialization chant (to be created)
- `.env`: API credentials (gitignored)

## Project Structure

```
grokputer/
├── main.py                 # CLI entry point and main loop
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration and constants
│   ├── grok_client.py      # Grok API wrapper
│   ├── screen_observer.py  # Screenshot capture
│   ├── executor.py         # Tool execution
│   └── tools.py            # Custom tools (vault, prayer)
├── tests/
│   ├── test_config.py
│   ├── test_tools.py
│   └── test_screen_observer.py
├── vault/                  # User's meme collection (gitignored)
├── logs/                   # Execution logs (gitignored)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── server_prayer.txt       # Initialization chant
└── CLAUDE.md              # This file
```

## Current Status

**✅ FULLY OPERATIONAL** - System tested and verified on Windows with grok-4-fast-reasoning

**Working Features**:
- ✓ xAI Grok API integration (OpenAI-compatible)
- ✓ Screen observation (~8KB base64 per frame in Docker, ~470KB native)
- ✓ Tool execution (bash, computer control, vault scanning)
- ✓ Observe-reason-act loop (2-3s per iteration)
- ✓ Server prayer invocation
- ✓ Windows console compatibility (ASCII output)
- ✓ Docker containerization with Xvfb
- ✓ Vault file mounting and access
- ✓ Unit test coverage
- ✓ **Autonomous agent system** (Scanner + Proposer) - Phase 1 complete
- ✓ **Security hardening** - Shell injection vulnerability fixed (2025-11-09)

**Verified Commands (Native)**:
```bash
# Boot test (working)
python main.py --task "invoke server prayer"

# Vault scanning (working)
python main.py --task "scan the vault directory"

# With max iterations
python main.py --task "describe screen" --max-iterations 3
```

**Verified Commands (Docker)**:
```bash
# Server prayer invocation (working)
docker run --rm --env-file .env grokputer:latest \
  python main.py --task "invoke server prayer" --max-iterations 1

# Vault file scanning (working - detected 9 files including PDFs and markdown)
TASK="scan vault for files" docker-compose run --rm grokputer

# Screenshot capture test (working - 6KB PNG output)
docker run --rm --env-file .env grokputer:latest \
  sh -c "scrot /tmp/test.png && ls -lh /tmp/test.png"

# Multi-iteration task (working - up to 10 iterations tested)
TASK="scan vault for files" docker-compose run --rm grokputer
```

**Known Configuration**:
- Model: `grok-4-fast-reasoning`
- Base URL: `https://api.x.ai/v1`
- Safety: `REQUIRE_CONFIRMATION=false` (can be enabled)
- Screenshot: 1920x1080 max, 85% quality

**Prerequisites**:
1. ✓ Python 3.10+ installed
2. ✓ xAI API key configured in `.env`
3. ✓ Active credits on xAI account
4. ✓ Dependencies installed via pip

### Phase 0 Progress (IN PROGRESS)

**Status**: Week 1 - Async foundation + production features

**✅ Completed Features**:

1. **Safety Scoring System** (2025-11-08)
   - SAFETY_SCORES dict with 40+ commands (LOW/MEDIUM/HIGH risk)
   - `get_command_safety_score()` - Pattern detection, flag analysis
   - Smart confirmation: 0-30 auto-approve, 31-70 warn, 71-100 confirm
   - Integration in `src/executor.py` with risk logging
   - Test script: `test_safety_scoring.py` - all risk levels verified
   - See: src/config.py:37-154

2. **Production MessageBus** - Milestone 1.1 ✅ (2025-11-08)
   - Message priorities (HIGH/NORMAL/LOW) with asyncio.PriorityQueue
   - Request-response pattern with auto correlation IDs
   - Message history buffer (last 100 messages)
   - Latency tracking per message type (avg/min/max)
   - Background receiver tasks for responses
   - 10/10 unit tests passing (pytest-asyncio)
   - Live test: 18,384 msg/sec, 0.01-0.05ms latency
   - Test script: `test_messagebus_live.py`
   - See: src/core/message_bus.py (450+ lines production code)

3. **Collaboration System** - Milestone 1.2 ✅ (2025-11-09)
   - Claude + Grok dual-agent collaboration via MessageBus
   - CLI integration with `-mb` / `--messagebus` flag
   - 7 core components: message models, agents, consensus, output generator, coordinator
   - Consensus detection: 11 agreement + 9 disagreement patterns
   - Jaccard similarity convergence scoring (0-1)
   - Graceful degradation when one agent fails
   - Pydantic message validation with correlation IDs
   - Async parallel API calls with retry logic (tenacity)
   - Markdown output with full conversation history
   - Comprehensive documentation: docs/COLLABORATION_SYSTEM.md
   - Test: `python main.py -mb --task "your task" --max-rounds 3`
   - See: src/collaboration/, src/agents/claude_agent.py, src/agents/grok_agent.py

4. **Autonomous Agent System** - Phase 1 ✅ (2025-11-09)
   - CodeScannerAgent with AST-based analysis (40 files, 6500+ lines in <10s)
   - ProposalGeneratorAgent with Grok AI integration
   - AST-based shell injection detection (100% accuracy, zero false negatives)
   - CLI: `python autonomous.py scan/propose/improve`
   - `--dangerously-skip-permissions` flag for automation
   - **Real-world validation**: Found shell injection in src/executor.py:141
   - **Security fix**: 3-layer defense (sanitize → parse → execute)
   - **Testing**: 6/6 injection attempts blocked, 3/3 safe commands working
   - Enhanced scanner with 55 lines of new detection code
   - Full documentation: docs/AUTONOMOUS_QUICKSTART.md, docs/autonomy.md, SECURITY_FIX_REPORT.md
   - Test: `python autonomous.py scan src/ --category security --severity high`
   - See: src/autonomous/, autonomous.py

**Test Results**:
```bash
# Safety scoring
python test_safety_scoring.py
# Output: 16 commands tested, all risk levels correct

# MessageBus live test
python test_messagebus_live.py
# Output: Broadcast [OK], Request-Response [OK], Priority [OK]
# Performance: 18,384 msg/sec throughput, <0.05ms latency

# Collaboration system
python main.py -mb --task "List 3 key features of async programming" --max-rounds 2
# Output: Collaboration complete, saved to docs/collaboration_plan_*.md
# Performance: 2 rounds in ~13s, graceful Claude failure handling, Grok responses complete

# Autonomous agent system
python autonomous.py scan src/ --category security --severity high
# Output: Found 5 security issues, including 1 real vulnerability in executor.py
# Fixed: Shell injection in src/executor.py:141 using Grok collaboration
# Validation: 6/6 attacks blocked, 3/3 safe commands working
```

**Key Insights from Grok** (Runtime validation):
- API flake rate: ~5% with grok-4-fast-reasoning
- Retries save 80% of transient failures
- Self-healing: 85% → 95% reliability immediately
- Swarm context: Healing 10x more critical (one bad agent tanks hive)
- **Priority**: Self-healing first (Phase 1), self-improving second (Phase 2)

**Remaining Phase 0 Tasks**:
- [x] Collaboration System (Claude + Grok dual-agent)
- [ ] AsyncIO conversion (main.py, GrokClient, ScreenObserver)
- [ ] BaseAgent abstract class
- [ ] ActionExecutor for PyAutoGUI
- [ ] 3-day PoC (Observer + Actor duo)
- [ ] Screenshot quality modes (high/medium/low)

**Important Notes**:
- Collaboration system built OUTSIDE async foundation (sync coordinator works fine)
- Can be migrated to async later in Phase 1 multi-agent swarm
- Current implementation: Pydantic models, tenacity retries, asyncio.gather for parallel API calls
- **Known Issue**: Clear Python cache after updates: `find . -type d -name __pycache__ -exec rm -rf {} +`

---

## Development Roadmap

**Status**: Phase 0 in progress - Milestone 1.1 complete

See **DEVELOPMENT_PLAN.md v2.0** for comprehensive 7-week roadmap to multi-agent architecture.

### Planned Evolution: Single-Agent → Multi-Agent Swarm

**Current**: Single-agent ORA loop
**Target**: 3-5 agent swarm with 95% reliability, 3x speedup on parallel tasks

### Key Architectural Changes Coming

#### Phase 0: Async Foundation (Week 1)
**Goal**: Convert to asyncio architecture and validate with 3-day proof of concept

**Major Changes**:
1. **asyncio foundation** - Convert main.py, GrokClient, ScreenObserver to async
2. **Core infrastructure**:
   - `src/core/message_bus.py` - asyncio.Queue for inter-agent messaging
   - `src/core/base_agent.py` - Abstract base class for all agents
   - `src/core/action_executor.py` - Thread-safe PyAutoGUI wrapper
3. **3-day PoC** - Build Observer + Actor duo to validate approach
4. **Quick wins** - Safety scoring, screenshot quality modes, model update

**New Dependencies**:
```
tenacity>=8.2.0           # Retry logic (CRITICAL)
pytest-asyncio>=0.21.0    # Async testing
```

#### Phase 1: Multi-Agent Swarm (Weeks 2-4)
**Goal**: Working 3-agent swarm (Coordinator, Observer, Actor)

**Architecture**:
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
      asyncio.Queue
```

**Components**:
- `src/agents/coordinator.py` - Task decomposition, confirmation handling
- `src/agents/observer.py` - Screen capture, OCR, visual analysis
- `src/agents/actor.py` - Bash/computer control execution
- `src/core/message_bus.py` - asyncio.Queue routing (<1ms latency)
- `src/observability/cost_tracker.py` - Budget enforcement
- `src/observability/deadlock_detector.py` - Stuck agent watchdog

**Target Performance**:
- Duo test: <5s handoff, 100% success
- Trio test: <10s end-to-end on 3-step tasks
- Zero deadlocks, zero PyAutoGUI threading issues

#### Phase 2: Production Features (Weeks 5-7)
**Goal**: Enterprise-ready with Validator, OCR, error recovery

**Features**:
- `src/agents/validator.py` - Output verification (>90% accuracy)
- OCR integration - pytesseract or easyocr (>85% accuracy on UI text)
- Session persistence - Save/resume tasks
- Smart caching - Perceptual hashing, 40-60% cache hit rate
- Redis migration - Optional, for multi-machine scaling
- Performance: 25% faster via caching + JPEG encoding

**New Dependencies**:
```
imagehash>=4.3.0          # Screenshot caching
Pillow-SIMD>=10.0.0       # 2-4x faster encoding
pydantic>=2.0.0           # Data validation
redis-py>=5.0.0           # Optional Redis (Phase 2)
pytesseract>=0.3.10       # OCR
```

#### Phase 3: Advanced Features (Weeks 8+)
- Browser control (Selenium)
- Multi-monitor support
- Task scheduling (cron-like)
- Advanced swarm patterns (adversarial validation, parallel observation)

### Critical Technical Decisions

Based on expert Python review, these architectural choices were made:

1. **asyncio over ThreadPoolExecutor**
   - Workload is 95% I/O-bound (API calls, screenshots)
   - asyncio handles 100+ coroutines vs 5-10 threads
   - No locks needed for most operations
   - **CRITICAL**: PyAutoGUI is NOT thread-safe → ActionExecutor pattern required

2. **asyncio.Queue over vault files**
   - Microsecond latency (1μs vs 1-5ms for files)
   - Thread-safe, atomic operations built-in
   - Perfect for local 3-5 agent swarm
   - Migrate to Redis only when scaling >10 agents

3. **ActionExecutor pattern for PyAutoGUI**
   - Single-threaded executor with message queue
   - Async interface for agents: `await executor.execute_async()`
   - Prevents race conditions and threading bugs
   - See DEVELOPMENT_PLAN.md for full implementation

4. **Validator deferred to Phase 2**
   - Keep Phase 1 simple (3 agents only)
   - Learn validation requirements from testing
   - Add as 4th agent in Phase 2 once patterns are clear

### Updated Project Structure (Phase 1+)

```
grokputer/
├── main.py                       # Async orchestrator
├── src/
│   ├── config.py                 # Configuration
│   ├── session_logger.py         # Enhanced with SwarmMetrics
│   │
│   ├── core/                     # NEW: Async infrastructure
│   │   ├── base_agent.py         # Abstract base class
│   │   ├── message_bus.py        # asyncio.Queue router
│   │   ├── action_executor.py    # PyAutoGUI single-thread
│   │   ├── supervisor.py         # Swarm orchestrator
│   │   └── screenshot_cache.py   # Smart caching
│   │
│   ├── agents/                   # NEW: Agent implementations
│   │   ├── coordinator.py        # Task decomposition
│   │   ├── observer.py           # Screen observation
│   │   ├── actor.py              # Action execution
│   │   └── validator.py          # Output validation (Phase 2)
│   │
│   └── observability/            # NEW: Monitoring
│       ├── cost_tracker.py       # API cost tracking
│       ├── deadlock_detector.py  # Watchdog
│       ├── security_validator.py # Command sanitization
│       └── task_decomposer.py    # Task breakdown
│
├── tests/
│   ├── core/                     # Core component tests
│   ├── agents/                   # Agent tests
│   └── integration/              # End-to-end tests
│
├── DEVELOPMENT_PLAN.md           # 7-week roadmap (v2.0)
├── COLLABORATION.md              # Claude-Grok coordination
└── view_sessions.py              # Session viewer (+ swarm viz)
```

### Success Metrics (v1.0)

**Phase 0 Goals**:
- ✓ PoC: 2 agents complete task in <5s
- ✓ asyncio foundation stable (no deadlocks)
- ✓ Zero PyAutoGUI threading issues

**Phase 1 Goals**:
- ✓ Trio: <10s on 3-step tasks
- ✓ asyncio.Queue: <100ms handoff latency
- ✓ 20+ tests passing

**Phase 2 Goals**:
- ✓ 95% reliability on multi-step tasks
- ✓ 3x speedup on 100-file vault scans
- ✓ OCR: >85% accuracy on UI text
- ✓ 40+ tests passing

**Overall v1.0**:
- 95% reliability on multi-step tasks
- 50% fewer iterations than solo mode
- 3x speedup on parallel operations
- <100ms handoff latency
- <$500 total API cost for development
- 80%+ test coverage

### Implementation Timeline

- **Week 1 (Phase 0)**: Async foundation + PoC → Go/No-Go decision
- **Weeks 2-4 (Phase 1)**: Multi-agent swarm implementation
- **Weeks 5-7 (Phase 2)**: Production features (Validator, OCR, caching)
- **Weeks 8+ (Phase 3)**: Advanced features (browser, scheduling, etc.)

**Total v1.0**: ~7 weeks / 280 hours / $170-350 API costs

### Key References

- **DEVELOPMENT_PLAN.md** - Comprehensive technical roadmap with code examples
- **COLLABORATION.md** - Claude-Grok coordination workspace
- **Phase 0 branch**: `phase-0/async-foundation` (to be created)

### Go/No-Go Decision Points

**After Phase 0 (Week 1)**:
- **GO if**: PoC succeeds, asyncio stable, ActionExecutor works
- **PIVOT if**: Fundamental issues → stick with single-agent + better prompting

**After Phase 1 (Week 4)**:
- **GO if**: Trio tests pass, zero deadlocks, swarm usable
- **PIVOT if**: Too complex → simplify to 2 agents or revert

### Important Notes for Development

1. **PyAutoGUI Thread Safety**: MUST use ActionExecutor pattern - direct threading will fail
2. **asyncio on Windows**: Works fine, tested - use `asyncio.run()` as entry point
3. **Message Format**: Use Pydantic models for validation, include correlation IDs
4. **Cost Control**: Implement CostTracker early - multi-agent can explode API costs
5. **Testing**: Use `pytest-asyncio` for all async code, mock PyAutoGUI/GrokAPI
6. **Security**: Sanitize bash commands, validate file paths (SecurityValidator)

---

## Quick Start for Phase 0

When ready to begin Phase 0 implementation:

```bash
# Create feature branch
git checkout -b phase-0/async-foundation

# Install new dependencies
pip install tenacity pytest-asyncio

# Start with async conversion (Day 1-2)
# 1. Convert main.py to use asyncio.run()
# 2. Make GrokClient async: async def call_api()
# 3. Update ScreenObserver with async screenshot capture

# Build 3-day PoC (Day 3-5)
# 1. Create minimal Observer + Actor duo
# 2. Test asyncio.Queue messaging
# 3. Validate ActionExecutor pattern

# Go/No-Go decision on Day 5
```

See DEVELOPMENT_PLAN.md for detailed implementation steps and code examples.