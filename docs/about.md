# About Grokputer

Grokputer is a CLI tool that enables xAI's Grok API to control a PC through a three-phase loop:

1. **Observe**: Capture and analyze screenshots
2. **Reason**: Send observations to Grok API (grok-4-fast-reasoning) for decision-making
3. **Act**: Execute commands, control mouse/keyboard, or access files

**Current Status**: Phase 0 Complete (100%) - Multi-agent swarm foundation operational
- Async architecture with asyncio
- MessageBus (18K msg/sec)
- Observer + Actor agents validated
- PoC test passed (3.13s, zero deadlocks)

**Next**: Phase 1 - Coordinator agent + 3-agent swarm (Weeks 2-4)
