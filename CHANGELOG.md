# Changelog

## [v2026.02.02] - 2026-02-02 - Docker Deployment & Python 3.11 Compatibility

### Fixed
- **Type Annotation Forward References**: Added `from __future__ import annotations` to 192+ Python files to resolve `NameError` issues with forward type references (e.g., `OrchestrationConfig`, `Tuple`, etc.) in Python 3.11+
- **Docker Build Issues**: 
  - Fixed orchestrator.py line 173: `NameError: name 'OrchestrationConfig' is not defined`
  - Fixed message_bus.py line 741: `NameError: name 'Tuple' is not defined`
  - Fixed analytics_performance_tools.py type annotation errors
  - Fixed base_agent.py and 20+ other modules
- **Missing Dependencies**: Added `cryptography` to requirements-minimal.txt for Docker builds
- **Docker Configuration**:
  - Added `superagent/` directory to Dockerfile COPY command
  - Whitelisted `!superagent/` in .dockerignore to ensure module availability
  - Fixed Xvfb display server initialization in Docker container

### Changed
- **Docker Startup**: Container now successfully runs "server prayer" task in headless mode with Xvfb virtual display
- **Python Compatibility**: All modules now compatible with Python 3.10+ type annotation semantics

### Verified
- ✅ All Python modules import successfully without errors
- ✅ Docker container starts and runs tasks in continuous loop
- ✅ Orchestrator, MessageBus, and RL Optimizer initialize correctly
- ✅ Headless Firefox + Xvfb working for GUI automation

**Migration Note**: If upgrading from previous versions, ensure your Python files include `from __future__ import annotations` at the top if using forward type references in type hints.

## [v2026.01.30] - 2026-01-30 - MessageBus Performance Upgrade & Windows Compatibility

### Changed
- **MessageBus Performance**: Upgraded to high-performance async implementation achieving 425,274 msg/sec (10x improvement from 42K), 0.007ms P95 latency (7x improvement from 0.05ms)
- **Windows Compatibility**: Removed all emojis from 27 Python files, replaced with ASCII equivalents ([OK], [FAIL], [STATS], etc.) to fix Windows encoding issues
- **Core Module Updates**: Improved agent lifecycle manager, base agent, and workflow systems
- **Observability Enhancements**: Refactored deadlock detector (270 lines removed), improved healing and learning modules

### Added
- **Security Validator**: New security_validator.py module for enhanced security checks
- **Test Coverage**: Added test_pantheon_integration.py and tests/collaboration/test_provider_pool.py
- **Documentation**: Updated grok.md with latest architecture and performance metrics

### Fixed
- **Windows Encoding Issues**: Eliminated UnicodeEncodeError from emoji characters in Python files
- **MessageBus Integration**: Synchronized with zejzl_net MessageBus implementation for consistency

### Performance
- **MessageBus**: 425K+ msg/sec throughput (10x faster), 0.007ms latency (7x lower)
- **Pantheon Pipeline**: Can now support 10,000+ agent swarms with sub-millisecond coordination
- **Zero External Dependencies**: Removed Redis requirement for inter-agent communication

## [v2025.11.14] - 2025-11-14 - Core Architecture Operational

### Added
- **MessageBus Throughput Validation**: Real-world testing achieved 42,301 messages/second with 10 concurrent agents
- **HRM Reasoner Agent**: Integrated Victor Taelin HRM with fallback reasoning for puzzle solving
- **Full System Collaboration Test**: Validated MAF orchestrator, agent lifecycle management, and MessageBus integration
- **Performance Monitoring**: Sub-millisecond latency (<0.05ms) confirmed for MessageBus operations

### Fixed
- **GrokClient Bugs**: Added missing `create_message` method and fixed async session handling to prevent 'ClientSession' await errors. Disabled problematic analytics integration.

### Tested
- **Concurrent Agent Communication**: 10 agents tested with zero deadlocks
- **Request-Response Patterns**: Correlation IDs and priority queuing validated
- **Collaboration Framework**: Consensus detection and session logging operational
- **Security Systems**: Shell injection protection and encryption confirmed active

### Performance
- **MessageBus**: 42k+ msg/sec throughput, <0.05ms latency
- **Agent Framework**: HRM Reasoner, lifecycle management, health monitoring
- **System Integration**: MAF orchestrator, MessageBus, collaboration consensus

**Note**: Core architecture fully operational; requires API keys for LLM functionality.

