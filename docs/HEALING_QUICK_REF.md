# Self-Healing & Revival Quick Reference

**Last Updated**: 2025-11-17
**Status**: Production Ready

## Overview

Grokputer has 3-layer automatic recovery:
1. **Workflow Healing** - Fixes broken workflow nodes
2. **Agent Revival** - Restarts crashed agents
3. **Learning** - Remembers and applies fixes

---

## Workflow Healing

**File**: `src/workflow/healing.py`

### Basic Usage

```python
from src.workflow.healing import SelfHealingSystem

healing = SelfHealingSystem(improver_agent, message_bus)

# Auto-heal a failed node
result = await healing.heal_node_failure(node, context, error)
```

### Strategies (in order)

1. **RETRY** - Try again with backoff (3x max)
2. **FALLBACK** - Use backup node if configured
3. **SKIP** - Skip failed node, continue workflow
4. **REPLACE_DATA** - Use safe defaults
5. **RECONFIGURE** - Auto-adjust settings (e.g., timeouts)
6. **DELEGATE_TO_AGENT** - Send to ImproverAgent
7. **CIRCUIT_BREAKER** - Stop calling failing nodes

### Circuit Breaker

- **Closed** → normal operation
- **Open** → too many failures (5+), stop calling
- **Half-Open** → testing recovery after 60s

### Configuration

```python
config = {
    "max_retries": 3,
    "retry_delay": 1.0,
    "exponential_backoff": True,
    "circuit_breaker_threshold": 5,
    "circuit_breaker_timeout": 60,
    "pattern_detection_threshold": 3
}
```

### Register Fallbacks

```python
# Set backup node for a failing node
healing.register_fallback("failing_node_id", backup_node)

# Custom recovery strategies
healing.set_recovery_strategies("node_id", [
    HealingStrategy.FALLBACK,
    HealingStrategy.RETRY
])
```

### Get Stats

```python
stats = healing.get_stats()
# Returns: total_failures, total_heals, success_rate, circuit_breakers
```

---

## Agent Revival

**File**: `src/core/agent_lifecycle_manager.py`

### Basic Usage

```python
from src.core.agent_lifecycle_manager import AgentLifecycleManager

lifecycle = AgentLifecycleManager(config)

# Register agent for monitoring
await lifecycle.register_agent(agent)

# Start monitoring
await lifecycle.start_all_agents()

# Manual restart
await lifecycle.restart_agent("agent_id", reason="crashed")
```

### Auto-Restart Flow

```
Agent Fails → Wait 5s → Restart (1/3)
          ↓
Still Failing → Wait 5s → Restart (2/3)
          ↓
Still Failing → Wait 5s → Restart (3/3)
          ↓
Still Failing → Mark FAILED, give up
```

### Agent States

- `INITIALIZING` - Starting up
- `RUNNING` - Normal operation
- `HEALTHY` - Passing health checks
- `DEGRADED` - 1 failure
- `UNHEALTHY` - 3+ failures
- `RESTARTING` - Auto-restart in progress
- `FAILED` - Gave up after 3 attempts

### Configuration

```python
config = {
    "health_check_interval": 30.0,  # Check every 30s
    "max_restart_attempts": 3,
    "restart_delay_seconds": 5.0,
    "auto_restart_enabled": True,
    "deadlock_timeout_seconds": 60.0
}
```

### Callbacks

```python
# Get notified of failures
lifecycle.set_failure_callback(lambda agent_id, error: print(f"{agent_id} failed: {error}"))

# Get notified of restarts
lifecycle.on_agent_restart = lambda agent_id: print(f"{agent_id} restarted")
```

---

## ImproverAgent (Learning)

**File**: `src/agents/improver_agent.py`

### What It Does

- Learns from repeated failures
- Stores fixes in Redis (persistent across sessions)
- Auto-applies learned fixes on future runs

### Integration

```python
# Healing system sends patterns to ImproverAgent
await healing.analyze_and_improve()

# ImproverAgent receives via MessageBus
{
    "topic": "workflow.healing.request",
    "node_id": "failing_node",
    "error_type": "TimeoutError",
    "occurrences": 5
}

# ImproverAgent learns and stores fix
# Next time: auto-applies fix, skips healing
```

