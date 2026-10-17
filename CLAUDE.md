# CLAUDE.md - Grokputer Technical Reference for Claude AI

**Last Updated**: 2026-10-17
**Project**: Grokputer - AI-Powered Computer Control & Multi-Agent System
**Status**: Active development. Full test suite green (629 passed, 11 skipped). Known runtime bugs remain (see Known Issues). Session notes and TODO: `nightowl_2026-10-15.md`.

Claims below marked "(unverified)" come from older notes and have not been re-measured.

## Overview

Grokputer is a Python multi-agent system that combines screen capture/vision, LLM reasoning, and a message-bus based agent swarm. It grew from a single observe-reason-act loop into a 9-agent "Pantheon", a multi-provider collaboration layer (MAF), and an in-progress workflow engine (GG Framework).

## Architecture Status

- **MessageBus** (`src/core/message_bus.py`): async priority queue with pub/sub. Measured 2026-10-15 (Python 3.14, Windows, single process, 20k msgs): 51k-105k msg/s end-to-end, 0% loss; unloaded send+receive p50 0.007 ms, p99 0.010 ms. The old 18,384 msg/sec figure is conservative. `tests/core/test_message_bus_throughput.py` is a script (`python tests/core/test_message_bus_throughput.py`), not a pytest test, and its per-consumer rate divides by a fixed 10 s window, so only its producer rate (~370k msg/s, enqueue only) and loss rate are meaningful.
- **Pantheon** (9 agents): Observer, Reasoner/Coordinator, Actor, Validator, Learner, Memory, Executor, Analyzer, Improver. Implemented in `src/agents/`.
- **MAF** (`src/collaboration/`): multi-provider collaboration with weighted-voting consensus, provider registry/pool, RL optimizer. Providers: xAI Grok, Anthropic Claude, OpenAI, Google Gemini, Ollama.
- **Multi-modal**: `src/vision_processor.py`, `src/audio_processor.py`, `src/multimodal_processor.py`, `src/knowledge_graph.py`. Audio tests are skipped on Python 3.13+ because the `audioop` module was removed.
- **GG Framework** (`src/workflow/`): implemented, not just planned. Engine, state, flow DSL, healing, learning, Pantheon/MessageBus adapters, and nodes (ai, asana, conditional, http, notion, slack, transform). `WorkflowEngine.execute(workflow)` returns status/data/state/nodes_executed and honors `timeout`; `Workflow.validate()` detects cycles; `TransformNode` supports jq-style paths (`.a.b`, `.items[0].id`). `main.py --workflow FILE` runs a YAML/JSON definition (`src/workflow/loader.py`, example `workflows/hello.yaml`); the engine does not yet gate nodes on a conditional's `branch`.
- **Phase 4** (self-improvement/RL): started; `src/self_improvement/`, `src/agents/learner.py`, `src/collaboration/rl_optimizer.py`.
- **Distributed swarm**: Docker Swarm + Redis pub/sub, Prometheus (9101), Grafana (3000), Streamlit (8501). Speedup and effectiveness figures in older notes are unverified.

## Key Files

- `main.py` - CLI entry point (click). `autonomous.py` - daemon/swarm orchestration.
- `src/core/` - `message_bus.py`, `base_agent.py`, `action_executor.py`
- `src/agents/` - agents. NOTE: many exist in two versions (`observer.py` and `observer_agent.py`, same for actor, executor, analyzer, improver; plus `imrover_agent.py`, a typo copy). Check which one is actually imported before editing.
- `src/collaboration/` - `provider_registry.py`, `provider_pool.py`, `consensus_manager.py`, `orchestrator.py`, `multi_provider_coordinator.py`, `rl_optimizer.py`
- `src/memory/` - `hierarchical_memory.py`, `backends/redis_store.py`, `backends/pinecone_store.py`
- `src/observability/` - `session_logger.py`, `deadlock_detector.py`; `dashboard.py` - Streamlit UI
- `src/safety/` - `godmode_protocols.py`, `code_scanner.py`
- `token_haze.py` - interactive onboarding tool (token counting via tiktoken, system status)
- `save_game.py`, `view_sessions.py` - state saves and session viewing

## CLI (verified against main.py)

Options: `--task`, `--max-iterations`, `--max-rounds`, `--debug`, `--skip-boot`, `--provider`, `--model`, `--swarm`, `--agent-roles`, `--messagebus`, `--pantheon`, `--providers`, `--maf-config`, `--review-mode`, `--analytics`, `--agent-name`, `--limit`, `--performance`, `--list-models`, `--syntax-check`, `--quick-check`, `--mcp`, `--todo-daemon`, `--distributed`, `--process-id`, `--connect-to`, `--grok4git`, `--execute`, `--workflow`, `--workflow-input`.

