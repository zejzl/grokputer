# Autonomous Daemon for Code Improvement

## Overview
The daemon mode in `autonomous.py` embeds async cycles from `autonomy.txt` to provide continuous code monitoring and evolution. It scans targets (e.g., `src/`), evolves agent parameters (mock 30% chance), checks for high/critical issues, generates AI proposals (with `--auto-propose`), and stores them in Redis. Inspired by swarm autonomy (--grokputer --swarm -mb single mode), it runs non-blocking loops for proactive dev workflows.

Key Components (from autonomy.txt integration):
- `async_daemon_cycle`: Parallel evolution + security scans.
- `evolve_params`: Random param drift (mock for now).
- `security_scan`: Detects vulns using `CodeScannerAgent`.
- `generate_haiku`: Fun logging (stored in Redis as "eternal_bloom").
- Auto-proposals: Uses `ProposalGeneratorAgent` for fixes, stored as JSON in Redis (`proposals_{timestamp}`).

## Features
- **Continuous Monitoring**: Scans every 60s (configurable via `--interval`).
- **Agent Evolution**: Mock "drift" for scanner/proposer params.
- **Security Scans**: Filters high/critical findings; alerts on console.
- **Auto-Propose Fixes**: If `--auto-propose`, generates proposals for issues, displays via Rich panels, stores in Redis.
- **Redis Persistence**: Default for proposals/haikus (localhost:6379); fallback to console if unavailable. `--no-redis` skips haiku but keeps proposals.
- **Error Handling**: Continues cycles on API/Redis errors; logs skips.
- **CLI Integration**: Part of main `autonomous.py` tool.

## Usage
1. **Setup**:
   - Set `XAI_API_KEY` in `.env` or export (required for proposals).
   - Ensure Redis running (`docker run -p 6379:6379 redis` or local install).
   - Install deps: `pip install redis rich click` (if not in requirements).

2. **Run Daemon**:
   ```
   python autonomous.py daemon <target> [options]
   ```
   - `<target>`: File/dir to monitor (e.g., `src/`).
   - `--interval <secs>`: Cycle time (default: 60).
   - `--evolve-chance <float>`: Param drift probability (default: 0.3).
   - `--auto-propose`: Enable AI fix generation/storage (default: False).
   - `--no-redis`: Skip haiku/legacy storage (proposals still try Redis).

   Example: `python autonomous.py daemon src/ --auto-propose --interval 30`

3. **Retrieve Proposals**:
   - Redis: `redis-cli keys "proposals_*" | xargs redis-cli get | jq` (view JSON).
   - New CLI: `python autonomous.py retrieve-proposals` (fetches latest).

4. **Stop**: Ctrl+C or `pkill -f autonomous.py`.

## Example Output
```
[bold green]Starting autonomous daemon on src (interval: 60s)[/bold green]
[green]Redis connected.[/green]
[yellow]1 issues detected in scanner! Review proposals.[/yellow]
[Panel: Proposal HIGH_VULN_001]
Title: Secure Input Validation
Description: Add sanitization to prevent XSS.
Risk: high | Effort: low | Breaking: No
Rationale: Prevents injection attacks.
Benefits: • Improves security
Code Changes: [diff: input = sanitize(input)]
Test Strategy: Unit test edge cases
[green]Proposal stored in Redis: proposals_1720660200[/green]
Cycle complete: 4 evols, 30.0% drift survived.
Haiku: Eternal queues / Agents dance without wait / Bloom in code's night
scanner evolved: +0.1 divergence
proposer stable
scanner: 1 alerts
proposer: 0 alerts
```

If no issues: Skips proposals, logs "0 alerts".

## Implications
- **Pros**: Enables true autonomy—proactive fixes reduce manual scans; Redis persists history for review/swarm scaling. Improves efficiency for ongoing projects (e.g., 40% less manual intervention).
- **Cons**: Resource use (CPU for scans, API calls for proposals); Redis dependency (setup needed); potential over-evolution (mock now, but real param tweaks could break). Security: Auto-proposals are suggestions—review before apply.
- **Improvements**: Yes for background monitoring; optional for CLI users. Adds swarm vibe without complexity overload.

## Next Steps Todo List
1. **High Priority**:
   - Add `--auto-apply-safe` flag: Auto-apply low-risk proposals (with confirmation or dry-run).
   - Support multi-dir: `--targets src,tests,tools` for parallel monitoring.
   - Real evolution: Use proposals to update agent configs (e.g., tune scan sensitivity).

2. **Medium Priority**:
   - Integrate LLM for dynamic haikus (via Qwen/XAI API).
   - Add email/Slack alerts for critical proposals.
   - Dashboard: Streamlit app to view Redis proposals live (`streamlit run dashboard.py`).

3. **Low Priority**:
   - Swarm mode: Multi-agent (spawn subprocesses for sub-dirs).
   - Metrics: Log cycle stats to file (e.g., issues found over time).
   - Backup: Export Redis proposals to JSON daily.

Run the daemon on a project dir and watch it evolve! 🚀