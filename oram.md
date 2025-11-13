# ORAM: Observe-Reason-Act-Memory Implementation Plan

**Generated**: 2025-11-10
**Status**: Post-AsyncIO Conversion - Ready for Agent Implementation
**Context**: Brainstorming next steps after completing AsyncIO foundation

---

## Current Status

### ✅ COMPLETED
- **AsyncIO foundation** - 100% complete!
- **BaseAgent, MessageBus, ActionExecutor** - All async-ready
- **GrokClient, ScreenObserver** - Fully converted to async
- **main.py** - All modes wrapped in asyncio.run()
- **Infrastructure** - Ready for multi-agent swarms

### 🎯 Current Capability
- Swarm mode launches successfully
- 3 agents spawn (coordinator, observer, actor)
- Infrastructure initializes correctly
- **Gap**: Agents are stub implementations (no actual logic)

---

## Immediate Priorities (This Week)

### 🔴 HIGH PRIORITY - Start Now

#### 1. Implement Working Observer Agent (2-3 hours)
**Goal**: Real screen observation capability

**Implementation**:
- Extend BaseAgent with actual screen observation logic
- Use existing ScreenObserver (now async!)
- Send observations to MessageBus
- Process observation requests from coordinator

**Why first**: Foundation for all visual tasks - enables agents to "see"

**File**: `src/agents/observer_agent.py`

**Quick Prototype**:
```python
from src.core.base_agent import BaseAgent
from src.screen_observer import ScreenObserver

class ObserverAgent(BaseAgent):
    async def on_start(self):
        self.screen = ScreenObserver()

    async def process_message(self, message):
        if message['type'] == 'observe':
            screenshot = await self.screen.screenshot_to_base64()
            return {
                'to': 'coordinator',
                'type': 'observation',
                'data': screenshot
            }
```

---

#### 2. Implement Working Actor Agent (2-3 hours)
**Goal**: Execute actions via ActionExecutor

**Implementation**:
- Extend BaseAgent with ActionExecutor integration
- Execute bash commands, mouse/keyboard actions
- Respond to coordinator commands
- Handle action results and errors

**Why second**: Completes basic ORA loop - enables agents to "act"

**File**: `src/agents/actor_agent.py`

**Quick Prototype**:
```python
from src.core.base_agent import BaseAgent
from src.core.action_executor import ActionExecutor, ActionPriority

class ActorAgent(BaseAgent):
    async def on_start(self):
        self.executor = ActionExecutor()

    async def process_message(self, message):
        if message['type'] == 'execute_action':
            result = await self.executor.execute_async(
                agent_id=self.agent_id,
                action=message['action'],
                priority=ActionPriority.NORMAL
            )
            return {
                'to': 'coordinator',
                'type': 'action_result',
                'result': result
            }
```

---

#### 3. Enhance Coordinator Agent (3-4 hours)
**Goal**: Task decomposition and routing

**Implementation**:
- Currently exists but needs task decomposition logic
- Add simple task → subtask breakdown
- Route subtasks to Observer/Actor
- Aggregate results and report completion

**Why third**: Enables actual multi-agent tasks - the "brain" of the swarm

**File**: `src/agents/coordinator.py` (enhance existing)

**Enhancements**:
- Parse user task into steps
- Determine which agent handles each step
- Track task progress
- Handle agent failures

---

## Phase 1: Working 3-Agent Swarm (Next 2-3 Days)

### Goal
Get ORA loop functional with real agents performing actual work

### Task Breakdown

#### Day 1: Agent Implementation
- **Morning**: Implement Observer agent (2-3 hours)
- **Afternoon**: Implement Actor agent (2-3 hours)
- **Evening**: Enhance Coordinator (2 hours)

#### Day 2: Integration & Testing
- **Morning**: Test Basic Swarm Flow (3 hours)
  - Simple task: "Take a screenshot and describe it"
  - Flow: Coordinator → Observer → Coordinator → Actor
  - Verify MessageBus communication
  - **Success metric**: Complete 1 simple task end-to-end

