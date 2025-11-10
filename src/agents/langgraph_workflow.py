"""
LangGraph Integration for Grokputer Agent Workflows
Simple graph: Planner -> Coder -> Tester (with retry loop on failure).
State shared via dict; integrates with MessageBus for events.
"""

from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator
from src.core.message_bus import MessageBus  # Existing bus
from src.core.action_executor import ActionExecutor  # For coder actions
import logging

logger = logging.getLogger(__name__)

# State schema (shared across nodes)
class AgentState(TypedDict):
    task: str  # Original task
    sub_tasks: list[str]  # From planner
    code_actions: list[Dict]  # From coder (tool calls)
    test_results: list[Dict]  # From tester
    messages: Annotated[list, add_messages]  # Chat history
    error: str  # For failures
    converged: bool  # End condition

# Stub agents (integrate real ones later; use existing stubs)
def planner_node(state: AgentState) -> AgentState:
    """Planner: Decompose task into sub-tasks."""
    logger.info("[LANGGRAPH] Planner: Decomposing task")
    # Simulate decomposition (real: Use Grok/Claude via client)
    sub_tasks = [
        f"Sub-task 1: {state['task']} - Plan step",
        f"Sub-task 2: {state['task']} - Implement",
        f"Sub-task 3: {state['task']} - Validate"
    ]
    state['sub_tasks'] = sub_tasks
    state['messages'].append({"role": "planner", "content": f"Planned: {sub_tasks}"})
    bus = MessageBus()  # Existing bus for events
    bus.broadcast({"type": "plan_complete", "sub_tasks": sub_tasks})  # Broadcast
    return state

def coder_node(state: AgentState) -> AgentState:
    """Coder: Execute actions for each sub-task."""
    logger.info("[LANGGRAPH] Coder: Executing actions")
    executor = ActionExecutor()  # Existing secure executor
    actions = []
    for sub in state['sub_tasks']:
        # Simulate tool call (real: Grok tool_calls)
        action = {"sub_task": sub, "tool": "bash", "command": "echo 'Executing: ' + sub[:20]"}
        result = executor.execute_tool_calls([action])  # Secure exec
        actions.append({"action": action, "result": result[0]})
    state['code_actions'] = actions
    state['messages'].append({"role": "coder", "content": f"Executed {len(actions)} actions"})
    bus = MessageBus()
    bus.broadcast({"type": "code_complete", "actions": len(actions)})
    return state

def tester_node(state: AgentState) -> AgentState:
    """Tester: Validate results; set converged or error."""
    logger.info("[LANGGRAPH] Tester: Validating")
    errors = []
    for action in state['code_actions']:
        if action['result'][0].get('status') != 'success':
            errors.append(f"Failed: {action['sub_task'][:30]}")
    if errors:
        state['error'] = "; ".join(errors)
        state['converged'] = False
        state['messages'].append({"role": "tester", "content": f"Failures: {len(errors)} - Retry needed"})
        bus = MessageBus()
        bus.broadcast({"type": "test_fail", "errors": len(errors)})
        return "coder"  # Conditional: Loop to coder
    state['converged'] = True
    state['messages'].append({"role": "tester", "content": "All tests passed"})
    bus = MessageBus()
    bus.broadcast({"type": "test_success", "converged": True})
    return END

# Build graph
def create_workflow_graph(task: str) -> StateGraph:
    workflow = StateGraph(state_schema=AgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("tester", tester_node)
    
    # Edges: Sequential with conditional retry
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "coder")
    workflow.add_conditional_edges(
        "coder",
        lambda s: "tester" if s.get('code_actions') else END,
        {"tester": "tester"}
    )
    workflow.add_conditional_edges(
        "tester",
        lambda s: "coder" if not s.get('converged', True) else END,
        {"coder": "coder", END: END}
    )
    
    return workflow.compile()

# Run function (integrate into swarm)
async def run_langgraph_workflow(task: str, bus: MessageBus = None):
    """Run the graph; optional bus for events."""
    graph = create_workflow_graph(task)
    initial_state = {
        "task": task,
        "sub_tasks": [],
        "code_actions": [],
        "test_results": [],
        "messages": [],
        "error": "",
        "converged": False
    }
    final_state = graph.invoke(initial_state)
    logger.info(f"[LANGGRAPH] Workflow complete: {final_state['converged']}")
    if bus:
        bus.broadcast({"type": "workflow_complete", "state": final_state})
    return final_state
