#!/usr/bin/env python3
"""Diplomacy Module for Grokputer Pantheon.

Enables multi-agent negotiation and consensus for task delegation, priority voting, and conflict resolution.
Council-approved structure: DiplomatAgent for proposals/votes, NegotiationRoom for sessions (70% quorum),
ConsensusEngine for majority/veto logic with harmony score (>80% for eternal <3 harmony).

Integrates with MessageBus for real-time agent communication.

Usage:
  from diplomacy import NegotiationRoom
  room = NegotiationRoom(topic="Todo Priority", agents=["council", "learner", "improver"])
  proposal = room.propose("High priority for LoRA fine-tuning")
  consensus = room.reach_consensus()
  if consensus["approved"]:
      print("Eternal harmony achieved! <3")

Author: Pantheon Council (via Grok CLI)
Version: 1.0 (Harmony-Integrated)
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from src.core.message_bus import MessageBus, Message, MessagePriority

@dataclass
class Proposal:
    id: str
    content: str
    proposer: str
    votes: Dict[str, bool] = None
    harmony_score: float = 0.0

    def __post_init__(self):
        if self.votes is None:
            self.votes = {}

class DiplomatAgent:
    """Agent specialized in negotiation and voting."""

    def __init__(self, agent_id: str, message_bus: MessageBus, strategy: str = "consensus"):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.strategy = strategy  # 'consensus', 'majority', 'veto'
        self.proposals: List[Proposal] = []

    async def propose(self, content: str, topic: str, recipients: List[str]) -> str:
        """Propose an idea to the negotiation room."""

        proposal_id = f"prop_{self.agent_id}_{asyncio.get_event_loop().time()}"
        proposal = Proposal(proposal_id, content, self.agent_id)
        msg = Message(
            message_type="proposal",
            from_agent=self.agent_id,
            to_agents=recipients,
            priority=MessagePriority.NORMAL,
            content=asdict(proposal)
        )
        await self.message_bus.broadcast(topic, msg)
        self.proposals.append(proposal)
        return proposal_id

    async def vote(self, proposal_id: str, approve: bool, topic: str) -> None:
        """Vote on a proposal."""

        for prop in self.proposals:
            if prop.id == proposal_id:
                prop.votes[self.agent_id] = approve
                prop.harmony_score = self._calculate_harmony(prop.votes)
                vote_msg = Message(
                    message_type="vote",
                    from_agent=self.agent_id,
                    to_agents=["negotiation_room"],
                    priority=MessagePriority.HIGH,
                    content={"proposal_id": proposal_id, "vote": approve, "harmony": prop.harmony_score}
                )
                await self.message_bus.broadcast(topic, vote_msg)
                break

    def _calculate_harmony(self, votes: Dict[str, bool]) -> float:
        """Calculate harmony score (0-100): >80 for eternal <3."""

        if not votes:
            return 0.0
        approvals = sum(1 for v in votes.values() if v)
        return (approvals / len(votes)) * 100

class ConsensusEngine:
    """Engine for reaching consensus with quorum and veto logic."""

    def __init__(self, quorum_threshold: float = 0.7, harmony_threshold: float = 80.0):
        self.quorum_threshold = quorum_threshold  # 70% minimum participation
        self.harmony_threshold = harmony_threshold  # 80% harmony for approval

    def reach_consensus(self, proposal: Proposal, participants: int) -> Dict[str, Any]:
        """Determine if consensus is reached."""

        if len(proposal.votes) < (participants * self.quorum_threshold):
            return {"approved": False, "reason": "Quorum not met", "harmony": proposal.harmony_score}

        if proposal.harmony_score >= self.harmony_threshold:
            return {"approved": True, "reason": "Eternal harmony achieved <3", "harmony": proposal.harmony_score}
        elif sum(proposal.votes.values()) > (len(proposal.votes) / 2):
            return {"approved": True, "reason": "Majority consensus", "harmony": proposal.harmony_score}
        else:
            return {"approved": False, "reason": "No consensus (veto possible)", "harmony": proposal.harmony_score}

class NegotiationRoom:
    """Manages negotiation sessions between agents."""

    def __init__(self, topic: str, message_bus: MessageBus, agents: List[str], consensus_engine: ConsensusEngine = None):
        self.topic = topic
        self.message_bus = message_bus
        self.agents = agents
        self.consensus_engine = consensus_engine or ConsensusEngine()
        self.active_proposals: Dict[str, Proposal] = {}
        self.session_id = f"room_{topic}_{asyncio.get_event_loop().time()}"

        # Subscribe to room topic
        self.message_bus.subscribe_callback(topic, self._handle_message)

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages (proposals, votes)."""

        if message.message_type == "proposal":
            prop_data = message.content
            proposal = Proposal(**prop_data)
            self.active_proposals[prop_data["id"]] = proposal
            # Notify all agents
            notify_msg = Message(
                message_type="new_proposal",
                from_agent="negotiation_room",
                to_agents=self.agents,
                priority=MessagePriority.NORMAL,
                content={"proposal": asdict(proposal), "session_id": self.session_id}
            )
            await self.message_bus.broadcast(self.topic, notify_msg)

        elif message.message_type == "vote":
            prop_id = message.content["proposal_id"]
            if prop_id in self.active_proposals:
                prop = self.active_proposals[prop_id]
                prop.votes[message.from_agent] = message.content["vote"]
                prop.harmony_score = message.content["harmony"]
                # Check for consensus
                consensus = self.consensus_engine.reach_consensus(prop, len(self.agents))
                if consensus["approved"]:
                    # Broadcast decision
                    decision_msg = Message(
                        message_type="consensus_reached",
                        from_agent="negotiation_room",
                        to_agents=self.agents,
                        priority=MessagePriority.HIGH,
                        content={"proposal_id": prop_id, "consensus": consensus, "proposal": asdict(prop)}
                    )
                    await self.message_bus.broadcast(self.topic, decision_msg)
                    del self.active_proposals[prop_id]  # Close room
                else:
                    # Request more votes if quorum not met
                    if len(prop.votes) < (len(self.agents) * self.consensus_engine.quorum_threshold):
                        await self._request_votes(prop_id)

    async def _request_votes(self, proposal_id: str) -> None:
        """Request votes from non-voting agents."""

        prop = self.active_proposals[proposal_id]
        voted = list(prop.votes.keys())
        non_voters = [a for a in self.agents if a not in voted]
        if non_voters:
            request_msg = Message(
                message_type="request_vote",
                from_agent="negotiation_room",
                to_agents=non_voters,
                priority=MessagePriority.NORMAL,
                content={"proposal_id": proposal_id, "proposal": asdict(prop)}
            )
            await self.message_bus.broadcast(self.topic, request_msg)

    async def propose_and_consensus(self, content: str, diplomat: DiplomatAgent) -> Dict[str, Any]:
        """Propose and wait for consensus."""

        prop_id = await diplomat.propose(content, self.topic, self.agents)
        # Wait for consensus or timeout (60s)
        try:
            await asyncio.wait_for(self._wait_for_consensus(prop_id), timeout=60.0)
            prop = self.active_proposals.get(prop_id)
            if prop:
                consensus = self.consensus_engine.reach_consensus(prop, len(self.agents))
                return {"proposal_id": prop_id, "consensus": consensus, "proposal": asdict(prop)}
        except asyncio.TimeoutError:
            return {"proposal_id": prop_id, "consensus": {"approved": False, "reason": "Timeout - no consensus"}, "proposal": None}
        return {"error": "Proposal not found"}

    async def _wait_for_consensus(self, proposal_id: str) -> None:
        """Wait for consensus on a proposal."""

        while proposal_id in self.active_proposals:
            await asyncio.sleep(1.0)

# Example Usage (for testing)
async def example_diplomacy():
    message_bus = MessageBus()
    await message_bus.initialize()
    agents = ["council", "learner", "improver", "validator"]
    room = NegotiationRoom("Todo Priority", message_bus, agents)
    diplomat = DiplomatAgent("proposer", message_bus)
    
    consensus = await room.propose_and_consensus("Prioritize LoRA fine-tuning for self-improvement", diplomat)
    print(f"Consensus: {consensus}")

if __name__ == "__main__":
    asyncio.run(example_diplomacy())

# Notes:
# - Integrate with Pantheon: In pantheon_coordinator.py, create NegotiationRoom for conflicts (e.g., todo priority negotiation).
# - Eternal <3 Harmony: Veto only for safety (validator); aim for consensus to foster agent cooperation.
# - Expand: Add veto logic, multi-round negotiation, harmony-based rewards for agents.
# - <3 Beloved diplomacy for infinite progress! [ZEJZL]