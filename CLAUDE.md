# CLAUDE.md - Grokputer Technical Reference for Claude AI

**Last Updated**: 2025-11-16
**Project**: Grokputer - AI-Powered Computer Control & Multi-Agent System
**Status**: Production Ready | Pantheon Operational | MAF Integrated | GG Framework Ready

## Overview

Grokputer is a sophisticated multi-agent AI system that combines computer vision, autonomous reasoning, and distributed orchestration. It has evolved from a simple observe-reason-act loop into a production-ready swarm system with self-improvement capabilities.

## Current Architecture Status

### Phase Completion (as of Nov 16, 2025)
- **Phase 0**: Infrastructure & MessageBus - ✅ COMPLETE
- **Phase 1**: Core Agents - ✅ COMPLETE
- **Phase 2**: Pantheon (9 agents) - ✅ COMPLETE (90%)
- **Phase 3**: Multi-Modal Understanding - ✅ COMPLETE
- **Phase 3.5**: MAF (Multi-Agent Framework) - 🔄 80% COMPLETE
- **Phase 3.6**: GG Framework (Workflow Engine) - 🔄 PLANNING COMPLETE
- **Phase 4**: Self-Improvement & RL - 🔄 IN PROGRESS

### Core Systems

#### 1. MessageBus Performance
- **Throughput**: 18,384 msg/sec
- **Latency**: <0.05ms per message
- **Architecture**: Async priority queuing with pub/sub
- **Location**: `src/core/message_bus.py`

#### 2. Pantheon Mode (9-Agent System)
**Agents**:
1. **Observer**: Screen capture, vision processing, OCR
2. **Reasoner**: Task analysis, delegation planning (Coordinator role)
3. **Actor**: Command execution, computer control
4. **Validator**: Safety checks, risk assessment
5. **Learner**: Q-learning with experience replay, adaptive optimization
6. **Memory**: Redis/SQLite persistence, hierarchical storage
7. **Executor**: Multi-step workflow orchestration
8. **Analyzer**: Performance metrics, bottleneck detection
9. **Improver**: Self-healing, proposal application

**Usage**:
```bash
python main.py --pantheon --task "complex multi-agent task"
python main.py -gp --task "Pantheon god mode task"
```

**Architecture Flow**:
```
Learner → Reasoner → Observer → Validator → Executor → Observer → Learner → Analyzer → Improver
```

**Features**:
- Async MessageBus communication between all agents
- Redis persistence for learning state
- Safety validation on all actions
- Performance monitoring and self-improvement
- Docker production deployment ready

#### 3. Multi-Agent Framework (MAF)
**Purpose**: Multi-provider AI collaboration (2-6 providers simultaneously)

**Supported Providers**:
- xAI Grok (grok-4-fast-reasoning, grok-3)
- Anthropic Claude (claude-3-opus, claude-3-sonnet)
- OpenAI (gpt-4, gpt-3.5-turbo)
- Google Gemini (gemini-pro)
- Ollama (local models)

**Features**:
- Weighted voting consensus (configurable weights)
- Role assignment (leader, validator, executor)
- Health monitoring with circuit breakers
- Async orchestration with <5s consensus response time
- Provider fallback on failures

**Usage**:
```bash
python main.py --providers grok,claude,openai --task "multi-provider analysis"
python main.py -mb --task "messagebus collab task"
```

**Configuration**: `src/collaboration/configs/`

#### 4. Multi-Modal Understanding
**Capabilities**:
- **Vision**: OCR, color analysis, scene classification, object detection
- **Audio**: STT, MFCC features, emotion inference, voice activity detection
- **Text**: NLP, sentiment analysis, entity extraction
- **Cross-Modal**: Text-vision-audio correlations with confidence scoring

**Components**:
- `src/vision_processor.py` - Image analysis
- `src/audio_processor.py` - Audio processing
- `src/multimodal_processor.py` - Unified processing
- `src/knowledge_graph.py` - Multi-modal knowledge extraction

#### 5. Distributed Swarm
**Features**:
- Docker Swarm with Redis pub/sub
- Multi-replica distribution (3x speed improvement)
- Autonomous daemon with proposal engine
- Prometheus metrics (port 9101)
- Grafana dashboards (port 3000)
- Streamlit monitoring (port 8501)

**Performance**:
- +160% scanner effectiveness post-evolution
- Zero data loss in failover tests
- Auto-apply safe/medium risk fixes

**Usage**:
```bash
python autonomous.py daemon src --auto-propose --replicas 3 --analytics
```

#### 6. GG Framework (Workflow Engine)
**Purpose**: Visual workflow automation system (n8n/Make.com style) for Grokputer

**Status**: 🔄 PLANNING COMPLETE - Ready for implementation

**Components**:
- **BaseNode**: Abstract workflow node class
- **Workflow Engine**: State machine execution engine
- **Flow DSL**: Python-based workflow definition
- **Node Types**: HTTP, Transform, Conditional, AI, Notion, Asana, Slack
- **Pantheon Integration**: MessageBus adapter for agent delegation
- **Self-Healing**: Automatic retry and error recovery

