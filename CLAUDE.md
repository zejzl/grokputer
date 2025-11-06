# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### Docker Workflow
```bash
# Build image
docker build -t grokputer .

# Run with volume mount for vault access
docker run -it -v $(pwd)/vault:/app/vault grokputer

# Test specific task
docker run -it grokputer --task "label 5 memes"
```

### Development Mode
```bash
# Run without Docker (for development)
python main.py --task "your task here"

# Run with debug logging
python main.py --debug --task "your task here"
```

## Key Implementation Notes

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
- ✓ Screen observation (~470KB base64 per frame)
- ✓ Tool execution (bash, computer control, vault scanning)
- ✓ Observe-reason-act loop (2-3s per iteration)
- ✓ Server prayer invocation
- ✓ Windows console compatibility (ASCII output)
- ✓ Docker containerization
- ✓ Unit test coverage

**Verified Commands**:
```bash
# Boot test (working)
python main.py --task "invoke server prayer"

# Vault scanning (working)
python main.py --task "scan the vault directory"

# With max iterations
python main.py --task "describe screen" --max-iterations 3
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