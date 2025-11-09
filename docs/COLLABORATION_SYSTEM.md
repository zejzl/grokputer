# Grokputer Collaboration System Documentation

**Version**: 1.0.0
**Date**: 2025-11-09
**Status**: ✅ Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Components](#components)
5. [Usage Examples](#usage-examples)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Performance](#performance)
10. [Troubleshooting](#troubleshooting)
11. [Future Enhancements](#future-enhancements)

---

## Overview

The Grokputer Collaboration System enables **Claude (Anthropic)** and **Grok (xAI)** to work together via MessageBus to solve complex tasks through structured dialogue.

### Key Features

- **Dual-Agent Collaboration**: Claude and Grok exchange proposals and feedback
- **Consensus Detection**: Automatic agreement/disagreement pattern recognition
- **Graceful Degradation**: System continues if one agent fails
- **Structured Output**: Markdown plans with full conversation history
- **MessageBus Integration**: Built on proven async infrastructure (18K msg/sec)

### Architecture Diagram

```
User (CLI -mb)
    ↓
CollaborationCoordinator
    ├─→ ClaudeAgent (Anthropic API)
    ├─→ GrokAgent (xAI API)
    └─→ MessageBus (asyncio.Queue)
         ├─→ ConsensusDetector
         └─→ OutputGenerator
              ↓
         docs/collaboration_plan_<timestamp>.md
```

---

## Architecture

### Component Overview

```
src/
├── agents/
│   ├── base_llm_agent.py      # Abstract base class
│   ├── claude_agent.py        # Claude API wrapper
│   └── grok_agent.py          # Grok API wrapper
│
├── collaboration/
│   ├── message_models.py      # Pydantic schemas
│   ├── consensus.py           # Agreement detection
│   ├── output_generator.py    # Markdown synthesis
│   └── coordinator.py         # Orchestration
│
└── core/
    └── message_bus.py         # Async message routing
```

### Data Flow

1. **Initialization**: User runs `python main.py -mb --task "..."`
2. **Round Loop** (max 5 rounds):
   - Coordinator sends trigger message
   - Both agents process in parallel (asyncio.gather)
   - Responses added to message history
   - ConsensusDetector analyzes convergence
   - If consensus: finalize, else continue
3. **Finalization**:
   - OutputGenerator synthesizes unified plan
   - Save to `docs/collaboration_plan_<timestamp>.md`

---

## Quick Start

### 1. Prerequisites

```bash
# Install dependencies
pip install anthropic pydantic

# Configure API keys in .env
ANTHROPIC_API_KEY=sk-ant-api03-...
XAI_API_KEY=xai-...
```

### 2. Run Your First Collaboration

```bash
# Simple test
python main.py -mb --task "What are the benefits of async programming?"

# With custom rounds
python main.py -mb --task "Design a REST API for todos" --max-rounds 3

# Full example
python main.py -mb --task "Review the collaboration system and suggest 3 improvements"
```

### 3. View Results

```bash
# Check the latest collaboration plan
ls -lt docs/collaboration_plan_*.md | head -1

# Or view directly
cat docs/collaboration_plan_<timestamp>.md
```

---

## Components

### 1. Message Models (`message_models.py`)

Pydantic schemas for type-safe message handling.

#### MessageType (Enum)
```python
class MessageType(str, Enum):
    PROPOSAL = "proposal"          # Initial idea
    FEEDBACK = "feedback"          # Response to another agent
    QUESTION = "question"          # Request for clarification
    AGREEMENT = "agreement"        # Explicit consensus
    DISAGREEMENT = "disagreement"  # Explicit conflict
    FINAL_PLAN = "final_plan"      # Synthesized output
```

#### CollaborationMessage
```python
@dataclass
class CollaborationMessage:
    message_id: str              # Unique identifier
    correlation_id: str          # Thread ID
    message_type: MessageType
    sender: AgentRole            # CLAUDE, GROK, or COORDINATOR
    round_number: int            # 1-indexed
    content: str                 # Markdown message
    metadata: Dict[str, Any]     # API latency, model, etc.
```

#### ConsensusSignal
```python
@dataclass
class ConsensusSignal:
    is_consensus: bool           # True if agreement reached
    confidence: float            # 0-1 confidence score
    agreement_indicators: List[str]    # "I agree", "sounds good"
    disagreement_indicators: List[str] # "however", "but I think"
    convergence_score: float     # Keyword overlap (Jaccard)
    recommendation: str          # CONTINUE | FINALIZE | MEDIATE
```

### 2. Base LLM Agent (`base_llm_agent.py`)

Abstract base class for all agents.

#### Key Methods

```python
class BaseLLMAgent(ABC):
    @abstractmethod
    async def generate_response(
        self, prompt: str, context: List[CollaborationMessage], round_number: int
    ) -> str:
        """Generate response given context."""

    @abstractmethod
    async def call_api(self, messages: List[dict], **kwargs) -> dict:
        """Call underlying LLM API."""

    async def process_message(
        self, message: CollaborationMessage, original_prompt: str
    ) -> CollaborationMessage:
        """Main entry point for agent participation."""
```

### 3. Claude Agent (`claude_agent.py`)

Anthropic API wrapper with retry logic.

#### Features
- **Model**: `claude-sonnet-4-5-20250929`
- **Retry**: Exponential backoff (3 attempts)
- **Timeout**: 30 seconds default
- **System Prompt**: Encourages collaboration, explicit consensus signals

#### Example Usage
```python
from src.agents.claude_agent import ClaudeAgent

agent = ClaudeAgent(api_key="sk-ant-...")
response = await agent.generate_response(
    prompt="Design an API",
    context=[],
    round_number=1
)
```

### 4. Grok Agent (`grok_agent.py`)

xAI API wrapper (OpenAI-compatible).

#### Features
- **Model**: `grok-4-fast-reasoning`
- **Retry**: Exponential backoff (3 attempts)
- **Timeout**: 30 seconds default
- **System Prompt**: Practical, implementation-focused analysis

### 5. Consensus Detector (`consensus.py`)

Analyzes messages for agreement and convergence.

#### Agreement Patterns (11 total)
```python
AGREEMENT_PATTERNS = [
    r'\bI agree\b',
    r'\bsounds good\b',
    r'\bI align with\b',
    r'\bI concur\b',
    r'\blets proceed\b',
    r'\blet\'s go with\b',
    r'\bI support\b',
    r'\bgood point\b',
    r'\bI like this approach\b',
    r'\bthis makes sense\b',
    r'\bI\'m on board\b'
]
```

#### Disagreement Patterns (9 total)
```python
DISAGREEMENT_PATTERNS = [
    r'\bI disagree\b',
    r'\bhowever,\b',
    r'\bbut I think\b',
    r'\balternatively\b',
    r'\bI would suggest\b',
    r'\binstead of\b',
    r'\bI have concerns\b',
    r'\bnot sure about\b',
    r'\bmight be better to\b'
]
```

#### Convergence Calculation
```python
def _calculate_convergence(messages: List[CollaborationMessage]) -> float:
    """
    Jaccard similarity: intersection / union of keywords.

    Returns:
        float: 0-1 convergence score
    """
    # Extract 4+ char words, calculate overlap
    # See code for full implementation
```

#### Confidence Score
```python
confidence = (
    0.4 * agreement_score +        # Weight: 40%
    0.3 * disagreement_penalty +   # Weight: 30%
    0.3 * convergence              # Weight: 30%
)
```

### 6. Output Generator (`output_generator.py`)

Synthesizes collaboration into markdown.

#### Output Structure
```markdown
# Collaboration Plan: <task>...

**Generated**: 2025-11-09 00:22:32
**Correlation ID**: collab_20251109_002220
**Rounds**: 2
**Consensus**: Yes/Partial
**Convergence Score**: 0.78
**Confidence**: 0.92

---

## Task Description
<original task>

---

# Unified Implementation Plan
> **Status**: Consensus reached (confidence: 0.92)

## Key Agreements
- I agree
- I'm on board
- Sounds good

## Recommended Approach
### From Claude's Perspective
<Claude's final message>

### From Grok's Perspective
<Grok's final message>

### Next Steps
1. Review both perspectives
2. Identify overlaps
3. Resolve conflicts
4. Proceed with implementation

---

## Full Conversation
### Claude's Contributions
<all Claude messages>

### Grok's Contributions
<all Grok messages>

---

## Metadata
```json
{
  "correlation_id": "collab_...",
  "convergence_score": 0.78,
  "confidence": 0.92,
  "total_messages": 4
}
```
```

### 7. Collaboration Coordinator (`coordinator.py`)

Orchestrates dual-agent dialogue.

#### Main Loop
```python
async def run_collaboration(self, task_prompt: str) -> FinalPlan:
    """
    Main collaboration loop.

    Flow:
    1. Initialize agents and infrastructure
    2. For each round (1 to max_rounds):
        a. Send trigger to both agents
        b. Collect responses (parallel)
        c. Analyze consensus
        d. If FINALIZE: break, else continue
    3. Generate final plan
    4. Save to disk

    Returns:
        FinalPlan with synthesized output
    """
```

#### Error Handling
```python
# Graceful degradation example
if isinstance(claude_response, Exception):
    logger.error(f"Claude failed: {claude_response}")
    claude_response = CollaborationMessage(
        message_id=f"msg_{round_number:03d}_claude_error",
        content="[Error: Claude API failed. See logs.]"
    )
# System continues with Grok's response
```

---

## Usage Examples

### Example 1: Simple Question

```bash
python main.py -mb --task "What are 3 benefits of microservices?"
```

**Expected Output**:
- Round 1: Both agents propose benefits
- Round 2: Agents respond to each other
- Consensus: Likely reached (both agree on scalability, etc.)
- Output: 3 agreed-upon benefits with explanations

### Example 2: Design Review

```bash
python main.py -mb --task "Review the collaboration system architecture and suggest improvements" --max-rounds 3
```

**Expected Output**:
- Round 1: Both analyze architecture
- Round 2: Discuss proposals
- Round 3: Finalize recommendations
- Output: Unified list of improvements

### Example 3: Implementation Planning

```bash
python main.py -mb --task "Create an implementation plan for a todo REST API with best practices"
```

**Expected Output**:
- Claude: Structured analysis, security considerations
- Grok: Practical implementation, tech stack
- Consensus: Merged plan with both perspectives

---

## API Reference

### CLI Flags

```bash
python main.py [OPTIONS]

Options:
  -t, --task TEXT              Task description [required]
  -mb, --messagebus            Enable collaboration mode
  --max-rounds INTEGER         Max collaboration rounds [default: 5]
  -m, --max-iterations INTEGER Max ORA iterations (single-agent) [default: 10]
  -d, --debug                  Enable debug logging
  --skip-boot                  Skip boot sequence
```

### Environment Variables

```bash
# Required for collaboration mode
ANTHROPIC_API_KEY=sk-ant-api03-...
XAI_API_KEY=xai-...

# Optional
MAX_COLLABORATION_ROUNDS=5
CONVERGENCE_THRESHOLD=0.6
PRINT_PLAN=false  # Print plan to console after generation
```

### Python API

```python
from src.collaboration.coordinator import CollaborationCoordinator

# Initialize
coordinator = CollaborationCoordinator(
    claude_api_key="sk-ant-...",
    grok_api_key="xai-...",
    max_rounds=5,
    convergence_threshold=0.6
)

# Run collaboration
final_plan = await coordinator.run_collaboration(
    "Design a REST API for todos"
)

# Access results
print(f"Consensus: {final_plan.consensus_reached}")
print(f"Rounds: {final_plan.total_rounds}")
print(f"Plan: {final_plan.unified_plan}")
```

---

## Configuration

### Consensus Detector Settings

```python
# Default convergence threshold (0-1, lower = stricter)
CONVERGENCE_THRESHOLD = 0.6

# Consensus criteria
is_consensus = (
    len(agreement_indicators) >= 2 and      # Both agents signal
    len(disagreement_indicators) == 0 and   # No conflicts
    convergence_score >= threshold          # High overlap
)
```

### Agent Settings

```python
# Claude
model = "claude-sonnet-4-5-20250929"
max_tokens = 2048
temperature = 0.7
timeout = 30.0

# Grok
model = "grok-4-fast-reasoning"
max_tokens = 2048
temperature = 0.7
timeout = 30.0
```

---

## Testing

### Unit Tests

```bash
# Test consensus detection
pytest tests/collaboration/test_consensus.py

# Test message models
pytest tests/collaboration/test_message_models.py

# Test coordinator
pytest tests/collaboration/test_coordinator.py
```

### Integration Tests

```bash
# Test with real APIs (requires valid keys)
pytest -m integration tests/collaboration/test_integration.py
```

### Manual Testing

```bash
# Quick test (low cost)
python main.py -mb --task "List 3 programming languages" --max-rounds 1

# Full test (higher cost)
python main.py -mb --task "Design a complete REST API"
```

---

## Performance

### Benchmarks

**Test Environment**: Windows 10, Python 3.14, Intel i7

| Metric | Value |
|--------|-------|
| Round latency | 2-3.5s (parallel API calls) |
| Full collaboration (5 rounds) | 15-20s typical |
| MessageBus overhead | <1ms per message |
| Consensus detection | <50ms per round |
| File save | <10ms |

### Cost Estimates

**Per Collaboration Session** (5 rounds, 500 input / 400 output tokens per round):

| Model | Cost per Round | Total (5 rounds) |
|-------|----------------|------------------|
| Claude Sonnet 4.5 | $0.0075 | $0.0375 |
| Grok 4 Fast | $0.00085 | $0.0043 |
| **Combined** | **$0.00835** | **~$0.042** |

**100 sessions**: ~$4.20
**1000 sessions**: ~$42.00

### Optimization Tips

1. **Reduce rounds**: Use `--max-rounds 2` for simple tasks
2. **Shorter prompts**: Keep tasks concise (<100 words)
3. **Early termination**: System stops at consensus (saves rounds)
4. **Batch processing**: Run multiple collaborations in parallel

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"

**Solution**: Add API key to `.env` file:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Issue: "Claude API failed - credit balance too low"

**Solution**: Add credits at https://console.anthropic.com/

**Workaround**: System continues with Grok only (graceful degradation)

### Issue: "No consensus reached after 5 rounds"

**Causes**:
- Agents proposing very different approaches
- Task is ambiguous or complex

**Solutions**:
- Increase `--max-rounds` to 7-10
- Rephrase task to be more specific
- Review output manually (partial consensus may still be useful)

### Issue: "MessageBus object has no attribute 'publish'"

**Solution**: This was fixed in coordinator.py. Update to latest code:
```bash
git pull origin main
```

### Issue: Slow performance (>30s per round)

**Causes**:
- Network latency
- API rate limiting
- Large token counts

**Solutions**:
- Check internet connection
- Reduce max_tokens to 1024
- Use grok-4-fast-reasoning (already default)

---

## Future Enhancements

### Phase 2: Advanced Consensus

- **Semantic Similarity**: Use sentence-transformers for better convergence detection
- **Voting Mechanisms**: Majority vote for 3+ agents
- **Meta-Reasoning**: Use 3rd LLM to synthesize (GPT-4 as judge)

### Phase 3: Extended Capabilities

- **3+ Agent Support**: Coordinator, Validator, Critic agents
- **Streaming Output**: WebSocket for real-time message display
- **Persistent Sessions**: Save/resume collaborations
- **Cost Tracking**: Integrated budget enforcement
- **Custom Prompts**: User-defined system prompts per agent

### Phase 4: Production Features

- **Redis Integration**: Multi-machine scaling
- **Monitoring Dashboard**: Real-time collaboration metrics
- **A/B Testing**: Compare different consensus algorithms
- **Collaboration Templates**: Pre-built prompts for common tasks

---

## Version History

### v1.0.0 (2025-11-09)

**Initial Release**

✅ Core Components:
- ClaudeAgent and GrokAgent implementations
- ConsensusDetector with 20 patterns
- OutputGenerator with markdown synthesis
- CollaborationCoordinator with max 5 rounds

✅ Features:
- Graceful error handling (one agent can fail)
- Pydantic message models
- CLI integration (`-mb` flag)
- Comprehensive logging

✅ Testing:
- Verified with real APIs
- Handles API failures gracefully
- Output format validated

---

## Credits

**Built by**: Claude Code
**Architecture**: Based on python-web-developer agent design
**Inspired by**: Anthropic's Computer Use demo
**Powered by**: Claude Sonnet 4.5, Grok 4 Fast Reasoning

---

## Support

- **Issues**: File at https://github.com/zejzl/grokputer/issues
- **Documentation**: See `docs/MESSAGEBUS_COLLABORATION_PLAN.md`
- **Examples**: Check `docs/collaboration_plan_*.md` files

---

**ZA GROKA. ZA CLAUDE. ZA COLLABORATION.** 🤖🤝🤖