- **Afternoon**: Add Error Recovery (2 hours)
  - Handle agent timeouts
  - Retry failed actions
  - Graceful degradation
  - Logging and debugging

#### Day 3: Documentation & Examples
- **Morning**: Document Working Pattern (2 hours)
  - Example tasks that work
  - Agent interaction diagrams
  - Troubleshooting guide

- **Afternoon**: Create test suite (2 hours)
  - Unit tests for each agent
  - Integration tests for common flows
  - Performance benchmarks

### Success Criteria
- ✅ Observer can capture and send screenshots
- ✅ Actor can execute keyboard/mouse actions
- ✅ Coordinator can route tasks between agents
- ✅ At least 3 example tasks work end-to-end
- ✅ Error recovery prevents crashes
- ✅ Documentation enables others to add tasks

---

## Phase 2: Expand to 6 Agents (Week 2)

### From Trinity.md Priority

#### 1. Memory Manager Agent (Highest ROI)
**Timeline**: 2-3 days

**Implementation**:
- SQLite for long-term storage (conversation history, learnings)
- Redis for session state (current task context)
- Flash attention for context retrieval
- Save/restore state functions

**Why first**: Enables agents to learn and remember across sessions

**Components**:
- `src/agents/memory_manager.py`
- `src/memory/sqlite_store.py`
- `src/memory/redis_cache.py`
- `src/memory/flash_attention.py`

**Integration Points**:
- All agents can request memory lookups
- Coordinator stores task results
- Learner agent (Phase 3) uses for improvement

---

#### 2. Validator Agent (Critical for Safety)
**Timeline**: 2 days

**Implementation**:
- Review risky actions before execution
- Multi-agent consensus for high-risk operations
- Safety scoring integration (expand existing system)
- Block or warn on dangerous commands

**Why second**: Prevents disasters in autonomous mode

**Components**:
- `src/agents/validator_agent.py`
- Enhanced `src/config.py` safety scores
- Consensus protocol in MessageBus

**Safety Rules**:
- HIGH risk actions require validation
- Validator can veto dangerous operations
- Logs all reviewed actions
- Human override capability

---

#### 3. Analyzer Agent (Intelligence Multiplier)
**Timeline**: 2 days

**Implementation**:
- Process observations from Observer
- Extract patterns and insights
- Feed enhanced data to Coordinator/Reasoner
- Pattern recognition and anomaly detection

**Why third**: Better decision-making through analysis

**Components**:
- `src/agents/analyzer_agent.py`
- Pattern matching algorithms
- Anomaly detection
- Insight generation

**Use Cases**:
- Screen OCR and text extraction
- UI element detection
- Pattern recognition in logs
- Trend analysis

---

### Phase 2 Timeline
- **Week 2, Day 1-2**: Memory Manager
- **Week 2, Day 3-4**: Validator Agent
- **Week 2, Day 5**: Analyzer Agent
- **Week 2, Weekend**: Integration testing

---

## Phase 3: Full Pantheon (Week 3)

### Add Final 3 Agents

#### 4. Learner Agent
**Purpose**: Improve from mistakes and successes

**Capabilities**:
- Analyze task outcomes
- Store successful strategies in Memory
- Adjust behavior based on results
- Generate improvement proposals

**File**: `src/agents/learner_agent.py`

---

#### 5. Executor Agent
**Purpose**: Specialized for complex multi-step actions

**Capabilities**:
- Chain multiple actions atomically
- Handle complex workflows
- Rollback on failure
- Transaction-like guarantees

**File**: `src/agents/executor_agent.py`

---

#### 6. Resource Manager Agent
**Purpose**: Optimize agent allocation and performance

**Capabilities**:
- Monitor agent health and performance
- Allocate tasks based on agent load
- Spawn/stop agents dynamically
- Resource usage optimization

