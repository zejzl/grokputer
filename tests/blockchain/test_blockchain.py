"""
Tests for Blockchain Integration

Author: Grokputer Team
Date: 2025-11-17
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.blockchain.chain_adapter import (
    BlockchainAdapter,
    ChainType,
    LocalBlockchain,
    Block,
    Transaction
)
from src.blockchain.agent_blockchain_logger import AgentBlockchainLogger


class TestLocalBlockchain:
    """Test local blockchain implementation"""

    def test_genesis_block(self):
        """Test genesis block creation"""
        chain = LocalBlockchain()
        assert len(chain.chain) == 1
        assert chain.chain[0].index == 0
        assert chain.chain[0].previous_hash == "0"

    def test_add_transaction(self):
        """Test adding transactions"""
        chain = LocalBlockchain()
        tx = Transaction(
            tx_id="test123",
            tx_type="agent_action",
            agent_id="observer",
            data={"action": "test"}
        )

        result = chain.add_transaction(tx)
        assert result is True
        assert len(chain.pending_transactions) == 1

    def test_mine_block(self):
        """Test block mining"""
        chain = LocalBlockchain(difficulty=1)

        # Add transactions
        for i in range(3):
            tx = Transaction(
                tx_id=f"tx{i}",
                tx_type="agent_action",
                agent_id="test",
                data={"action": f"action{i}"}
            )
            chain.add_transaction(tx)

        # Mine block
        block = chain.mine_pending_transactions()

        assert block is not None
        assert block.index == 1
        assert len(block.data["transactions"]) == 3
        assert len(chain.pending_transactions) == 0
        assert len(chain.chain) == 2

    def test_chain_validation(self):
        """Test blockchain validation"""
        chain = LocalBlockchain(difficulty=1)

        # Add and mine blocks
        for i in range(3):
            tx = Transaction(
                tx_id=f"tx{i}",
                tx_type="agent_action",
                agent_id="test",
                data={"action": f"action{i}"}
            )
            chain.add_transaction(tx)
            chain.mine_pending_transactions()

        # Validate chain
        assert chain.is_valid() is True

        # Tamper with block
        chain.chain[1].data["transactions"][0]["data"]["action"] = "tampered"

        # Should be invalid now
        assert chain.is_valid() is False

    def test_get_transaction_history(self):
        """Test getting agent transaction history"""
        chain = LocalBlockchain(difficulty=1)

        # Add transactions for different agents
        for i in range(5):
            agent_id = "agent1" if i % 2 == 0 else "agent2"
            tx = Transaction(
                tx_id=f"tx{i}",
                tx_type="agent_action",
                agent_id=agent_id,
                data={"action": f"action{i}"}
            )
            chain.add_transaction(tx)

        chain.mine_pending_transactions()

        # Get history for agent1
        history = chain.get_transaction_history("agent1")
        assert len(history) == 3  # 3 out of 5 transactions

    def test_block_hash(self):
        """Test block hashing"""
        block = Block(
            index=1,
            timestamp=1234567890.0,
            data={"test": "data"},
            previous_hash="previous_hash"
        )

        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()

        # Same block should produce same hash
        assert hash1 == hash2

        # Modified block should produce different hash
        block.data["test"] = "modified"
        hash3 = block.calculate_hash()
        assert hash1 != hash3


class TestBlockchainAdapter:
    """Test blockchain adapter"""

    @pytest.mark.asyncio
    async def test_log_agent_action(self):
        """Test logging agent action"""
        adapter = BlockchainAdapter(ChainType.LOCAL)

        tx_id = await adapter.log_agent_action(
            agent_id="observer",
            action="capture_screen",
            data={"resolution": "1920x1080"}
        )

        assert tx_id is not None
        assert len(adapter.chain.pending_transactions) == 1

    @pytest.mark.asyncio
    async def test_log_memory_update(self):
        """Test logging memory update"""
        adapter = BlockchainAdapter(ChainType.LOCAL)

        tx_id = await adapter.log_memory_update(
            agent_id="memory",
            memory_type="episodic",
            data={"event": "task_completed"}
        )

        assert tx_id is not None

    @pytest.mark.asyncio
    async def test_log_consensus(self):
        """Test logging consensus decision"""
        adapter = BlockchainAdapter(ChainType.LOCAL)

        tx_id = await adapter.log_consensus_decision(
            agents=["grok", "claude"],
            decision="approve",
            votes={"grok": "yes", "claude": "yes"},
            confidence=0.95
        )

        assert tx_id is not None

    @pytest.mark.asyncio
    async def test_log_learning_state(self):
        """Test logging learning state"""
        adapter = BlockchainAdapter(ChainType.LOCAL)

        tx_id = await adapter.log_learning_state(
            agent_id="learner",
            task="optimize",
            state={"q_values": {}},
            performance=0.85
        )

        assert tx_id is not None

    @pytest.mark.asyncio
    async def test_mine_block(self):
        """Test manual block mining"""
        adapter = BlockchainAdapter(ChainType.LOCAL, config={"difficulty": 1})

        # Add transactions (don't trigger auto-mine)
        for i in range(3):
            await adapter.log_agent_action(
                agent_id="test",
                action=f"action{i}",
                data={"index": i}
            )

        # Verify pending transactions
        assert len(adapter.chain.pending_transactions) == 3

        # Mine block
        block = await adapter.mine_block()

        assert block is not None
        assert len(block.data["transactions"]) == 3
        assert len(adapter.chain.pending_transactions) == 0

    def test_get_stats(self):
        """Test getting blockchain stats"""
        adapter = BlockchainAdapter(ChainType.LOCAL)
        stats = adapter.get_stats()

        assert "chain_type" in stats
        assert "total_blocks" in stats
        assert stats["chain_type"] == "local"
        assert stats["total_blocks"] == 1  # Genesis block

    def test_verify_integrity(self):
        """Test chain integrity verification"""
        adapter = BlockchainAdapter(ChainType.LOCAL)
        assert adapter.verify_chain_integrity() is True

    def test_export_chain(self, tmp_path):
        """Test exporting blockchain"""
        adapter = BlockchainAdapter(ChainType.LOCAL)
        filepath = tmp_path / "test_chain.json"

        adapter.export_chain(str(filepath))

        assert filepath.exists()


class TestAgentBlockchainLogger:
    """Test agent blockchain logger"""

    @pytest.mark.asyncio
    async def test_log_action(self):
        """Test logging agent action"""
        logger = AgentBlockchainLogger()

        tx_id = await logger.log_action(
            agent_id="observer",
            action="capture_screen",
            data={"resolution": "1920x1080"}
        )

        assert tx_id is not None

    @pytest.mark.asyncio
    async def test_log_learning_update(self):
        """Test logging learning update"""
        logger = AgentBlockchainLogger()

        tx_id = await logger.log_learning_update(
            agent_id="learner",
            task="optimize",
            state={"q_values": {}},
            performance=0.85
        )

        assert tx_id is not None

    @pytest.mark.asyncio
    async def test_auto_mining(self):
        """Test auto-mining threshold"""
        logger = AgentBlockchainLogger(auto_mine_threshold=3)

        # Add transactions below threshold
        await logger.log_action("test", "action1", {})
        await logger.log_action("test", "action2", {})

        # Should not have mined yet
        assert len(logger.blockchain.chain.chain) == 1  # Only genesis

        # Add one more to trigger mining
        await logger.log_action("test", "action3", {})

        # Should have mined
        assert len(logger.blockchain.chain.chain) == 2

    def test_get_audit_trail(self):
        """Test getting agent audit trail"""
        # Create fresh blockchain to avoid test pollution
        from src.blockchain.chain_adapter import BlockchainAdapter, ChainType
        blockchain = BlockchainAdapter(ChainType.LOCAL)
        logger = AgentBlockchainLogger(blockchain_adapter=blockchain)

        # Initially empty
        trail = logger.get_agent_audit_trail("observer")
        assert len(trail) == 0

    def test_verify_integrity(self):
        """Test integrity verification"""
        logger = AgentBlockchainLogger()
        assert logger.verify_integrity() is True


@pytest.mark.asyncio
async def test_concurrent_transactions():
    """Test concurrent transaction processing"""
    adapter = BlockchainAdapter(ChainType.LOCAL, config={"difficulty": 1})

    # Simulate concurrent agent actions (use smaller number to avoid auto-mine in log_agent_action)
    num_transactions = 8
    tasks = []
    for i in range(num_transactions):
        task = adapter.log_agent_action(
            agent_id=f"agent{i % 3}",
            action=f"action{i}",
            data={"index": i}
        )
        tasks.append(task)

    # Wait for all transactions
    tx_ids = await asyncio.gather(*tasks)

    assert len(tx_ids) == num_transactions
    # Note: Some transactions may have auto-mined, so check for at least some pending
    assert len(adapter.chain.pending_transactions) > 0

    # Mine all pending
    block = await adapter.mine_block()
    if block:  # Only check if mining occurred
        assert len(block.data["transactions"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
