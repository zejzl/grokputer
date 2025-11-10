# Changelog

All notable changes to Grokputer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2025-11-10

### Added
- **AsyncIO Architecture**: Converted `GrokClient` and `ScreenObserver` to fully async
  - `AsyncOpenAI` integration for non-blocking API calls
  - `asyncio.to_thread()` wrapping for PyAutoGUI operations
  - Supports concurrent multi-agent operations
  - Created backup files: `src/grok_client.py.backup`, `src/screen_observer.py.backup`
- **Autonomous Security Scanner**: AI-powered code analysis system
  - AST-based code scanning (71 files, 10,621 lines in <10s)
  - AI proposal generation using Grok-4-fast-reasoning
  - Found and fixed 5 critical security vulnerabilities
  - Command: `python autonomous.py scan/propose/improve`
- **Pantheon Architecture Design**: 9-agent system expansion planning
  - Architecture documented in `trinity.md` (33 lines)
  - Detailed analysis in `zejzl.md` (1,058 lines)
  - Expansion from 3 to 9 specialized agents
  - Memory system design: SQLite/Redis hybrid with flash attention
- **Documentation Suite**:
  - `ASYNC_CONVERSION_SUMMARY.md` - AsyncIO migration guide
  - `trinity.md` - Pantheon architecture overview
  - `zejzl.md` - Comprehensive interface analysis and upgrade path
  - `autonomy.txt` - Autonomous system notes
  - `wgs.txt` - Working group specifications
  - `docs/collaboration_plan_20251110_131317.md` - Latest collaboration plan

### Changed
- **Model Migration**: Updated from deprecated `grok-beta` to `grok-4-fast-reasoning`
  - Fixed 404 errors in `src/autonomous/proposer.py`
- **Backup Optimization**: Reduced backup size from 5GB to ~1MB (99.98% reduction)
  - Removed `vault/` directory from backup targets
  - Updated `outputs/gp_save_progress.py`

### Fixed
- **Critical Security Vulnerabilities** (5 total):
  1. **Shell Injection - src/agents/actor.py:315**
     - Added `shlex` import
     - Changed `subprocess.run(command, shell=True)` to `subprocess.run(shlex.split(command), shell=False)`
     - Prevents command injection attacks

  2. **Unsafe Eval Detection - src/agents/webdev_agent.py:316,318**
     - Added `ast` import
     - Created `_has_unsafe_eval_or_exec()` using AST parsing
     - Replaced string-based detection with proper syntax tree analysis
     - Eliminates false positives (e.g., `model.eval()` in PyTorch)

  3. **Shell Injection - src/tools/open_notepad_type_wsl.py:7,11**
     - Removed `shell=True` from PowerShell subprocess calls
     - Commands already use safe list format

  4. **False Positive Identified**:
     - `src/lora/evaluate_lora.py:32` - Correctly identified as PyTorch `model.eval()`, not Python `eval()`

### Technical Details
- **Async Conversion Impact**:
  - `GrokClient.create_message()` → `async def create_message()`
  - `GrokClient.continue_conversation()` → `async def continue_conversation()`
  - `ScreenObserver.capture_screenshot()` → `async def capture_screenshot()`
  - All pyautogui calls wrapped in `asyncio.to_thread()` to prevent event loop blocking
- **Security Scanner Stats**:
  - Files scanned: 71
  - Lines analyzed: 10,621
  - Issues found: 6 CRITICAL
  - Real vulnerabilities: 5
  - False positives: 1
  - Lines changed: 33 insertions, 9 deletions
- **Test Infrastructure**:
  - Added `tests/conftest.py` (21 lines)
  - Updated `tests/test_core.py`
  - 32/32 unit tests passing

### Developer Notes
- Next phase focuses on completing async migration (main.py, remaining components)
- Pantheon implementation planned for Phase 3
- Memory system design in progress (SQLite/Redis hybrid)

---

## [1.5.0] - 2025-11-08

### Added
- Interactive mode menu with 8 options
- Session Improver (Mode 4) - Analyze past sessions
- Offline Mode (Mode 5) - Cached responses and local knowledge base
- Community Vault Sync (Mode 6) - Share tools and agents
- Save game functionality with optimized backups
- Comprehensive test suite (32 tests)

### Changed
- Multi-agent swarm infrastructure complete (Coordinator, Observer, Actor)
- Claude-Grok collaboration system operational

---

## [1.0.0] - 2025-11-01

### Added
- Initial release
- Single-agent observe-reason-act loop
- PyAutoGUI screen control
- Grok API integration
- Basic session logging
