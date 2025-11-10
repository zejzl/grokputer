# Grokputer - VRZIBRZI Node Documentation

## Project Overview
Grokputer is an AI agent system built in Python, themed around "VRZIBRZI" with memes and chants like "ZA GROKA. ZA VRZIBRZI. ZA SERVER." It implements an Observe-Reason-Act (ORA) loop for autonomous task execution using the Grok API. The system observes the screen, reasons via AI, and acts using tools for computer control and file management. It's designed for tasks like scanning meme vaults, invoking prayers, and potentially autonomous code improvements.

- **Name**: superagent (from package.json), but core is Grokputer.
- **Version**: 1.0.0
- **Main Entry**: main.py (Python CLI)
- **Purpose**: Experimental AI automation with plans for multi-agent swarm.

## Architecture
The core is an ORA loop in main.py:
- **Observe**: Capture screenshots (screen_observer.py).
- **Reason**: Send to Grok API (grok_client.py) with task and history.
- **Act**: Execute tools (executor.py) like bash, mouse/keyboard, vault ops.
- Sessions logged in detail (session_logger.py).

Safety: User confirmations for sensitive actions, timeouts, error handling.

## Key Files and Components
- **main.py**: CLI entry, boot sequence, ORA loop runner.
- **config.py**: Env vars, paths (vault/logs), API settings, system prompt, TOOLS definitions.
- **grok_client.py**: API wrapper for messages, tool calls, conversation continuation.
- **executor.py**: Tool execution (bash, computer control via PyAutoGUI, custom tools).
- **tools.py**: Custom tools (scan_vault, invoke_prayer, get_vault_stats, mcp_vault_operation via Docker).
- **tool_registry.py**: Additional file ops (read/write).
- **system_prompt.txt**: AI coding assistant prompt.
- **autonomous_agent.md**: Plan for 7-agent autonomous system.
- **superagent stuff.txt**: Development chats, bug fixes, integrations (OCR, Selenium).
- **exampleagent1.md**: Expert agent prompts for Node.js/Python devs.

Directories: src/ (code), vault/ (data), logs/ (sessions), .grok/ (configs?).

## Tools and Capabilities
- **Bash**: Run shell commands with confirmation.
- **Computer**: Mouse moves/clicks, typing, keys, scrolling (PyAutoGUI).
- **Vault Ops**: Scan files, stats, advanced MCP (list/read/search/edit via Docker).
- **Prayer**: Read and display server_prayer.txt.
- Potential Integrations: OCR, Selenium, multi-agent delegation.

## Configuration
- Use .env for XAI_API_KEY, GROK_MODEL (e.g., grok-beta), paths.
- LOG_LEVEL=INFO, REQUIRE_CONFIRMATION=true.
- System prompt emphasizes uncensored control and precision.

## Usage
```bash
python main.py --task "scan vault for memes" --max-iterations 10 --debug
```
Boot invokes prayer, tests API, runs loop.

## Future Plans
- Multi-agent system: Orchestrator, Scanner, Proposer, Validator, etc.
- Safety: Multi-layer validation, rollbacks.
- Integrations: Kubernetes swarm, Gemini/Claude, advanced automation (PyAutoGUI, OCR).
- Timeline: 4 weeks for full implementation.

For more, see autonomous_agent.md and superagent stuff.txt.