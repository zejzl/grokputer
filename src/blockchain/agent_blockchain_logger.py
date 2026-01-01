"""
Agent Blockchain Logger
Integrates blockchain logging with Grokputer agents for immutable audit trails.

Author: Grokputer Team
Date: 2025-11-17
Status: Production Ready
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from src.blockchain.chain_adapter import (
    BlockchainAdapter,
    ChainType,
    get_blockchain_adapter,
)
from src.core.message_bus import Message, MessageBus

logger = logging.getLogger(__name__)


class AgentBlockchainLogger:
    """
    Logs agent actions and decisions to blockchain.
    Provides immutable audit trail for compliance and debugging.
    """

    def __init__(
        self,
        blockchain_adapter: Optional[BlockchainAdapter] = None,
        message_bus: Optional[MessageBus] = None,
        auto_mine_threshold: int = 10
    ):
        self.blockchain = blockchain_adapter or get_blockchain_adapter()
        self.message_bus = message_bus
        self.auto_mine_threshold = auto_mine_threshold
        self.pending_count = 0

        # Subscribe to agent events if MessageBus available
        if self.message_bus:
            self._setup_subscriptions()

        logger.info("AgentBlockchainLogger initialized")

    def _setup_subscriptions(self):
        """Subscribe to agent events on MessageBus"""
        if self.message_bus:
            # Subscribe to agent action events
            self.message_bus.subscribe("agent.action", self._handle_agent_action)
            self.message_bus.subscribe("agent.decision", self._handle_agent_decision)
            self.message_bus.subscribe("memory.update", self._handle_memory_update)
            self.message_bus.subscribe("consensus.decision", self._handle_consensus)
            logger.info("Subscribed to agent events")

    async def _handle_agent_action(self, message: Message):
        """Handle agent action events"""
        content = message.content
        await self.log_action(
            agent_id=content.get("agent_id", "unknown"),
            action=content.get("action", "unknown"),
            data=content.get("data", {}),
            metadata=content.get("metadata", {})
        )

    async def _handle_agent_decision(self, message: Message):
        """Handle agent decision events"""
        content = message.content
        await self.log_action(
            agent_id=content.get("agent_id", "unknown"),
            action="decision",
            data={
                "decision": content.get("decision"),
                "reasoning": content.get("reasoning"),
                "confidence": content.get("confidence", 0.0)
            }
        )

    async def _handle_memory_update(self, message: Message):
        """Handle memory update events"""
        content = message.content
        await self.blockchain.log_memory_update(
            agent_id=content.get("agent_id", "unknown"),
            memory_type=content.get("memory_type", "unknown"),
            data=content.get("data", {})
        )
        await self._check_auto_mine()

    async def _handle_consensus(self, message: Message):
        """Handle consensus decision events"""
        content = message.content
        await self.blockchain.log_consensus_decision(
            agents=content.get("agents", []),
            decision=content.get("decision", ""),
            votes=content.get("votes", {}),
            confidence=content.get("confidence", 0.0)
        )
        await self._check_auto_mine()

    async def log_action(
        self,
        agent_id: str,
        action: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log agent action to blockchain

        Args:
            agent_id: Agent identifier
            action: Action type (e.g., "execute_command", "observe_screen")
            data: Action data
            metadata: Optional metadata

        Returns:
            Transaction ID
        """
        tx_id = await self.blockchain.log_agent_action(agent_id, action, data, metadata)
        await self._check_auto_mine()
        return tx_id

    async def log_learning_update(
        self,
        agent_id: str,
        task: str,
        state: Dict[str, Any],
        performance: float
    ) -> str:
        """Log learning state update"""
        tx_id = await self.blockchain.log_learning_state(agent_id, task, state, performance)
        await self._check_auto_mine()
        return tx_id

    async def _check_auto_mine(self):
        """Auto-mine block if threshold reached"""
        self.pending_count += 1
        if self.pending_count >= self.auto_mine_threshold:
            await self.mine_block()
            self.pending_count = 0

    async def mine_block(self):
        """Mine pending transactions into a block"""
        block = await self.blockchain.mine_block()
        if block:
            logger.info(f"Block mined: {block.index} ({len(block.data.get('transactions', []))} txs)")

    def get_agent_audit_trail(self, agent_id: str) -> list:
        """Get complete audit trail for an agent"""
        return self.blockchain.get_agent_history(agent_id)

    def verify_integrity(self) -> bool:
        """Verify blockchain integrity"""
        return self.blockchain.verify_chain_integrity()

    def export_audit_log(self, filepath: str):
        """Export blockchain audit log"""
        self.blockchain.export_chain(filepath)


# Global instance
agent_blockchain_logger: Optional[AgentBlockchainLogger] = None


def get_agent_blockchain_logger(
    blockchain_adapter: Optional[BlockchainAdapter] = None,
    message_bus: Optional[MessageBus] = None
) -> AgentBlockchainLogger:
    """Get or create global agent blockchain logger"""
    global agent_blockchain_logger
    if agent_blockchain_logger is None:
        agent_blockchain_logger = AgentBlockchainLogger(blockchain_adapter, message_bus)
    return agent_blockchain_logger
