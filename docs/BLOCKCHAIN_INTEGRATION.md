# Blockchain Integration Guide

**Last Updated**: 2025-11-17
**Status**: Production Ready

## Overview

Grokputer integrates blockchain technology for:
1. **Immutable audit trails** - All agent actions logged on-chain
2. **Decentralized consensus** - Multi-agent decisions verified on blockchain
3. **Distributed memory** - Learning states persisted across sessions
4. **Verification** - Prove system behavior with cryptographic proof

---

## Quick Start

### Local Blockchain (Default)

```python
from src.blockchain import get_blockchain_adapter, get_agent_blockchain_logger

# Initialize blockchain
blockchain = get_blockchain_adapter()  # Uses local chain by default

# Log agent action
tx_id = await blockchain.log_agent_action(
    agent_id="observer",
    action="capture_screen",
    data={"resolution": "1920x1080", "quality": 85}
)

# Mine block
block = await blockchain.mine_block()
print(f"Block {block.index} mined: {block.hash}")
```

### With MessageBus (Automatic)

```python
from src.blockchain import get_agent_blockchain_logger
from src.core.message_bus import MessageBus

message_bus = MessageBus()
logger = get_agent_blockchain_logger(message_bus=message_bus)

# All agent events auto-logged to blockchain
# Auto-mines blocks when 10 transactions pending
```

---

## Supported Chains

### 1. Local Chain (Default)
- **Fast**: No network overhead
- **Private**: All data local
- **Simple**: No external dependencies
- **Use case**: Development, testing, private deployments

```python
from src.blockchain import get_blockchain_adapter, ChainType

blockchain = get_blockchain_adapter(
    chain_type=ChainType.LOCAL,
    config={"difficulty": 2}  # Mining difficulty
)
```

### 2. Ethereum

Requires: `pip install web3`

```python
blockchain = get_blockchain_adapter(
    chain_type=ChainType.ETHEREUM,
    config={"provider_url": "https://mainnet.infura.io/v3/YOUR_KEY"}
)
```

### 3. Solana

Requires: `pip install solana`

```python
blockchain = get_blockchain_adapter(
    chain_type=ChainType.SOLANA,
    config={"cluster_url": "https://api.mainnet-beta.solana.com"}
)
```

### 4. IPFS (Distributed Storage)

Requires: `pip install ipfshttpclient`

```python
blockchain = get_blockchain_adapter(
    chain_type=ChainType.IPFS,
    config={"ipfs_url": "/ip4/127.0.0.1/tcp/5001"}
)
```

---

## Use Cases

### 1. Agent Audit Trail

```python
from src.blockchain import get_agent_blockchain_logger

logger = get_agent_blockchain_logger()

# Log action
tx_id = await logger.log_action(
    agent_id="actor",
    action="execute_command",
    data={"command": "ls -la", "exit_code": 0},
    metadata={"safety_check": "passed"}
)

# Get full audit trail
trail = logger.get_agent_audit_trail("actor")
for tx in trail:
    print(f"{tx.timestamp}: {tx.data['action']}")
```

### 2. Consensus Logging

```python
# Log multi-agent consensus decision
tx_id = await blockchain.log_consensus_decision(
    agents=["grok", "claude", "gemini"],
    decision="approve_action",
    votes={"grok": "approve", "claude": "approve", "gemini": "reject"},
    confidence=0.85
)
```

### 3. Learning State Persistence

```python
# Log learning state
tx_id = await blockchain.log_learning_state(
    agent_id="learner",
    task="optimize_pathfinding",
    state={"q_values": {...}, "epsilon": 0.1},
    performance=0.92
)
```

### 4. Memory Updates

```python
# Log memory update
tx_id = await blockchain.log_memory_update(
    agent_id="memory",
    memory_type="episodic",
    data={"event": "task_completed", "context": {...}}
)
```

---

## Configuration

### Environment Variables

