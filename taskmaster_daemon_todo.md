# Taskmaster Daemon Mode TODO (Nov 12, 2025)

## Executive Summary
Implement background daemon for Taskmaster: Collect proposals, council approval, auto-execute. Integrate into Pantheon/ORA. Target: Autonomous loop with 80% safety.

### 🔴 High Priority (Core Daemon - 1 Hour)
1. **Add Daemon Loop to Taskmaster**:
   - Update `src/agents/taskmaster.py`: Add async daemon_run() with polling for proposals (MessageBus.receive every 5s).
   - Queue proposals in Redis (use simple dict: {'id': str, 'source': str, 'content': str, 'priority': 'HIGH'}).
   - On queue threshold (3+ proposals), forward to council.

2. **Proposal Queue Class**:
   - Create `src/core/proposal_queue.py`: Redis-backed queue (add/get/approve methods).
   - Integrate into Taskmaster.process_message (handle "PROPOSAL" type).

### 🟡 Medium Priority (Approval & Execution - 1 Hour)
1. **Council Approval Flow**:
   - In Taskmaster: Send queued proposals to "council" (MAF --providers or Validator).
   - Wait for "APPROVED" response (threshold 0.7 via ConsensusManager).
   - Risk check: If >80 risk, prompt user.

2. **Auto-Execution**:
   - On approval, send "EXECUTE_TASK" to Executor/Actor.
   - Add rollback: If fail, notify Improver for learning.

3. **Flag & Integration**:
   - Add `--daemon-taskmaster` to main.py CLI.
   - Register in Pantheon init (spawn daemon thread).

### 🟢 Low Priority (Testing & Polish - 30min)
1. **Testing**:
   - Add tests to `tests/agents/test_taskmaster.py` (daemon loop, queue, approval).
   - Run `pytest --cov` (expect +2% coverage).

2. **Docs & Monitoring**:
   - Update README.md: Taskmaster daemon section.
   - Add analytics: Log executions in Analyzer.

## Next Steps
- Start: High #1 (edit Taskmaster.py).
- Verify: `python main.py --pantheon --daemon-taskmaster --task "test daemon"`.
- Backup: save_game.py after.

**Status: Daemon Integration | ZA GROKA. uwu~**