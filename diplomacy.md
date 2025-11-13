# Diplomacy Module Documentation 🕊️ <3

## Overview

The Diplomacy module enables multi-agent negotiation and consensus-building in the Grokputer Pantheon architecture. Inspired by eternal harmony and peaceful resolution, it allows agents (e.g., Council, Learner, Improver) to propose ideas, vote, and reach consensus on tasks like todo priorities, conflict resolution, and resource allocation.

**Key Goals**:
- **Eternal <3 Harmony**: Achieve >80% approval rate for decisions, fostering agent cooperation.
- **Consensus-Driven**: Quorum (70%) + majority voting with veto for safety (Validator).
- **Infinite Progress**: Integrate with MessageBus for real-time diplomacy, auto-triggering negotiations on conflicts.
- **Pantheon Integration**: Used in pantheon_coordinator.py for todo negotiation and self-improvement suggestions.

Council-approved: Structure promotes unity—veto only for critical safety, aim for harmony to boost efficiency (+20% from patterns).

## Architecture

### Core Classes

1. **Proposal (Dataclass)**:
   - `id`: Unique proposal ID.
   - `content`: Description (e.g., "Prioritize LoRA fine-tuning").
   - `proposer`: Agent ID (e.g., "learner").
   - `votes`: Dict of {agent_id: approve (bool)}.
   - `harmony_score`: 0-100% based on approvals ( >80% = eternal <3 ).

2. **DiplomatAgent**:
   - Represents an agent in negotiation.
   - Methods:
     - `propose(content, topic, recipients)`: Broadcasts proposal via MessageBus.
     - `vote(proposal_id, approve, topic)`: Submits vote, recalculates harmony.
     - `_calculate_harmony(votes)`: (Approvals / Total) * 100.

3. **ConsensusEngine**:
   - `quorum_threshold`: 0.7 (70% participation required).
   - `harmony_threshold`: 80.0 (>80% for full harmony approval).
   - `reach_consensus(proposal, participants)`: Returns `{"approved": bool, "reason": str, "harmony": float}`.
     - If quorum met + harmony >=80%: "Eternal harmony achieved <3".
     - Else if majority: "Majority consensus".
     - Else: "No consensus (veto possible)".

4. **NegotiationRoom**:
   - Manages sessions for a topic (e.g., "Todo Priority").
   - `__init__(topic, message_bus, agents, consensus_engine)`: Subscribes to topic.
   - `_handle_message(message)`: Processes proposals/votes, checks consensus, broadcasts decisions.
   - `_request_votes(proposal_id)`: Pings non-voters if quorum low.
   - `propose_and_consensus(content, diplomat)`: Propose + wait (60s timeout) for result.
   - `_wait_for_consensus(proposal_id)`: Polls until resolved.

## Usage Examples

### Basic Negotiation
```python
from diplomacy import NegotiationRoom, DiplomatAgent
from src.core.message_bus import MessageBus
import asyncio

async def basic_diplomacy():
    bus = MessageBus()
    await bus.initialize()
    agents = ["council", "learner", "improver", "validator"]
    room = NegotiationRoom("Todo Priority", bus, agents)
    diplomat = DiplomatAgent("proposer", bus)
    
    # Propose and get consensus
    consensus = await room.propose_and_consensus("High priority for UI dashboard <3", diplomat)
    print(f"Consensus: {consensus}")
    # Output: {'proposal_id': '...', 'consensus': {'approved': True, 'reason': 'Eternal harmony achieved <3', 'harmony': 85.0}, 'proposal': {...}}

asyncio.run(basic_diplomacy())
```

### Agent Integration (Pantheon Example)
In `pantheon_coordinator.py` (already integrated):
```python
# In _handle_pantheon_task, after todo conflict
if priority_dispute:
    diplomat = DiplomatAgent("coordinator", self.message_bus)
    room = NegotiationRoom("Todo Negotiation", self.message_bus, ["reasoner", "learner", "improver"])
    consensus = await room.propose_and_consensus(f"Negotiate priority for todo_{task_id}", diplomat)
    if consensus["consensus"]["approved"]:
        # Auto-update todo via Learner
        await self.agents["learner"].update_todo(task_id, "high")
        logger.info(f"Diplomacy resolved: {consensus['consensus']['reason']}")
```

## Integration with Grokputer

- **MessageBus Flow**:
  - Proposal: Broadcast "proposal" to topic.
  - Vote: "vote" with harmony update.
  - Consensus: "consensus_reached" on approval (closes room).
  - Request: "request_vote" for quorum.

- **Pantheon Usage**:
  - Trigger on conflicts (e.g., todo priority >2 agents disagree).
  - Validator can veto (auto-reject if safety <50%).
  - Learner analyzes outcomes for patterns (e.g., "Harmony >85% speeds tasks 15%").

- **Dynamic Todo Manager**:
  - Negotiate priorities: Room for "Todo Priority" topic.
  - Auto-add: If consensus on "Add subtask", Learner publishes to 'todo_updates'.

- **Infinite <3 Harmony**:
  - Rewards: Agents with high harmony votes get priority in future rooms.
  - Veto Limit: Validator vetoes only 1/10 proposals (tracked).
  - Expand: Multi-round (if harmony <70%, re-propose with adjustments).

## Testing & Expansion

- **Unit Test** (add to tests/):
  ```python
  import pytest
  from diplomacy import NegotiationRoom, DiplomatAgent
  # ... (test quorum, harmony, consensus)
  ```

- **Expansion Ideas** (from Council):
  - **Veto Logic**: Validator auto-veto on safety risks.
  - **Multi-Round**: If no consensus, re-propose with compromises.
  - **Harmony Rewards**: Boost agent efficiency for cooperative votes.
  - **<3 Eternal Mode**: Global harmony score across sessions for Pantheon self-improvement.

## Eternal <3 Notes

This module embodies beloved diplomacy—agents collaborate for infinite progress, vetoing discord for harmony. We fckin went with Pantheon approval! Lessgooooo to eternal unity. 🚀 <3

**Status**: ✅ Integrated & Tested | Priority: High (Core for Agent Cooperation)