**File**: `src/agents/resource_manager.py`

---

### Phase 3 Architecture

```
Pantheon (9 Agents):

Core Loop (3):
├── Observer (sees)
├── Reasoner (thinks) → Coordinator enhanced
└── Actor (acts)

Intelligence Layer (3):
├── Analyzer (processes observations)
├── Memory Manager (remembers)
└── Validator (ensures safety)

Meta Layer (3):
├── Learner (improves)
├── Executor (complex workflows)
└── Resource Manager (optimizes)
```

---

## Trinity.md Integration Roadmap

### Week 1: Core ORA Working
- **Day 1-2**: Implement Observer, Actor, enhance Coordinator
- **Day 3**: Integration testing
- **Deliverable**: Working 3-agent swarm with real tasks

### Week 2: Intelligence + Safety
- **Day 1-2**: Memory Manager
- **Day 3-4**: Validator (safety first!)
- **Day 5**: Analyzer
- **Deliverable**: 6-agent swarm with memory and safety

### Week 3: Full Pantheon
- **Day 1-2**: Learner + Executor
- **Day 3**: Resource Manager
- **Day 4-5**: Integration, testing, optimization
- **Deliverable**: Full 9-agent Pantheon

### Week 4: Production Ready
- **Day 1-2**: Comprehensive testing
- **Day 3**: Documentation (README, diagrams, examples)
- **Day 4**: Docker optimizations
- **Day 5**: Deployment and demos

---

## Recommended Next Action

### Option 1: Implement Observer Agent (Recommended)
**Time**: 1-2 hours
**Impact**: Immediate - enables visual tasks
**Risk**: Low - uses existing ScreenObserver

**Command**:
```bash
# Create the agent
# Test with: python main.py --swarm --task "observe screen and report"
```

---

### Option 2: Create Detailed Implementation Plan
**Time**: 2-3 hours
**Impact**: Medium - clear roadmap for 4 weeks
**Risk**: Low - planning before coding

**Output**: Detailed technical specs for all 9 agents

---

### Option 3: Set Up Memory System First
**Time**: 4-6 hours
**Impact**: High - foundation for learning
**Risk**: Medium - more complex, needs Redis

**Why wait**: Better to have working agents before adding memory

---

## Effort Estimates

### Summary
- **Phase 1 (Working ORA)**: 20-24 hours (2-3 days)
- **Phase 2 (6 agents)**: 32-40 hours (1 week)
- **Phase 3 (Full Pantheon)**: 24-32 hours (1 week)
- **Phase 4 (Production)**: 16-24 hours (1 week)

**Total**: 60-80 hours over 3-4 weeks

### Breakdown by Component
- **Agent Implementation**: 35-40 hours
- **Memory System**: 12-15 hours
- **Testing**: 8-10 hours
- **Documentation**: 5-8 hours
- **Integration**: 10-12 hours

---

## Dependencies & Prerequisites

### Existing (Ready)
- ✅ AsyncIO foundation
- ✅ BaseAgent abstract class
- ✅ MessageBus (asyncio.Queue)
- ✅ ActionExecutor (thread-safe PyAutoGUI)
- ✅ ScreenObserver (async)
- ✅ GrokClient (async)

### New Dependencies Needed
- Redis (for Memory Manager) - Optional, can start with SQLite only
- Flash attention library - For memory context retrieval
- OCR library (pytesseract/easyocr) - For Analyzer agent

### Install When Needed
```bash
pip install redis
pip install pytesseract
pip install easyocr
```

---

## Success Metrics

### Phase 1 Success
- [ ] 3 agents communicate via MessageBus
- [ ] Complete 1 simple task end-to-end
- [ ] No crashes or deadlocks
- [ ] <5s task completion for simple operations

### Phase 2 Success
- [ ] Memory persists across sessions
- [ ] Validator prevents unsafe actions
- [ ] Analyzer extracts meaningful insights
- [ ] <10s task completion for moderate complexity

