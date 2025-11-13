# Must Fix Issues

## Critical Code Errors

### 1. Pantheon Mode - ValidatorAgent Implementation ✅ FIXED
**Status:** Completed - ValidatorAgent implemented and working
**Details:**
- Created `ValidatorAgent` class inheriting from `BaseAgent`
- Added validation for task outputs (error detection, success status, required fields)
- Added safety checks for dangerous commands and data exposure
- Agent registers with MessageBus and processes validation requests
- Fixed import paths for `BaseAgent` in multiple agent files

**Remaining:** PantheonCoordinator requires all 9 agents - need to implement remaining 5

### 2. Incomplete Pantheon Architecture
**Location:** `main.py` `_run_pantheon_mode()`
**Details:**
- Code mentions 9-agent system but only implements 4 agents (Observer, Coordinator, Actor, Validator)
- Missing agents: Learner, Memory Manager, Executor, Analyzer, Improver
- PantheonCoordinator initializes with only 4 agents
- **Impact:** Full 9-agent workflow not available

**Fix Required:**
- Implement remaining 5 agents with BaseAgent inheritance
- Update PantheonCoordinator to handle all 9 agents
- Define agent roles and message flows

### 3. API Key Validation Issues
**Location:** Various (boot sequence, collaboration, swarm)
**Error:** Invalid XAI API key causes all modes to fail
**Details:**
- API key validation happens during boot/connection test
- Single agent mode exits immediately on API failure
- Swarm/collaboration modes fail during task execution
- No fallback to offline/local mode when API unavailable

**Fix Required:**
- Add graceful API failure handling
- Implement offline mode fallback
- Better error messages for API key issues

## Minor Issues

### 4. Duplicate ValidatorAgent Classes
**Location:** `src/agents/validator.py`
**Details:** Two identical `ValidatorAgent` classes defined in same file (lines 108 and 367)
**Fix:** Remove duplicate class definition

### 5. Missing Agent Registrations
**Location:** Various agent `__init__` methods
**Details:** Some agents don't register with MessageBus automatically
**Status:** Fixed for Coordinator and ActorAgent in recent commits

## Testing Status
- ✅ Swarm mode: Working (agent communication fixed)
- ❌ Pantheon mode: Fails on ValidatorAgent
- ❌ Collaboration mode: Fails on API key
- ❌ Single agent mode: Fails on API key during boot

## Priority
1. Implement ValidatorAgent for Pantheon mode
2. Fix API key validation/fallback
3. Complete remaining Pantheon agents
4. Clean up duplicate code