```bash
python main.py --task "your task"
python main.py --pantheon --task "complex task"
python main.py --providers grok,claude --task "collaborative analysis"
python main.py --messagebus --task "messagebus task"
python main.py --workflow workflows/hello.yaml   # GG workflow from YAML/JSON (see src/workflow/loader.py)
python autonomous.py daemon src --auto-propose --replicas 3
streamlit run dashboard.py
```

The short flags `-gp` and `-mb` mentioned in older docs are not defined in `main.py`. Running `main.py` with no arguments opens the interactive menu.

## Configuration

Copy `.env.example` to `.env` (gitignored). Main variables: `XAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROK_MODEL`, `XAI_BASE_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_URL`, `REQUIRE_CONFIRMATION`, `VAULT_PATH`, `LOG_LEVEL`, `LOG_FILE`.

## Testing

**Current run (2026-10-15, Python 3.14.7, `pytest tests -q --continue-on-collection-errors`)**: 629 passed, 11 skipped, 0 failed, 0 errors as of 2026-10-17 (2 PyAutoGUI action_executor tests fail if the real mouse sits in a screen corner: fail-safe). (Before the 2026-10-15 fixes: 299 passed, 13 failed, 12 collection errors.)

How the suite is set up:
- `tests/conftest.py` sets a placeholder `XAI_API_KEY` (a real one in the environment is left alone), because `src/config.py` raises at import time without a key. Tests mock all network calls.
- `pyproject.toml` uses `--strict-markers`; registered markers: `slow`, `integration`, `stress`, `windows`, `phase1`. Register any new marker there.
- `tests/workflow/test_healing.py` tests `WorkflowHealer` (magic healing disabled for determinism).
- `tests/observability/test_deadlock_detector.py` tests the restored original `DeadlockDetector` API.

Skipped (11):
- `tests/test_hyde_complete.py`: Pinecone not installed; also `huggingface-hub` must match the pin in `requirements.txt` (0.36.0) for `transformers` to import.
- `tests/test_multimodal_processor.py`, `tests/test_vision_integration.py`: Python 3.13+ removed `audioop`.
- `tests/agents/test_coordinator.py` (6): marked "written for a different Coordinator API".
- `tests/test_screen_observer.py` (2): `ScreenObserver.screenshot_to_base64` is async but tests call it synchronously.

Commands:
```bash
pytest tests/collaboration --cov=src/collaboration -v
pytest tests -q --continue-on-collection-errors
```

## Known Issues and Pending Work

