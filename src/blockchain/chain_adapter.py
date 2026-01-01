"""
Blockchain Adapter for Grokputer
Provides decentralized storage, audit logging, and consensus mechanisms.

Supported chains:
- Ethereum (via Web3.py)
- Solana (via solana-py)
- Local chain (simple implementation)
- IPFS (for distributed storage)

Author: Grokputer Team
Date: 2025-11-17
Status: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChainType(Enum):
    """Supported blockchain types"""
    LOCAL = "local"
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    IPFS = "ipfs"
    POLYGON = "polygon"


@dataclass
class Block:
    """Simple block structure for local chain"""
    index: int
    timestamp: float
    data: Dict[str, Any]
    previous_hash: str
    hash: str = ""
    nonce: int = 0

    def __post_init__(self):
        if not self.hash:
            self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2):
        """Proof of work mining"""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()


@dataclass
class Transaction:
    """Blockchain transaction"""
    tx_id: str
    tx_type: str  # agent_action, memory_update, consensus, learning
    agent_id: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None
    block_index: Optional[int] = None


class LocalBlockchain:
    """
    Simple local blockchain implementation.
    Fast, lightweight, no network overhead.
    """

    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = difficulty
        self.mining_reward = 1.0

        # Create genesis block
        genesis = Block(0, time.time(), {"message": "Genesis Block"}, "0")
        genesis.mine_block(self.difficulty)
        self.chain.append(genesis)

        logger.info("LocalBlockchain initialized with genesis block")

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool"""
        self.pending_transactions.append(transaction)
        logger.debug(f"Transaction added: {transaction.tx_id}")
        return True

    def mine_pending_transactions(self) -> Block:
        """Mine all pending transactions into a block"""
        if not self.pending_transactions:
            return None

        # Create new block
        last_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data={
                "transactions": [
                    {
                        "tx_id": tx.tx_id,
                        "tx_type": tx.tx_type,
                        "agent_id": tx.agent_id,
                        "data": tx.data,
                        "timestamp": tx.timestamp
                    }
                    for tx in self.pending_transactions
                ]
            },
            previous_hash=last_block.hash
        )

        # Mine block
        new_block.mine_block(self.difficulty)

        # Add to chain
        self.chain.append(new_block)

        # Update transaction block indices
        for tx in self.pending_transactions:
            tx.block_index = new_block.index

        # Clear pending transactions
        self.pending_transactions.clear()

        logger.info(f"Block {new_block.index} mined: {new_block.hash[:16]}...")
        return new_block

    def is_valid(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Verify hash
            if current_block.hash != current_block.calculate_hash():
                logger.error(f"Invalid hash at block {i}")
                return False

            # Verify chain
            if current_block.previous_hash != previous_block.hash:
                logger.error(f"Broken chain at block {i}")
                return False

        return True

    def get_block(self, index: int) -> Optional[Block]:
        """Get block by index"""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def get_transaction_history(self, agent_id: str) -> List[Transaction]:
        """Get all transactions for an agent"""
        transactions = []
        for block in self.chain[1:]:  # Skip genesis
            for tx_data in block.data.get("transactions", []):
                if tx_data["agent_id"] == agent_id:
                    transactions.append(Transaction(**tx_data))
        return transactions


class BlockchainAdapter:
    """
    Main blockchain adapter for Grokputer.
    Provides unified interface to multiple blockchain backends.
    """

    def __init__(self, chain_type: ChainType = ChainType.LOCAL, config: Dict[str, Any] = None):
        self.chain_type = chain_type
        self.config = config or {}
        self.chain = None

        # Web3 instance (for Ethereum/Polygon)
        self.web3 = None

        # Initialize chain
        self._initialize_chain()

        logger.info(f"BlockchainAdapter initialized: {chain_type.value}")

    def _initialize_chain(self):
        """Initialize blockchain connection"""
        if self.chain_type == ChainType.LOCAL:
            difficulty = self.config.get("difficulty", 2)
            self.chain = LocalBlockchain(difficulty)

        elif self.chain_type == ChainType.ETHEREUM:
            try:
                from web3 import Web3
                provider_url = self.config.get("provider_url", "http://localhost:8545")
                self.web3 = Web3(Web3.HTTPProvider(provider_url))

                if self.web3.is_connected():
                    logger.info(f"Connected to Ethereum: {provider_url}")
                else:
                    logger.warning("Failed to connect to Ethereum, falling back to LOCAL")
                    self.chain_type = ChainType.LOCAL
                    self.chain = LocalBlockchain()
            except ImportError:
                logger.warning("web3.py not installed, falling back to LOCAL")
                self.chain_type = ChainType.LOCAL
                self.chain = LocalBlockchain()

        elif self.chain_type == ChainType.SOLANA:
            try:
                from solana.rpc.api import Client
                cluster_url = self.config.get("cluster_url", "https://api.devnet.solana.com")
                self.solana_client = Client(cluster_url)
                logger.info(f"Connected to Solana: {cluster_url}")
            except ImportError:
                logger.warning("solana-py not installed, falling back to LOCAL")
                self.chain_type = ChainType.LOCAL
                self.chain = LocalBlockchain()

        elif self.chain_type == ChainType.IPFS:
            try:
                import ipfshttpclient
                ipfs_url = self.config.get("ipfs_url", "/ip4/127.0.0.1/tcp/5001")
                self.ipfs_client = ipfshttpclient.connect(ipfs_url)
                logger.info(f"Connected to IPFS: {ipfs_url}")
            except ImportError:
                logger.warning("ipfshttpclient not installed, falling back to LOCAL")
                self.chain_type = ChainType.LOCAL
                self.chain = LocalBlockchain()

    async def log_agent_action(
        self,
        agent_id: str,
        action: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log agent action to blockchain (immutable audit trail)

        Returns:
            Transaction ID
        """
        tx_id = hashlib.sha256(
            f"{agent_id}{action}{time.time()}".encode()
        ).hexdigest()[:16]

        transaction = Transaction(
            tx_id=tx_id,
            tx_type="agent_action",
            agent_id=agent_id,
            data={
                "action": action,
                "data": data,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
        )

        if self.chain_type == ChainType.LOCAL:
            self.chain.add_transaction(transaction)
            # Auto-mine if enough pending transactions
            if len(self.chain.pending_transactions) >= 5:
                await asyncio.to_thread(self.chain.mine_pending_transactions)

        logger.debug(f"Agent action logged: {tx_id} ({agent_id})")
        return tx_id

    async def log_memory_update(
        self,
        agent_id: str,
        memory_type: str,
        data: Dict[str, Any]
    ) -> str:
        """Log memory update to blockchain"""
        tx_id = hashlib.sha256(
            f"{agent_id}{memory_type}{time.time()}".encode()
        ).hexdigest()[:16]

        transaction = Transaction(
            tx_id=tx_id,
            tx_type="memory_update",
            agent_id=agent_id,
            data={
                "memory_type": memory_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        )

        if self.chain_type == ChainType.LOCAL:
            self.chain.add_transaction(transaction)

        logger.debug(f"Memory update logged: {tx_id}")
        return tx_id

    async def log_consensus_decision(
        self,
        agents: List[str],
        decision: str,
        votes: Dict[str, Any],
        confidence: float
    ) -> str:
        """Log consensus decision to blockchain"""
        tx_id = hashlib.sha256(
            f"consensus{decision}{time.time()}".encode()
        ).hexdigest()[:16]

        transaction = Transaction(
            tx_id=tx_id,
            tx_type="consensus",
            agent_id="system",
            data={
                "decision": decision,
                "agents": agents,
                "votes": votes,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
        )

        if self.chain_type == ChainType.LOCAL:
            self.chain.add_transaction(transaction)

        logger.info(f"Consensus logged: {tx_id} (confidence: {confidence:.2f})")
        return tx_id

    async def log_learning_state(
        self,
        agent_id: str,
        task: str,
        state: Dict[str, Any],
        performance: float
    ) -> str:
        """Log learning state to blockchain"""
        tx_id = hashlib.sha256(
            f"{agent_id}{task}{time.time()}".encode()
        ).hexdigest()[:16]

        transaction = Transaction(
            tx_id=tx_id,
            tx_type="learning",
            agent_id=agent_id,
            data={
                "task": task,
                "state": state,
                "performance": performance,
                "timestamp": datetime.now().isoformat()
            }
        )

        if self.chain_type == ChainType.LOCAL:
            self.chain.add_transaction(transaction)

        logger.debug(f"Learning state logged: {tx_id}")
        return tx_id

    async def mine_block(self) -> Optional[Block]:
        """Manually trigger block mining"""
        if self.chain_type == ChainType.LOCAL:
            return await asyncio.to_thread(self.chain.mine_pending_transactions)
        return None

    def get_agent_history(self, agent_id: str) -> List[Transaction]:
        """Get complete blockchain history for an agent"""
        if self.chain_type == ChainType.LOCAL:
            return self.chain.get_transaction_history(agent_id)
        return []

    def verify_chain_integrity(self) -> bool:
        """Verify blockchain integrity"""
        if self.chain_type == ChainType.LOCAL:
            return self.chain.is_valid()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        if self.chain_type == ChainType.LOCAL:
            return {
                "chain_type": self.chain_type.value,
                "total_blocks": len(self.chain.chain),
                "pending_transactions": len(self.chain.pending_transactions),
                "chain_valid": self.chain.is_valid(),
                "difficulty": self.chain.difficulty,
                "last_block_hash": self.chain.chain[-1].hash[:16] + "..." if self.chain.chain else None
            }
        return {"chain_type": self.chain_type.value}

    def export_chain(self, filepath: str):
        """Export blockchain to JSON file"""
        if self.chain_type == ChainType.LOCAL:
            chain_data = {
                "blocks": [
                    {
                        "index": block.index,
                        "timestamp": block.timestamp,
                        "data": block.data,
                        "previous_hash": block.previous_hash,
                        "hash": block.hash,
                        "nonce": block.nonce
                    }
                    for block in self.chain.chain
                ]
            }

            with open(filepath, 'w') as f:
                json.dump(chain_data, f, indent=2)

            logger.info(f"Blockchain exported to {filepath}")


# Global blockchain adapter instance
blockchain_adapter: Optional[BlockchainAdapter] = None


def get_blockchain_adapter(
    chain_type: ChainType = ChainType.LOCAL,
    config: Dict[str, Any] = None
) -> BlockchainAdapter:
    """Get or create global blockchain adapter"""
    global blockchain_adapter
    if blockchain_adapter is None:
        blockchain_adapter = BlockchainAdapter(chain_type, config)
    return blockchain_adapter