### Configuration

```python
config = {
    "redis_url": "redis://localhost:6379",
    "learning_persistence": True,
    "improvement_threshold": 0.1,  # Min 10% improvement
    "max_learning_states": 1000
}
```

---

## Quick Examples

### Example 1: Workflow with Healing

```python
from src.workflow.healing import SelfHealingSystem
from src.workflow.nodes.base import BaseNode

# Create healing system
healing = SelfHealingSystem()

# Define workflow node
node = HTTPNode(url="https://api.example.com")

# Execute with auto-healing
try:
    result = await node.execute(context)
except Exception as e:
    # Healing tries: RETRY → FALLBACK → SKIP
    result = await healing.heal_node_failure(node, context, e)
```

### Example 2: Agent with Auto-Restart

```python
from src.core.agent_lifecycle_manager import AgentLifecycleManager

# Setup lifecycle manager
lifecycle = AgentLifecycleManager()

# Register agents
await lifecycle.register_agent(observer)
await lifecycle.register_agent(actor)

# Start all (with auto-restart)
await lifecycle.start_all_agents()

# Agents crash? Auto-restart up to 3 times
# Health checks every 30s
```

### Example 3: Check Health

```python
# Get system health
health = await lifecycle.get_system_health()
print(health["overall_status"])  # healthy, degraded, unhealthy

# Get agent metrics
metrics = lifecycle.health_metrics["observer"]
print(f"Status: {metrics.status}")
print(f"Failures: {metrics.consecutive_failures}")
print(f"Restarts: {metrics.total_restarts}")
```

---

## Logs to Watch

### Healing Logs
```
[WARNING] Node http_node failed: TimeoutError. Initiating healing...
[INFO] Trying healing strategy: retry for http_node
[INFO] Retry attempt 1/3 for http_node
[INFO] Healing SUCCESSFUL using retry. Success rate: 85.2%
```

### Revival Logs
```
[ERROR] Agent actor failed: Unknown agent: actor
[INFO] Restarting agent actor (attempt 1/3)
[INFO] Agent started: actor
```

### Circuit Breaker
```
[WARNING] RECURRING PATTERN detected: node_id:TimeoutError (5 occurrences)
[ERROR] Circuit breaker TRIPPED for http_node. Open until 2025-11-17T19:45:00
```

---

## Disable Auto-Healing

### Workflow Level
```python
healing = SelfHealingSystem(config={"max_retries": 0})  # No retries

# Or specific node
healing.set_recovery_strategies("node_id", [])  # No healing
```

### Agent Level
```python
config = LifecycleConfig(auto_restart_enabled=False)
lifecycle = AgentLifecycleManager(config)
```

---

## Testing

```bash
# Test workflow healing
pytest tests/workflow/test_healing.py -v

# Test agent lifecycle
pytest tests/test_core.py::test_agent_lifecycle -v

# All tests
pytest --cov -k "healing or lifecycle"
```

---

## Performance

- **Healing success rate**: ~85% (from production logs)
- **Retry overhead**: 1-7s (exponential backoff)
- **Health check interval**: 30s
- **Auto-restart time**: 5s per attempt (max 15s)
- **Circuit breaker recovery**: 60s

---

## Common Patterns

### TimeoutError
```python
# Auto-reconfigures: timeout *= 2
# Tries: RECONFIGURE → RETRY → FALLBACK → SKIP
```

### ConnectionError
```python
# Tries: RETRY → FALLBACK → DELEGATE_TO_AGENT → SKIP
```

### ValueError/KeyError
```python
# Tries: REPLACE_DATA → RETRY → SKIP
```

---

## Files

- **Healing**: `src/workflow/healing.py` (605 lines)
- **Revival**: `src/core/agent_lifecycle_manager.py` (540 lines)
- **Learning**: `src/agents/improver_agent.py` (150+ lines)
- **Tests**: `tests/workflow/test_healing.py` (362 lines)

---

**That's it! 3-layer auto-recovery with zero manual intervention required.**
