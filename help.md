# Grokputer Commands & Flags Reference

## Main Entry Point: `python main.py`

### Core Options
- `--task`, `-t` TEXT: Task description for Grokputer to execute (optional: omit for interactive mode)
- `--max-iterations`, `-m` INT: Maximum loop iterations (single-agent mode) [default: 5]
- `--debug`, `-d`: Enable debug logging
- `--skip-boot`: Skip boot sequence
- `--provider`, `-pr` TEXT: AI provider (grok, openai, claude, ollama) [default: grok]
- `--model` TEXT: Specific model to use (provider-dependent)

### Collaboration Mode (Grok + Claude)
- `--messagebus`, `-mb`: Enable collaboration mode (Claude + Grok)
- `--max-rounds` INT: Maximum collaboration rounds [default: 5]
- `--review-mode`, `-r`: Pause after each round for human review

### Swarm Mode (Multi-Agent)
- `--swarm`: Enable multi-agent swarm mode
- `--agents` INT: Number of agents in swarm [default: 3]
- `--agent-roles` TEXT: Comma-separated agent roles [default: coordinator,observer,actor]

### Pantheon Mode (9-Agent Architecture)
- `--pantheon`, `-p`: Enable Pantheon mode (9-agent architecture with validation & learning)

### Analytics & Monitoring
- `--analytics`, `-a`: Enable live analytics and throughput monitoring

### Code Quality
- `--syntax-check`: Run comprehensive syntax and code quality checks
- `--quick-check`: Run fast syntax check (core files only)

## Interactive Mode
Run `python main.py` without arguments to access the interactive menu with these options:
1. Single Agent (Grok only) - Observe-Reason-Act loop
2. Collaboration Mode (Grok + Claude) - Dual AI planning
3. Swarm Mode (Multi-agent) - Async team coordination
4. Pantheon Mode (9-agent) - Full AI orchestration with validation & learning
5. Improver Manual - Run self-improvement on specific session/log
6. Offline Mode - Cached/local fallback (no API, uses vault/KB)
7. Community Vault Sync - Pull/push evolutions and tools
8. Save Game - Invoke progress save script
9. Quit

## Save Game: `python save_game.py`
- `--auto`: Auto-save without prompts
- `--message` TEXT: Custom git commit message
- `--interval` INT: Autosave interval in minutes (runs as daemon)

## Session Viewer: `python view_sessions.py`
- `session_id`: Session ID to view
- `--graph`: Show graph (requires matplotlib)

## Autonomous Security Scanner: `python autonomous.py`

### Scan Command
`python autonomous.py scan <target> [options]`
- `--category` TEXT: Filter by category (security, performance, etc.)
- `--severity` TEXT: Filter by severity (critical, high, medium, low)
- `--output`, `-o` PATH: Save report to JSON file
- `--auto-propose`: Automatically generate proposals for findings
- `--dangerously-skip-permissions`: Skip all permission checks

### Propose Command
`python autonomous.py propose <finding_id> [options]`
- `--finding-file` PATH: JSON file with findings (required)
- `--output`, `-o` PATH: Save proposal to JSON file
- `--dangerously-skip-permissions`: Skip permission checks

### Improve Command
`python autonomous.py improve <target> [options]`
- `--category` TEXT: Filter by category
- `--severity` TEXT: Filter by severity [default: high]
- `--auto-approve-safe`: Auto-approve low-risk proposals
- `--dangerously-skip-permissions`: Skip all permission checks

### Daemon Mode
`python autonomous.py daemon <target> [options]`
- `--interval` INT: Cycle interval in seconds [default: 60]
- `--evolve-chance` FLOAT: Chance of param evolution [default: 0.3]
- `--no-redis`: Disable Redis persistence

## Streamlit Dashboard: `streamlit run streamlit_app.py`
Web-based monitoring interface with live metrics, swarm visualization, and session analysis.

## Docker Commands
- `docker-compose up grokputer`: Run in Docker
- `docker-compose --profile pantheon up grokputer`: Pantheon mode in Docker
- `docker-compose --profile debug up grokputer-vnc`: Debug mode with VNC
- `TASK="scan vault for files" docker-compose run --rm grokputer`: Run specific task

## Testing & Quality
- `python -m pytest tests/`: Run all tests
- `pytest --cov=src tests/`: Run tests with coverage
- `python main.py --syntax-check`: Comprehensive code quality checks
- `python main.py --quick-check`: Fast syntax check

## Build Scripts
- `./build-mcp.sh` or `build-mcp.bat`: Build MCP server
- `python grokputer_server.py`: Run MCP server

## Example Usage Patterns

### Single Agent Mode
```bash
python main.py --task "describe what's on screen"
python main.py --task "list all PDF files in vault" --max-iterations 3
python main.py --provider openai --model gpt-4 --task "analyze data"
python main.py --provider claude --model claude-3-opus-20240229 --task "write code"
python main.py --provider gemini --model gemini-1.5-flash --task "quick analysis"
python main.py --provider ollama --model llama2 --task "chat locally"
```

### Collaboration Mode
```bash
python main.py -mb --task "design REST API with best practices"
python main.py --messagebus --task "review main.py for improvements" --max-rounds 3
python main.py -mb -r --task "analyze project structure" --max-rounds 5
```

### Swarm Mode
```bash
python main.py --swarm --task "scan vault, analyze files, create summary"
python main.py --swarm --agent-roles "observer,actor" --task "take screenshot"
python main.py --swarm --debug --task "complex task"
```

### Pantheon Mode
```bash
python main.py --pantheon --task "execute complex task with safety validation"
python main.py -p --task "scan files and create report" --debug
```

### MAF Mode (Multi-Agent Framework)
```bash
# Load custom MAF configuration
python main.py --maf-config src/collaboration/configs/test_optimization_duo.json --task "optimize code"

# Use multiple providers
python main.py --providers grok,claude --task "collaborative analysis"

# Backward compatibility test
python main.py -mb --task "test MAF features"
```

#### MAF Configuration Files
Create custom configs in `src/collaboration/configs/`:
```json
{
  "agents": [
    {
      "name": "optimizer",
      "provider": "grok",
      "role": "code_optimizer",
      "model": "grok-4-fast-reasoning"
    },
    {
      "name": "reviewer",
      "provider": "claude",
      "role": "code_reviewer",
      "model": "claude-3-sonnet-20240229"
    }
  ],
  "workflow": "optimization_pipeline",
  "max_rounds": 3
}
```

#### MAF Troubleshooting
- **Config not found**: Ensure config file exists in `src/collaboration/configs/`
- **Provider errors**: Check API keys in `.env` for all specified providers
- **Workflow failures**: Verify agent roles match expected workflow steps
- **Performance issues**: Reduce max_rounds or use fewer agents

### Autonomous Security
```bash
python autonomous.py scan src/
python autonomous.py scan src/ --category security --severity high
python autonomous.py scan src/ --auto-propose --dangerously-skip-permissions
python autonomous.py improve src/grok_client.py
python autonomous.py daemon src --auto-propose --replicas 3 --analytics
```

### Autosave
```bash
python save_game.py --auto
python save_game.py --interval 15  # Every 15 minutes
```

### Session Analysis
```bash
python view_sessions.py session_12345
python view_sessions.py session_12345 --graph
```

## Notes
- Most commands support `--debug` for verbose logging
- Pantheon mode includes advanced features like conflict resolution, rollback, and meta-reasoning
- Swarm mode uses async coordination with load balancing
- Autonomous mode can run as daemon for continuous monitoring
- All modes support analytics with `--analytics` flag</content>
<parameter name="filePath">help.md