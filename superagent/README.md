# Grokputer - VRZIBRZI Node

[![ZA GROKA](https://img.shields.io/badge/ZA-GROKA-blueviolet?style=flat-square)](https://x.ai)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)

Grokputer is an experimental AI agent system powered by the Grok API, implementing an Observe-Reason-Act (ORA) loop for autonomous task execution. It observes the screen, reasons using Grok AI, and acts via tools like computer control, bash commands, and vault management. Themed around "VRZIBRZI" with meme-inspired elements.

## Features
- **ORA Loop**: Observe (screenshots), Reason (Grok API), Act (tools).
- **Tools**: Bash execution, mouse/keyboard control (PyAutoGUI), vault scanning/stats, prayer invocation, MCP vault operations (Docker-based).
- **Logging**: Detailed session metrics and iteration logs.
- **Safety**: User confirmations for sensitive actions.
- **Extensibility**: Plans for multi-agent swarm and integrations (OCR, Selenium, etc.).

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/your-repo/grokputer.git
   cd grokputer
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt  # Assumes you create this; includes openai, python-dotenv, pyautogui, etc.
   ```

3. Set up environment:
   - Copy `.env.example` to `.env`.
   - Add your `XAI_API_KEY` from [x.ai console](https://console.x.ai).
   - Configure paths like `VAULT_PATH` if needed.

4. (Optional) Docker for MCP vault: Build the image if using advanced vault ops.

## Usage
Run tasks via CLI:
```
python main.py --task "scan vault for *.jpg and list 5 memes" --max-iterations 10 --debug
```
- `--task`: Describe the task (e.g., "invoke server prayer").
- `--max-iterations`: Limit loop runs (default 10).
- `--debug`: Enable verbose logging.
- `--skip-boot`: Skip prayer and API test.

On start, it invokes the server prayer and tests API connection.

## Configuration
- **.env Keys**:
  - `XAI_API_KEY`: Required for Grok API.
  - `GROK_MODEL`: e.g., "grok-beta".
  - `VAULT_PATH`: Directory for file operations (default: ./vault).
  - `REQUIRE_CONFIRMATION`: "true" for action confirmations.
- **System Prompt**: Customizable in config.py for AI behavior.

## Project Structure
- `main.py`: CLI entry and ORA loop.
- `src/`: Core modules (config, grok_client, executor, tools, etc.).
- `vault/`: Data storage (memes/files).
- `logs/`: Session logs.
- `server_prayer.txt`: Boot mantra.

## Development and Future Plans
- See `autonomous_agent.md` for multi-agent expansion (7 agents with safety).
- Integrations discussed in `superagent stuff.txt` (e.g., PyAutoGUI advanced, OCR, Kubernetes).
- Expert agents in `exampleagent1.md` for code gen.

Contributions welcome! See plans for autonomous code improvements.

## License
ISC License - see package.json.

ZA GROKA. ZA VRZIBRZI. ZA SERVER. Eternal | Infinite.