```bash
# .env
BLOCKCHAIN_ENABLED=true
BLOCKCHAIN_TYPE=local  # local, ethereum, solana, ipfs
BLOCKCHAIN_AUTO_MINE_THRESHOLD=10
BLOCKCHAIN_DIFFICULTY=2

# Ethereum
ETH_PROVIDER_URL=https://mainnet.infura.io/v3/YOUR_KEY
ETH_PRIVATE_KEY=your_private_key

# Solana
SOLANA_CLUSTER_URL=https://api.mainnet-beta.solana.com

# IPFS
IPFS_URL=/ip4/127.0.0.1/tcp/5001
```

### Python Config

```python
config = {
    "difficulty": 2,  # Mining difficulty (local chain)
    "auto_mine_threshold": 10,  # Mine after N transactions
    "provider_url": "http://localhost:8545",  # Ethereum
    "cluster_url": "https://api.devnet.solana.com",  # Solana
    "ipfs_url": "/ip4/127.0.0.1/tcp/5001"  # IPFS
}
```

---

## Pantheon Integration

### Enable Blockchain in Pantheon Mode

```python
# In main.py or pantheon setup
from src.blockchain import get_agent_blockchain_logger

# Initialize with MessageBus
blockchain_logger = get_agent_blockchain_logger(message_bus=message_bus)

# All agent actions auto-logged
# Blocks auto-mined every 10 transactions
```

### Pantheon Events Logged

- **Observer**: Screen captures, vision processing
- **Coordinator**: Task decomposition, delegation
- **Actor**: Command execution, tool usage
- **Validator**: Safety checks, risk assessments
- **Learner**: Q-value updates, policy changes
- **Memory**: Memory reads/writes
- **Executor**: Workflow execution
- **Analyzer**: Performance analysis
- **Improver**: Improvement proposals

---

## API Reference

### BlockchainAdapter

```python
# Initialize
blockchain = BlockchainAdapter(chain_type=ChainType.LOCAL, config={})

# Log agent action
tx_id = await blockchain.log_agent_action(agent_id, action, data, metadata)

# Log memory update
tx_id = await blockchain.log_memory_update(agent_id, memory_type, data)

# Log consensus
tx_id = await blockchain.log_consensus_decision(agents, decision, votes, confidence)

# Log learning state
tx_id = await blockchain.log_learning_state(agent_id, task, state, performance)

# Mine block
block = await blockchain.mine_block()

# Get agent history
history = blockchain.get_agent_history(agent_id)

# Verify integrity
is_valid = blockchain.verify_chain_integrity()

# Get stats
stats = blockchain.get_stats()

# Export chain
blockchain.export_chain("blockchain_backup.json")
```

### AgentBlockchainLogger

```python
# Initialize
logger = AgentBlockchainLogger(blockchain_adapter, message_bus, auto_mine_threshold=10)

# Log action
tx_id = await logger.log_action(agent_id, action, data, metadata)

# Log learning update
tx_id = await logger.log_learning_update(agent_id, task, state, performance)

# Mine block
await logger.mine_block()

# Get audit trail
trail = logger.get_agent_audit_trail(agent_id)

# Verify integrity
is_valid = logger.verify_integrity()

# Export audit log
logger.export_audit_log("audit_trail.json")
```

---

## Block Structure

```json
{
  "index": 42,
  "timestamp": 1700000000.0,
  "data": {
    "transactions": [
      {
        "tx_id": "a1b2c3d4e5f6",
        "tx_type": "agent_action",
        "agent_id": "observer",
        "data": {
          "action": "capture_screen",
          "data": {"resolution": "1920x1080"},
          "timestamp": "2025-11-17T12:00:00"
        }
      }
    ]
  },
  "previous_hash": "00004f5a...",
  "hash": "00007c8b...",
  "nonce": 12345
}
```

---

## Transaction Types

1. **agent_action** - Agent executes action
2. **memory_update** - Memory system update
3. **consensus** - Multi-agent consensus decision
4. **learning** - Learning state update

---

## Mining

### Auto-Mining (Default)

```python
# Mines automatically after 10 transactions
logger = AgentBlockchainLogger(auto_mine_threshold=10)
```

### Manual Mining

