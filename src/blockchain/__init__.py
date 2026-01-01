"""
Blockchain integration for Grokputer

Provides:
- Immutable audit logging for agent actions
- Decentralized consensus mechanisms
- Distributed memory storage
- Learning state persistence

Supported chains: Local, Ethereum, Solana, IPFS
"""

from src.blockchain.agent_blockchain_logger import (
    AgentBlockchainLogger,
    get_agent_blockchain_logger,
)
from src.blockchain.chain_adapter import (
    Block,
    BlockchainAdapter,
    ChainType,
    LocalBlockchain,
    Transaction,
    get_blockchain_adapter,
)

__all__ = [
    "BlockchainAdapter",
    "ChainType",
    "Block",
    "Transaction",
    "LocalBlockchain",
    "get_blockchain_adapter",
    "AgentBlockchainLogger",
    "get_agent_blockchain_logger"
]