1. Old xAI and Google/Gemini keys were committed in `grokputerfirstversionbackup/xaikey.txt` and remain in git history. They are already deactivated and deleted (confirmed by the user), so no rotation is needed. The files are now untracked and ignored (also `ULTIMATE_KEY.md`); scrubbing history is optional.
2. `src/grok_client.py`: Claude/Gemini API paths are unit-tested but not exercised live; `chat()` falls back to the next configured provider when one returns None or raises (fixed 2026-10-17); it returns None if all fail. Test provider `claude-cli` (`PRIORITY_PROVIDER=claude-cli`, optional `CLAUDE_CLI_MODEL`) runs `claude -p` on the subscription login (text only; strips `ANTHROPIC_API_KEY` from the subprocess env).
3. Token usage is recorded per agent tag; `--pantheon` prints a TOKEN USAGE table at the end (only the Coordinator's calls so far: ~870 in / 850-1560 out per decomposition).
3b. `--pantheon` is plan-only by default: decompose -> safety review of each subtask -> report (prints PLAN and TOKEN USAGE). `--pantheon --execute` also runs `actor` subtasks one at a time: the LLM proposes ONE command, the validator checks it, you confirm at the prompt, then `ActionExecutor.execute_bash` runs it (no shell; metacharacters rejected). Non-actor subtasks are reported as skipped. Executor/Analyzer/Improver are not used by this flow. Known limits: validator safety patterns are crude substrings (the word "format" flags a subtask), only the first 300 chars of command output are shown. `ExecutorAgent` now uses `execute_async` (fixed 2026-10-17) but is covered only by unit tests, not a live run.
3c. MAF mode (menu option 9, `--providers`) now calls real models. Providers: `grok`, `claude`, `claude-cli`, `gemini`, `openai`, optionally with a model (`claude-cli:haiku,claude-cli:sonnet` lets two Claude models collaborate when only the subscription is available). `MAF_USE_MOCK=1` restores canned mock responses. The orchestrator needs at least 2 providers; the default preset is `grok_claude_dual` (roles analyzer/critic; the old `primary_agent`/`secondary_agent` roles failed the schema). Each round costs one call per provider. Limits: same-family providers share one sender label (`AgentRole`), `success` means consensus was reached, RL provider selection logs an unhashable-key warning and falls back to the default, and `openai`/`gemini` are untested live.
4. (done 2026-10-17) `shell=True` removed from `improve_swarm.py` (pure-Python edit, argv test run) and `src/tools.py`. Guard: `tests/test_shell_hardening.py` fails on any `shell=True` call or bare `except:` in `main.py`, `improve_swarm.py`, `autonomous.py`, `src/`. `improve_swarm.py` now reverts the edit from its backup when `test_fix` fails (`revert_edit`).
5. (done) `main.py` menu exits cleanly on EOF/Ctrl+C via `_ask()`.
6. (reviewed 2026-10-17, deliberately not merged) The `observer`/`observer_agent`, `actor`/`actor_agent`, `analyzer`/`analyzer_agent`, `improver`/`improver_agent` pairs are different implementations with different message protocols, not copies. `main.py` runs the `*_agent.py` versions; the plain ones use the Pantheon `subtask` protocol and have no live consumer except `limbo_daemon.py` (Observer). Both sets are now constructible and tested. Map and rationale: `src/agents/__init__.py`. Plain `Actor` now uses `src/core/command_safety.py` (ActionExecutor's metacharacter rule plus a blocked-program list); it is still not wired into any live flow. `MessageBus.send_and_wait` now exists (the plain Improver needed it). `epic_win.py` (stale one-shot script with wrong constructor calls) moved to `scripts/legacy/`.
7. (done) `node_modules/`, `saves/`, `backups/`, `logs/` untracked and ignored; root `fix_*` scripts moved to `scripts/legacy_fixes/`.
8. (done) workflow engine wired into `main.py --workflow`. Also: Two agents: `Taskmaster` (`src/agents/taskmaster.py`, bus id `task_planner`) is the analytics planner (`suggest`, `next_step`); `TaskMaster` (`src/agents/task_master.py`, bus id `taskmaster`) is the task board that `BaseAgent`'s task client talks to (restored from commit 37db194, where it had been overwritten; the client now waits for replies via `send_and_wait`; task dependencies are now enforced). `demo_task_management.py` and `test_task_client_integration.py` need live LLM agents and were not run; `ActorAgent` file_create/file_edit are unsupported (ActionExecutor has no file ops).

Fixed 2026-10-17: `db/integrated_tools.py` removed (strict duplicate of `src/tools/toolkit.py`; the toolkit now has its real `invoke_prayer`). The unreferenced staging files in `db/` (`swarm_analytics_enhancement*.py`, `temp_merge.py`, `async_tool_wrappers.py`, `updated_*`, `test_swarm*.py`, `test_analytics.py`) moved to `scripts/legacy/db/`; `db/` keeps the live `config.py` and `analytics_performance_tools.py`. `analytics_performance_tools` (strings, MAF metrics) and the toolkit's analytics (dicts) are different APIs, do not merge blindly. the old `src/tools.py` was shadowed by the `src/tools/` package and had spliced function bodies (`get_vault_stats` had no `def`, `generate_code`/`execute_tool` bodies were swapped, a stub `analytics_query` overrode the real one). It is now `src/tools/toolkit.py`, re-exported lazily from `src.tools` (`from src.tools import bash, search, execute_tool, ...` works). `generate_code` rejects filenames that escape the sandbox dir. Tests: `tests/test_tools_package.py`.

Fixed 2026-10-15: `asyncio==4.0.0` removed from requirements (it shadows the stdlib module); `shell=True` removed from the executor and MCP server; deadlock detector API restored (callers in `main.py`, coordinator, actors and lifecycle manager use `register_agent`/`update_activity`); HTTP node now interpolates `{{vars}}` inside dict bodies.

## Development Guidelines

- Readable, PEP 8 code; no hardcoded keys; validate inputs; `shell=False` for subprocess.
- Full runnable code, no placeholders. Async fixtures and mocks for external services in tests.
- No emojis in code (Windows console compatibility).
- Prefer Python dicts/YAML over JSON for configs.
- Use `ripgrep` for text search and `ast-grep` for structural changes; prefer dedicated tools over shell one-liners.
- Test risky changes in Docker. Back up state before large changes (`python save_game.py --auto`).

## Docker

```bash
docker-compose up grokputer
docker-compose --profile pantheon up        # with Redis
docker-compose --profile debug up grokputer-vnc   # VNC on 5900
docker-compose up mcp-server
```

Base image `python:3.11-slim`, Xvfb display `:99`, persistent Redis volume.

## Resources

`README.md`, `grok.md`, `DEVELOPMENT_PLAN.md`, `CHANGELOG.md`, `help.md`, `GG_TASK_PLAN.md`. Remote: https://github.com/zejzl/grokputer (branch `main`).