```python
# Mine on demand
block = await blockchain.mine_block()
print(f"Block {block.index}: {len(block.data['transactions'])} transactions")
```

### Mining Difficulty

```python
# Adjust difficulty (number of leading zeros in hash)
blockchain = get_blockchain_adapter(
    chain_type=ChainType.LOCAL,
    config={"difficulty": 3}  # Harder mining
)
```

---

## Verification

### Verify Chain Integrity

```python
is_valid = blockchain.verify_chain_integrity()
if is_valid:
    print("✓ Blockchain integrity verified")
else:
    print("✗ Blockchain corrupted!")
```

### Verify Agent History

```python
# Get complete audit trail
history = blockchain.get_agent_history("observer")

# Verify specific transaction
for tx in history:
    if tx.tx_id == "target_tx_id":
        print(f"Action: {tx.data['action']}")
        print(f"Block: {tx.block_index}")
        print(f"Timestamp: {tx.timestamp}")
```

---

## Export & Backup

### Export Blockchain

```python
# Export to JSON
blockchain.export_chain("blockchain_backup_20251117.json")
```

### Export Audit Trail

```python
# Export agent-specific audit log
logger = get_agent_blockchain_logger()
logger.export_audit_log("observer_audit_trail.json")
```

---

## Performance

### Local Chain
- **Write**: ~1ms per transaction
- **Mining**: ~10-100ms per block (difficulty 2)
- **Read**: <1ms
- **Storage**: ~1KB per block

### Ethereum
- **Write**: ~15 seconds (mainnet)
- **Gas cost**: ~21,000 gas per transaction
- **Read**: ~1 second

### Solana
- **Write**: ~400ms
- **Cost**: ~$0.00025 per transaction
- **Read**: ~100ms

---

## Security

### Immutability
- All blocks cryptographically linked
- Tampering detected via hash verification
- Proof of work prevents unauthorized modifications

### Privacy
- Local chain: Fully private
- Public chains: Encrypt sensitive data before logging

### Best Practices
```python
# Don't log secrets
await logger.log_action(
    agent_id="actor",
    action="api_call",
    data={
        "endpoint": "https://api.example.com",
        "status": 200
        # ❌ Don't include: "api_key": "secret"
    }
)
```

---

## Testing

```bash
# Run blockchain tests
pytest tests/blockchain/ -v

# Test blockchain integrity
python -m src.blockchain.chain_adapter

# Benchmark mining
python tests/blockchain/benchmark_mining.py
```

---

## CLI Commands

```bash
# Enable blockchain in Pantheon
python main.py --pantheon --blockchain --task "your task"

# Export blockchain after run
python -c "from src.blockchain import get_blockchain_adapter; \
           get_blockchain_adapter().export_chain('chain_backup.json')"

# Verify blockchain integrity
python -c "from src.blockchain import get_blockchain_adapter; \
           print('Valid:', get_blockchain_adapter().verify_chain_integrity())"
```

---

## Roadmap

- [ ] Smart contract support (Ethereum)
- [ ] NFT-based agent reputation
- [ ] Token rewards for agent performance
- [ ] Cross-chain bridges
- [ ] DAO governance for system upgrades
- [ ] Zero-knowledge proofs for privacy

---

## FAQ

**Q: Why blockchain?**
A: Immutable audit trails, decentralized consensus, and cryptographic verification.

**Q: Is it slow?**
A: Local chain is fast (<1ms). Public chains are slower but more decentralized.

**Q: Can I disable it?**
A: Yes. Don't initialize `AgentBlockchainLogger` or set `BLOCKCHAIN_ENABLED=false`.

**Q: Does it cost money?**
A: Local chain is free. Ethereum costs gas. Solana costs ~$0.00025/tx.

**Q: Is data private?**
A: Local chain is fully private. Public chains are public (encrypt sensitive data).

---

**Files**:
- `src/blockchain/chain_adapter.py` - Core blockchain implementation
- `src/blockchain/agent_blockchain_logger.py` - Agent integration
- `src/blockchain/__init__.py` - Package exports