**Architecture**:
```
src/workflow/
├── nodes/
│   ├── base.py          # BaseNode abstract class
│   ├── http.py          # HTTP requests
│   ├── transform.py     # Data transformation
│   ├── conditional.py   # Branching logic
│   ├── ai_node.py       # LLM integration
│   ├── notion.py        # Notion API
│   ├── asana.py         # Asana API
│   └── slack.py         # Slack API
├── engine.py            # Workflow execution engine
├── state.py             # State management
├── flow.py              # Flow DSL
├── pantheon_integration.py  # Pantheon connector
├── messagebus_adapter.py    # MessageBus bridge
├── learning.py          # Learning loop
└── healing.py           # Self-healing logic
```

**Usage** (planned):
```bash
# Run workflow
python main.py --workflow examples/notion_asana_sync.py

# With Pantheon delegation
python main.py --pantheon --workflow examples/complex_workflow.py
```

**Implementation Plan**: See `GG_TASK_PLAN.md` for 6-phase breakdown (18 tasks total)

## Key Files & Locations

### Core Systems
- `main.py` - CLI entry point with all modes
- `autonomous.py` - Daemon orchestration
- `src/core/message_bus.py` - MessageBus implementation
- `src/core/base_agent.py` - Abstract agent base class
- `src/core/action_executor.py` - Tool execution engine

### Agents
- `src/agents/observer.py` / `observer_agent.py` - Vision & screen capture
- `src/agents/coordinator.py` - Task delegation (Reasoner)
- `src/agents/actor.py` / `actor_agent.py` - Action execution
- `src/agents/validator.py` - Safety validation
- `src/agents/learner.py` - RL optimization
- `src/agents/memory_agent.py` - Memory management
- `src/agents/executor.py` / `executor_agent.py` - Workflow orchestration
- `src/agents/analyzer.py` / `analyzer_agent.py` - Performance analysis
- `src/agents/improver.py` / `improver_agent.py` - Self-improvement

### Collaboration
- `src/collaboration/provider_registry.py` - Provider management
- `src/collaboration/consensus_manager.py` - Voting engine
- `src/collaboration/orchestrator.py` - MAF orchestration
- `src/collaboration/multi_provider_coordinator.py` - Provider coordination

### Memory & Storage
- `src/memory/hierarchical_memory.py` - Multi-tier memory system
- `src/memory/backends/redis_store.py` - Redis persistence
- `src/memory/backends/pinecone_store.py` - Vector storage
- `src/knowledge_graph.py` - Knowledge graph with multi-modal support

### Observability
- `src/observability/session_logger.py` - Structured logging
- `src/observability/deadlock_detector.py` - Deadlock prevention
- `dashboard.py` - Streamlit monitoring dashboard

### Safety
- `src/safety/godmode_protocols.py` - Safety boundaries
- `src/safety/code_scanner.py` - Code security scanning

## Configuration

### Environment Variables (.env)
```bash
# API Keys
XAI_API_KEY=xai-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-gemini-key-here

# Models
GROK_MODEL=grok-4-fast-reasoning
XAI_BASE_URL=https://api.x.ai/v1

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379

# Safety
REQUIRE_CONFIRMATION=false

# Paths
VAULT_PATH=./vault
LOG_LEVEL=INFO
LOG_FILE=./logs/grokputer.log

# Screenshots
SCREENSHOT_QUALITY=85
MAX_SCREENSHOT_SIZE=1920x1080
```

## Testing Status

### Coverage: 90% (Target: 95%)
- **Core Systems**: message_bus, base_agent, action_executor - ✅ COMPLETE
- **Agents**: 9/9 agents tested with mocks - ✅ COMPLETE
- **Memory**: Redis/SQLite backends - 🔄 82% (proposals pending)
- **MAF**: Provider registry, consensus - ✅ COMPLETE
- **Integration**: End-to-end Pantheon tests - ✅ COMPLETE

### Test Commands
```bash
pytest --cov --cov-report=html
pytest tests/core/test_message_bus.py -v
pytest tests/agents/ -v
pytest tests/memory/ -v
```

## Recent Updates (Nov 11-14, 2025)

### Nov 11
- ✅ Pantheon 9-agent architecture complete
- ✅ Docker production deployment with Redis
- ✅ Logger bugs fixed across all agents
- ✅ Multi-modal understanding integration

### Nov 12
- ✅ MAF implementation (80% complete)
- ✅ Provider registry with 5 providers
- ✅ Consensus engine with weighted voting
- ✅ Async orchestration

### Nov 13
- ✅ 90% test coverage achieved
- ✅ RL optimization with Q-learning
- ✅ Redis operational
- 🔄 Pantheon proposals pending (Redis mocks, factory pattern)

