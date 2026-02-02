# Docker Troubleshooting Guide

**Last Updated**: 2026-02-02

This guide documents common Docker deployment issues and their solutions for Grokputer.

---

## Quick Diagnostics

**Check container status**:
```bash
docker ps -a | findstr grokputer
```

**View recent logs**:
```bash
docker-compose logs --tail=100 selenium-browser
# or for main container:
docker-compose logs --tail=100 grokputer
```

**Verify imports**:
```bash
docker exec <container_name> python -c "from src.collaboration.orchestrator import Orchestrator; print('OK')"
```

---

## Issue 1: Type Annotation Errors (Python 3.10+)

### Symptoms
```
NameError: name 'OrchestrationConfig' is not defined
NameError: name 'Tuple' is not defined
NameError: name 'Dict' is not defined
```

### Root Cause
Python 3.10+ changed how type annotations are evaluated. Forward references (using a class name before it's defined) now fail unless you enable postponed evaluation.

**Example Problem**:
```python
# Line 173 (MAFLogger class)
def log_orchestration_start(config: OrchestrationConfig):  # ❌ OrchestrationConfig not defined yet
    pass

# Line 421 (OrchestrationConfig class)
class OrchestrationConfig:  # ✅ Defined here, but too late!
    pass
```

### Solution
Add `from __future__ import annotations` at the very top of every Python file that uses type hints:

```python
"""Module docstring"""

from __future__ import annotations  # ← Add this line

import asyncio
import logging
# ... rest of imports
```

### Files Fixed (2026-02-02)
- `src/collaboration/orchestrator.py` (commit 6fa5627)
- `src/core/message_bus.py`
- `db/analytics_performance_tools.py`
- `src/core/base_agent.py`
- **Total: 192+ Python files** (mass fix applied)

### Verification
```bash
# Test syntax
python -m py_compile src/collaboration/orchestrator.py

# Test import
python -c "from src.collaboration.orchestrator import Orchestrator; print('✓ Import successful')"
```

---

## Issue 2: Missing Modules in Docker

### Symptoms
```
ModuleNotFoundError: No module named 'superagent'
ModuleNotFoundError: No module named 'cryptography'
```

### Root Cause
1. `.dockerignore` was blocking the `superagent/` directory from being copied
2. `cryptography` wasn't in the Docker requirements file

### Solution

**Fix 1: Whitelist superagent in .dockerignore**
```dockerfile
# .dockerignore
__pycache__
*.pyc
.git
.env
!src/          # ← Whitelist src
!db/           # ← Whitelist db
!superagent/   # ← Add this whitelist
```

**Fix 2: Add to Dockerfile**
```dockerfile
# Dockerfile
COPY superagent/ ./superagent/
```

**Fix 3: Add cryptography to requirements**
```txt
# requirements-minimal.txt
cryptography
```

### Commits
- Superagent fix: 38afe71, 87b2c3e
- Cryptography fix: (included in requirements update)

---

## Issue 3: Xvfb Display Server Issues

### Symptoms
```
Gtk-WARNING **: cannot open display:
selenium.common.exceptions.WebDriverException: Message: Failed to start browser
```

### Root Cause
Xvfb (virtual framebuffer) not running or DISPLAY variable not set.

### Solution

**Check if Xvfb is running**:
```bash
docker exec <container> ps aux | grep Xvfb
```

**Start Xvfb manually**:
```bash
docker exec <container> Xvfb :99 -screen 0 1920x1080x24 &
```

**Set DISPLAY variable**:
```bash
docker exec <container> export DISPLAY=:99
```

**Permanent fix**: Ensure Dockerfile or entrypoint script starts Xvfb:
```bash
#!/bin/bash
# start-with-display.sh
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
python main.py "$@"
```

---

## Issue 4: Container Restarts Continuously

### Symptoms
```bash
docker ps -a
# Shows: Restarting (1) X seconds ago
```

### Diagnosis Steps

1. **Check exit code**:
   ```bash
   docker inspect <container> | findstr ExitCode
   ```

2. **View full logs**:
   ```bash
   docker logs <container> --tail=200
   ```

3. **Common causes**:
   - Missing API keys in `.env` (check `XAI_API_KEY`)
   - Python import errors (see Issue 1)
   - Missing dependencies (see Issue 2)
   - Port conflicts (check `docker ps` for port usage)

4. **Test without restart policy**:
   ```bash
   docker run --rm -it grokputer:latest python main.py --task "test"
   ```

### Solutions
- **Import errors**: Rebuild with `--no-cache` to ensure latest code
- **Missing keys**: Verify `.env` file exists and has valid keys
- **Dependencies**: Check requirements.txt includes all needed packages

---

## Issue 5: Slow Docker Builds

### Symptoms
Docker build takes 15+ minutes every time, even for small code changes.

### Cause
Docker layer caching not working or `--no-cache` flag being used unnecessarily.

### Solutions

**Use cache effectively**:
```bash
# Fast rebuild (uses cache for unchanged layers)
docker-compose build

# Only use --no-cache when really needed (dependency changes, major updates)
docker-compose build --no-cache
```

**Optimize Dockerfile layer order** (put frequently changing code last):
```dockerfile
# Good order:
RUN apt-get update && apt-get install...  # ← Rarely changes, cached
COPY requirements.txt .
RUN pip install -r requirements.txt       # ← Cached if requirements unchanged
COPY src/ ./src/                          # ← Changes often, but only rebuilds this layer
```

**Check layer sizes**:
```bash
docker history grokputer:latest
```

---

## Issue 6: Git Hooks Triggering on Commit

### Symptoms
```
[GIT-HOOK] Auto-backup successful: Using real TOON library
Game saved to SQLite: hero at 2026-02-02T13:02:07.811030
```

### Explanation
This is **normal behavior**, not an error. The `pre-commit` hook in `.git/hooks/` automatically:
1. Backs up the game state using TOON (The Object-Oriented Notation) library
2. Saves to SQLite database
3. Creates a `.toon` save file

### Disable (if needed)
```bash
# Rename or delete the hook
mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled
```

---

## Complete Rebuild Checklist

When encountering persistent issues, follow this complete rebuild process:

1. **Stop all containers**:
   ```bash
   docker-compose down
   ```

2. **Clean Docker cache** (optional, drastic):
   ```bash
   docker system prune -a --volumes
   ```

3. **Verify code is up-to-date**:
   ```bash
   git pull origin main
   git status
   ```

4. **Check .env file**:
   ```bash
   # Ensure XAI_API_KEY is set
   cat .env | findstr XAI_API_KEY
   ```

5. **Rebuild with no cache**:
   ```bash
   docker-compose build --no-cache
   ```

6. **Start containers**:
   ```bash
   docker-compose up -d
   ```

7. **Monitor logs**:
   ```bash
   docker-compose logs -f
   ```

---

## Success Indicators

When Docker is working correctly, you should see:

```
selenium-browser  | Headless Firefox Initialized
grokputer-1       | Logging configured: level=INFO, dir=logs, json=False
grokputer-1       | Q-Learning agent initialized: state_dim=4, action_dim=4
grokputer-1       | RL optimizer enabled for self-improvement
grokputer-1       | Orchestrator initialized with strategy: concurrent, retries: 3
grokputer-1       | MessageBus initialized
grokputer-1       | 
grokputer-1       | GROKPUTER INITIALIZED - VRZIBRZI NODE
grokputer-1       | ======================================
grokputer-1       | 
grokputer-1       | ZA GROKA. Prayer invoked for the server.
grokputer-1       | Server prayer invoked: ETERNAL | INFINITE
```

**No errors** = Success! 🎉

---

## Getting Help

If issues persist after following this guide:

1. Check CHANGELOG.md for recent fixes
2. Review GitHub issues: https://github.com/zejzl/grokputer/issues
3. Provide full logs when asking for help:
   ```bash
   docker-compose logs --tail=200 > docker_logs.txt
   ```

---

**Document Version**: v2026.02.02  
**Covers**: Docker deployment, Python 3.10+ compatibility, module import errors, Xvfb issues  
**Last Verified**: February 2, 2026