## [v2025.11.13] - 2025-11-13

### Added
- New feature: src/config.py
- New feature: src/core/action_executor.py
- New feature: src/grok_client.py
- New feature: src/screen_observer.py
- New feature: src/__pycache__/
- ... and 18 more features
### Vision & OCR
- Enhanced vision capabilities: src/ocr/__pycache__/
### Agents
- Agent enhancement: src/core/base_agent.py
- Agent enhancement: backups/agent_states.py
- Agent enhancement: src/agents/__pycache__/
### Testing
- Added/updated 6 test files

All notable changes to Grokputer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.2] - 2025-11-13 - Optimizations & Analytics Wave

### Added
- **Analytics Tracking** (`analytics.py`): SQLite-based session metrics (API calls, success rates, durations). Integrates with Pantheon for real-time tracking. Usage: `python analytics.py` for reports.
- **Structured Logging** (`logging_config.py`): JSON-formatted logs with rotation (10MB files, 5 backups). Import `setup_logging()` in main.py. Enhances observability.
- **Hierarchical Memory Optimizations** (`src/memory/hierarchical_memory.py`): LRU caching (@lru_cache on retrieve/store), size limits, decay/eviction to prevent leaks. Added `optimize()` method.
- **Enhanced Streamlit Dashboard** (`streamlit_app.py`): Real-time graphs (Plotly: API timelines, success bars, provider pies), system metrics (CPU/Mem/Disk gauges via psutil), memory viz, log preview. Run: `streamlit run streamlit_app.py`.
- **Log Aggregator** (`log_aggregator.py`): ELK simulation—watchdog file watcher parses JSON logs to SQLite (`db/logs_aggregated.db`). Query like Kibana. Run: `python log_aggregator.py` for live aggregation.
- **Redis Backup** (`backup_redis.py`): Dumps all keys/values to `./vault/redis_backup.json` (handles strings, hashes, lists). Integrated into `save_game.py --auto`. Run: `python backup_redis.py`.

### Changed
- **Documentation Updates**: README.md enhanced with new tool sections/examples. Added Redis backup explanation in vault notes.
- **Save Game Enhancements**: Auto-Redis backup before git commit (skips if Redis down). Vault sync improved (better error handling).
- **Pantheon Testing**: Validated optimizations with dir analysis task—100% success, 4 API calls, 45s duration.

### Fixed
- **Dependency Issues**: Resolved Streamlit deps (tornado, altair, etc.); compatible pyarrow (14.0.1 binary).
- **Syntax Errors**: Cleaned src/config.py (Redis config); langchain warnings addressed.
- **Cleanup**: git clean freed ~2GB (temps, caches); .gitignore excludes large Solana SDK.

## [1.8.1] - 2025-11-13 - Multi-Modal & Pantheon Complete

### Added
- **Multi-Modal Understanding** (Phase 3.5): Vision (OCR, object detection), Audio (speech-to-text, features), Unified Processor with cross-modal correlation.
- **Knowledge Graph Integration** (Phase 3.4): Entity/relationship extraction, semantic search fused with memory.
- **Hierarchical Memory** (Phase 3.3): 3-tier (short/context/long-term) with Redis/SQLite hybrid.

### Changed
- **Pantheon Architecture**: Full 9 agents operational (Observer, Reasoner, Validator, etc.) with safety, learning, Redis persistence.
- **Docker**: Production-ready with Pantheon profile.

## [1.8.0] - 2025-11-11 - Advanced Intelligence

### Added
- **AsyncIO Foundation**: Full async conversion, MessageBus, BaseAgent.
- **Multi-Agent Swarm**: 3-agent ORA loop; expandable to Pantheon.
- **Claude-Grok Collaboration**: Dual AI consensus.
- **Interactive Menu**: 8 modes (Single, Swarm, Pantheon, etc.).
- **Offline Mode & Vault Sync**: Local KB, community sharing.
- **Save Game**: Optimized backups (5GB → 1MB).

### Fixed
- **Security Audit**: 5 vulnerabilities remediated (API keys, shell injection).

## [1.7.0] - 2025-11-10 - Initial Release

### Added
- Core Observe-Reason-Act loop.
- Screen control (PyAutoGUI), shell execution.
- Grok API integration.
- Basic testing suite (32+ tests).

[1.8.2]: https://github.com/zejzl/grokputer/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/zejzl/grokputer/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/zejzl/grokputer/compare/v1.7.0...v1.8.0