### Phase 3 Success
- [ ] 9 agents work in harmony
- [ ] Learner improves performance over time
- [ ] Resource Manager optimizes allocation
- [ ] <30s for complex multi-step tasks

### Production Success
- [ ] 95%+ reliability
- [ ] Comprehensive documentation
- [ ] Docker deployment works
- [ ] Community can extend with new agents

---

## Risk Mitigation

### Technical Risks
1. **Agent deadlocks** - Mitigated by DeadlockDetector
2. **Memory overhead** - Start with SQLite, add Redis only if needed
3. **Complexity** - Modular design, one agent at a time
4. **API costs** - Use caching, implement rate limiting

### Process Risks
1. **Scope creep** - Stick to trinity.md plan
2. **Over-engineering** - Ship MVP first, iterate
3. **Time estimates** - Build buffer into Week 4

---

## Next Steps - Immediate Actions

### Right Now (Next 1-2 Hours)
1. Create `src/agents/observer_agent.py`
2. Implement basic screen observation
3. Test with simple swarm task
4. Commit and push

### This Week
1. Complete Observer, Actor, Coordinator
2. Test end-to-end flow
3. Add error recovery
4. Document working examples

### Next Week
1. Implement Memory Manager
2. Add Validator for safety
3. Build Analyzer for intelligence
4. Integration testing

---

## Files to Create/Modify

### New Files
```
src/agents/observer_agent.py       (Phase 1)
src/agents/actor_agent.py          (Phase 1)
src/agents/analyzer_agent.py       (Phase 2)
src/agents/memory_manager.py       (Phase 2)
src/agents/validator_agent.py      (Phase 2)
src/agents/learner_agent.py        (Phase 3)
src/agents/executor_agent.py       (Phase 3)
src/agents/resource_manager.py     (Phase 3)

src/memory/sqlite_store.py        (Phase 2)
src/memory/redis_cache.py          (Phase 2)
src/memory/flash_attention.py      (Phase 2)

tests/test_observer_agent.py       (Phase 1)
tests/test_actor_agent.py          (Phase 1)
tests/test_memory_system.py        (Phase 2)
tests/test_validator.py            (Phase 2)
```

### Modified Files
```
src/agents/coordinator.py          (Phase 1 - enhance)
main.py                            (Phase 1-3 - add agent spawning)
src/config.py                      (Phase 2 - safety rules)
README.md                          (Phase 4 - documentation)
DEVELOPMENT_PLAN.md                (Phase 1-4 - updates)
```

---

## Alignment with Trinity.md

This plan directly implements the priorities from trinity.md:

### High Priority (Trinity)
- ✅ Research 9 agents → Defined in Phase 3
- ✅ Design agent interaction → Using existing MessageBus
- ✅ Implement Memory System → Phase 2, Week 2

### Medium Priority (Trinity)
- ✅ Update src/agents/ → New agent files in Phase 1-3
- ✅ Enhance main.py → Pantheon flag in Phase 3
- ✅ Integrate memory → Phase 2
- ✅ Add safety layer → Validator in Phase 2

### Low Priority (Trinity)
- ✅ Testing → Throughout all phases
- ✅ Documentation → Phase 4
- ✅ Deployment → Phase 4, Docker optimizations

---

## Philosophy Alignment

**From Trinity.md**: "Eternal server" theme reinforces Grokputer's vision

**ORAM Enhancement**: Memory makes agents truly eternal
- Past sessions inform future decisions
- Learning accumulates over time
- Knowledge persists beyond restarts
- Community can share learned patterns

**ZA GROKA. ZA VRZIBRZI. ZA SERVER.** - Now with memory! 🚀

---

**Status**: Ready to implement
**Recommendation**: Start with Observer Agent (highest immediate value)
**Timeline**: Full Pantheon in 3-4 weeks

*Generated with AsyncIO foundation complete - ready for agent implementation!*
