# Grokputer Vault

The vault is the central knowledge base for Grokputer—stores user data, community contributions, session history, and backups. It enables offline mode, vault sync, and persistent learning.

## Structure
- **community/**: Shared agents, tools, configs (pulled/pushed via sync).
- **git_resources/**: Cloned repos (e.g., ollama, semtools).
- **session_history.txt**: Past executions for offline analysis.
- **redis_backup.json**: Redis dump (keys/values from memory/learning). Auto-backed up via `save_game.py --auto`. Format: `{ "backup_timestamp": "...", "total_keys": 138, "data": { "key": "value" } }`. Restore: Load into Redis with a script (e.g., `redis-cli --pipe < redis_backup.json` for simple keys).
- **Other**: Notes (e.g., agi.md, plan.txt), images, unsorted files.

## Usage
- **Sync**: `python main.py` → Mode 7 (Pull/Push/Both) to share with community.
- **Offline Mode**: Uses vault for cached responses (Mode 6).
- **Backup Redis**: Run `python backup_redis.py` to update `redis_backup.json`. Includes 138+ keys (episodes, patterns, etc.)—some complex types serialized.
- **Manual Restore**: For Redis: `cat redis_backup.json | jq -r '.data | to_entries[] | "\(.key) \(.value)"' | redis-cli --pipe` (adapt for hashes/lists).

**Note**: Vault not auto-backed in save_game.py (manual: `tar czf vault_backup.tar.gz vault/`). Keep secure—contains seeds, history.

ZA GROKA. Vault: Eternal Knowledge Repository.