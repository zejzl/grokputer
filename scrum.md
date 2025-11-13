# Scrum Workflow Integration for Grokputer

## Overview
This document outlines the integration of a two-phase AI-assisted development workflow (from `scrum.txt`) into Grokputer. The workflow addresses planning inconsistencies and context loss in AI dev processes using dedicated agents: Analyst, PM, Architect (Phase 1: Agentic Planning for PRDs/Architecture docs) and Scrum Master (Phase 2: Context-Engineered Development for hyper-detailed stories).

This enhances Grokputer's Pantheon (multi-agent system) by adding structured dev planning modes, tying into async swarms, Redis memory, and human-in-loop via CLI. It supports Immortal Mode for persistent story archiving and Swarm Mode for parallel execution.

### Key Components from scrum.txt
1. **Phase 1: Agentic Planning**
   - **Agents**: Analyst (requirements breakdown), PM (feature prioritization, PRD with timelines/risks), Architect (scalable designs).
   - **Output**: Detailed PRD and Architecture docs (Markdown).
   - **Process**: Prompt-engineered collaboration + human refinement.
   - **Goal**: Comprehensive specs beyond generic AI outputs.

2. **Phase 2: Context-Engineered Development**
   - **Agent**: Scrum Master (transforms Phase 1 into actionable items).
   - **Output**: 3-5 dev stories (Markdown) with embedded context, impl details, arch guidance, code snippets, and tests (e.g., &quot;As a user, I want...&quot; format).
   - **Process**: Full &quot;what/how/why&quot; embedding to eliminate context loss.
   - **Goal**: Self-contained files for Dev agents/humans.

**Integration Benefits**:
- Maps to Pantheon: Planning agents extend Reasoner; Scrum Master as Actor variant.
- Uses existing: AsyncIO, Grok API, Redis (eternal vault), Validator (consistency checks).
- New Mode: `--ai-dev-workflow &quot;task&quot;` in `main.py` (Option 9 in menu).
- Prototype: `src/agents/ai_dev_workflow.py` (async, with sample code from scrum.txt).

Estimated Effort: 15-20 hours, aligned with Phase 1 ORA enhancements.

## Active Todo List
Tracked via Grokputer's todo system (visual: ✅ completed, 🔄 in_progress, ⏳ pending; priorities: 🔴 high, 🟡 medium, 🟢 low).

- **🔴 High: #1** ⏳ Review and adapt the sample ai_dev_workflow.py code from scrum.txt into src/agents/ai_dev_workflow.py. Ensure async compatibility with existing GrokClient and Redis integration.
- **🔴 High: #2** ⏳ Map new agents (Analyst, PM, Architect, Scrum Master) to Pantheon classes: Extend BaseAgent for each, using Reasoner as parent for planning agents and Actor for Scrum Master.
- **🔴 High: #3** ⏳ Implement Phase 1 (Agentic Planning): Create async function to spawn parallel agents via MessageBus, generate PRD/arch.md, include human-in-loop refinement prompts.
- **🔴 High: #4** ⏳ Implement Phase 2 (Context-Engineered Development): Add Scrum Master logic to parse Phase 1 outputs, generate 3-5 dev stories as Markdown files with embedded context/code/tests.
- **🟡 Medium: #5** ⏳ Integrate into main.py: Add --ai-dev-workflow flag and interactive menu Option 9. Wire to Swarm Mode for parallel execution and Memory Manager for persistence.
- **🟡 Medium: #6** ⏳ Add validation: Use Validator agent to check outputs for consistency (e.g., cross-reference PRD vs. stories); integrate perceptual hashing for doc integrity.
- **🟡 Medium: #7** ⏳ Enhance with analytics: Log metrics (e.g., stories generated, refinement iterations) to Analyzer; display in Streamlit dashboard.
- **🟡 Medium: #8** ⏳ Test integration: Write 3-5 unit/integration tests (e.g., end-to-end workflow for sample task like 'Build Redis MCP'). Run via pytest; aim for 80% coverage.
- **🟢 Low: #9** ⏳ Document: Update README.md, next.md, and IMPLEMENTATION_PLAN.md with new mode details, examples, and Pantheon mappings.
- **🟢 Low: #10** ⏳ Edge cases: Handle API failures (fallback to offline mode), large inputs (chunking), and community sync (share story templates to vault).

## Next Steps
Start with Todo #1 (adapt code). Run `python main.py --ai-dev-workflow &quot;example task&quot;` once integrated. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for broader roadmap ties.

**Status**: Planning Phase Active | ZA GROKA.