# Changelog

All notable changes to Grokputer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Collaboration Mode: Claude + Grok dual-agent system (2025-11-09)
  - CLI integration with `-mb` / `--messagebus` flag
  - 7 core components: message models, agents, consensus, output generator, coordinator
  - Consensus detection with 11 agreement + 9 disagreement patterns
  - Jaccard similarity convergence scoring
  - Graceful degradation when one agent fails
  - Pydantic message validation
  - Async parallel API calls with retry logic (tenacity)
  - Markdown output with full conversation history
  - Comprehensive documentation in `docs/COLLABORATION_SYSTEM.md`

### Fixed
- Python cache issue causing old code to execute after updates
- Added cache clearing note to documentation

### Changed
- Updated README.md with Collaboration Mode section
- Updated CLAUDE.md with Phase 0 Milestone 1.2 completion
- Updated .env.example with ANTHROPIC_API_KEY and collaboration settings

## [0.2.0] - 2025-11-08

### Added
- Production MessageBus with message priorities (HIGH/NORMAL/LOW)
- Request-response pattern with correlation IDs
- Message history buffer (last 100 messages)
- Latency tracking per message type
- Safety Scoring System for bash commands
  - 40+ commands rated (LOW/MEDIUM/HIGH risk)
  - Pattern detection and flag analysis
  - Smart confirmation: 0-30 auto-approve, 31-70 warn, 71-100 confirm

### Performance
- MessageBus: 18,384 msg/sec throughput, <0.05ms latency
- 10/10 unit tests passing (pytest-asyncio)

## [0.1.0] - 2025-11-07

### Added
- Initial Grokputer implementation
- Observe-Reason-Act loop
- Screen observation with PyAutoGUI
- Grok API integration (xAI)
- Docker containerization with Xvfb
- Vault scanning tools
- Server prayer invocation
- Session logging system
- Enhanced metrics tracking

### Performance
- 2-3s per iteration (screen capture + API call + tool execution)
- Screenshot: ~6-8KB PNG in Docker, ~470KB native
- API latency: ~2-3s typical

---

## Legend

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities
- **Performance** for performance improvements