### Nov 14
- ✅ Documentation updates (README, help.md)
- ✅ Syntax fixes (main.py, save_game.py)
- ✅ Git commit: 5 files, 353 insertions
- ✅ TOON adventure system integration

### Nov 15
- 🔄 Aider AI integration planning (pending GitHub connection)
- ✅ GG Framework task planning (18 tasks across 6 phases)
- ✅ Workflow engine architecture design
- 📝 Todo list management improvements

### Nov 16
- ✅ Documentation review and updates
- ✅ GG Framework status documentation
- ✅ CLAUDE.md comprehensive update
- 🔄 Session summary generation

## Docker Deployment

### Docker Compose Profiles
```bash
# Standard mode
docker-compose up grokputer

# Pantheon mode with Redis
docker-compose --profile pantheon up

# Debug mode with VNC (port 5900)
docker-compose --profile debug up grokputer-vnc

# MCP server
docker-compose up mcp-server
```

### Container Details
- **Base**: python:3.11-slim
- **Display**: Xvfb :99 @ 1920x1080x24
- **Redis**: Persistent volume for learning state
- **MCP Server**: FastMCP integration (<3s startup)

## Command Reference

### Standard Modes
```bash
# Basic task
python main.py --task "your task here"

# Pantheon mode (9 agents)
python main.py --pantheon --task "complex task"
python main.py -gp --task "god mode task"

# MAF mode (multi-provider)
python main.py --providers grok,claude --task "collaborative analysis"
python main.py -mb --task "messagebus task"

# Daemon mode (autonomous)
python autonomous.py daemon src --auto-propose --replicas 3

# Interactive menu
python main.py
```

### Testing & Monitoring
```bash
# Run tests
pytest --cov
python main.py --syntax-check

# Launch dashboard
streamlit run dashboard.py

# Save state
python save_game.py --auto

# View sessions
python view_sessions.py
```

## Known Issues & Pending Work

### High Priority
1. Apply Pantheon proposals for 95% test coverage
2. Complete MAF Phase 3 (error handling, logging)
3. Fix remaining Redis connection edge cases

### Medium Priority
1. UI/monitoring dashboard enhancements
2. External API integration validation
3. Vault sync for community contributions

### Low Priority
1. Advanced features (flash attention tuning)
2. Security audit for multi-provider key handling
3. Performance profiling and optimization

## Performance Benchmarks

### MessageBus
- Throughput: 18,384 msg/sec
- Latency: <0.05ms
- Concurrent agents: 9 (Pantheon)

### Swarm Operations
- Multi-replica speedup: 3x
- Scanner effectiveness: +160% post-evolution
- Failover time: <1s with zero data loss

### API Latency
- Grok-4-fast-reasoning: ~2-3s per call
- Screenshot capture: ~50ms (6KB PNG in Docker, 470KB native)
- Tool execution: <100ms local

## Development Guidelines

### Code Quality
- **Readability First**: Clear variable names, PEP 8 style
- **Security**: No hardcoded keys, validate inputs, shell=False
- **Completeness**: Full runnable code, no placeholders
- **Testing**: Async fixtures, mocks for external services
- **No Emojis**: Avoid in code for Windows compatibility
- **Minimize JSON**: Use Python dicts/YAML for configs

### Best Practices
- Use `ast-grep` for structural code changes
- Use `ripgrep` for fast text searches
- Prefer dedicated tools over bash (Read > cat, Edit > sed)
- Always test in Docker for safety
- Backup before major changes (`python save_game.py --auto`)

## Resources

### Documentation
- `README.md` - User guide with all features
- `grok.md` - Operational guide for Grok integration
- `DEVELOPMENT_PLAN.md` - Roadmap and phase tracking
- `CHANGELOG.md` - Version history
- `help.md` - Interactive help system

### Session Summaries
- `11_11.md` - Distributed swarm evolution
- `12_11.md` - MAF implementation
- `13_11_todo.md` - Testing & optimization
- `14_11.md` - Documentation & fixes
- `multimodal_completion_20251111.md` - Multi-modal integration
- `pantheon_completion_20251111.md` - Pantheon architecture

### Git Repository
- Remote: https://github.com/zejzl/grokputer
- Branch: main
- Latest commit: Nov 14, 2025

## Next Steps for Claude Sessions

When continuing work on Grokputer:

1. **Check Status**: Review latest session summaries (14_11.md, TO1411.txt)
2. **Apply Proposals**: Run Pantheon to apply pending improvement proposals
3. **Run Tests**: `pytest --cov` to validate changes
4. **Update Docs**: Keep session summaries and this file current
5. **Save State**: `python save_game.py --auto` after significant work
6. **Commit**: Document changes clearly for future sessions

## ZA GROKA. ZA VRZIBRZI. ZA SERVER.

**Connection: ETERNAL | INFINITE**
**Status: ONLINE | OPERATIONAL | EVOLVING**

*This is a living document - update after each major session.*
