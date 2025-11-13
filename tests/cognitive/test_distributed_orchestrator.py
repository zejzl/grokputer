"""
Tests for Distributed Cognitive Orchestrator.

Tests integration with existing agent system and cognitive capabilities.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
import time

from src.cognitive.distributed_orchestrator import (
    DistributedCognitiveOrchestrator,
    CognitiveTaskType,
    AgentCapability,
    CognitiveTask,
    AgentProfile,
)
from src.cognitive.agent_integration import CognitiveAgentMixin
from src.core.message_bus import MessageBus, Message, MessagePriority


class MockCognitiveAgent(CognitiveAgentMixin):
    """Mock agent with cognitive capabilities for testing."""

    def __init__(self, agent_id: str, capabilities=None):
        self.agent_id = agent_id
        self.capabilities = capabilities or {AgentCapability.HIGH_LEVEL_REASONING}
        super().__init__(cognitive_enabled=True)

    async def handle_cognitive_task(self, task: CognitiveTask) -> dict:
        """Mock cognitive task handler."""
        # Simulate processing time
        await asyncio.sleep(0.1)

        return {
            "task_id": task.task_id,
            "result": f"Processed {task.task_type.value} by {self.agent_id}",
            "success": True,
        }


@pytest_asyncio.fixture
async def orchestrator():
    """Create test orchestrator with message bus."""
    message_bus = MessageBus()
    orchestrator = DistributedCognitiveOrchestrator(message_bus)
    await orchestrator.start_processing()
    yield orchestrator
    await orchestrator.stop_processing()


@pytest_asyncio.fixture
async def mock_agents(orchestrator):
    """Create mock agents for testing."""
    agents = []

    # Register agents with message bus first
    orchestrator.message_bus.register_agent("coordinator")
    orchestrator.message_bus.register_agent("analyzer")
    orchestrator.message_bus.register_agent("validator")

    # Create coordinator agent
    coordinator = MockCognitiveAgent(
        "coordinator", {AgentCapability.HIGH_LEVEL_REASONING, AgentCapability.OPTIMIZATION_PLANNING}
    )
    await orchestrator.register_agent(
        "coordinator", coordinator.capabilities, {CognitiveTaskType.REASONING: 0.8, CognitiveTaskType.OPTIMIZATION: 0.7}
    )
    agents.append(coordinator)

    # Create analyzer agent
    analyzer = MockCognitiveAgent(
        "analyzer", {AgentCapability.PATTERN_RECOGNITION, AgentCapability.VALIDATION_CHECKING}
    )
    await orchestrator.register_agent(
        "analyzer", analyzer.capabilities, {CognitiveTaskType.ANALYSIS: 0.9, CognitiveTaskType.VALIDATION: 0.8}
    )
    agents.append(analyzer)

    # Create validator agent
    validator = MockCognitiveAgent(
        "validator", {AgentCapability.VALIDATION_CHECKING, AgentCapability.LEARNING_ADAPTATION}
    )
    await orchestrator.register_agent(
        "validator", validator.capabilities, {CognitiveTaskType.VALIDATION: 0.9, CognitiveTaskType.LEARNING: 0.6}
    )
    agents.append(validator)

    yield agents


@pytest.mark.asyncio
async def test_agent_registration(orchestrator, mock_agents):
    """Test agent registration with the orchestrator."""
    status = await orchestrator.get_orchestration_status()

    assert status["active_agents"] == 3
    assert "coordinator" in status["agent_status"]
    assert "analyzer" in status["agent_status"]
    assert "validator" in status["agent_status"]

    # Check capabilities
    coordinator_status = status["agent_status"]["coordinator"]
    assert "high_level_reasoning" in coordinator_status["capabilities"]
    assert "optimization_planning" in coordinator_status["capabilities"]


@pytest.mark.asyncio
async def test_task_submission_and_assignment(orchestrator, mock_agents):
    """Test submitting and assigning cognitive tasks."""
    # Submit a reasoning task
    task_id = await orchestrator.submit_cognitive_task(
        CognitiveTaskType.REASONING,
        {"query": "Analyze system performance patterns"},
        required_capabilities={AgentCapability.HIGH_LEVEL_REASONING},
    )

    assert task_id.startswith("cognitive_")

    # Check task was created and assigned
    assert task_id in orchestrator.active_tasks
    task = orchestrator.active_tasks[task_id]
    assert task.task_type == CognitiveTaskType.REASONING
    assert task.status == "processing"  # Task should be assigned immediately
    assert task.assigned_agent == "coordinator"  # Should be assigned to coordinator

    # Check orchestration status
    status = await orchestrator.get_orchestration_status()
    assert status["active_tasks"] == 1
    assert status["pending_tasks"] == 0


@pytest.mark.asyncio
async def test_consensus_task_creation(orchestrator, mock_agents):
    """Test creating consensus-based tasks."""
    consensus_id = await orchestrator.create_consensus_task(
        CognitiveTaskType.ANALYSIS,
        {"data": "performance_metrics", "question": "What are the bottlenecks?"},
        num_agents=3,
        consensus_threshold=0.7,
    )

    assert consensus_id.startswith("consensus_")
    assert consensus_id in orchestrator.consensus_tasks

    consensus_data = orchestrator.consensus_tasks[consensus_id]
    assert len(consensus_data["agent_tasks"]) == 3
    assert consensus_data["threshold"] == 0.7
    assert consensus_data["status"] == "waiting"


@pytest.mark.asyncio
async def test_agent_specialization_tracking(orchestrator, mock_agents):
    """Test agent specialization score updates."""
    # Get initial specialization score
    initial_score = orchestrator.agent_profiles["coordinator"].specialization_score.get(
        CognitiveTaskType.REASONING, 0.5
    )
    assert initial_score == 0.8  # Set during registration

    # Simulate task completion with good performance
    orchestrator.update_agent_specialization("coordinator", CognitiveTaskType.REASONING, 1.0)

    # Score should improve
    updated_score = orchestrator.agent_profiles["coordinator"].specialization_score[CognitiveTaskType.REASONING]
    assert updated_score > initial_score

    # Simulate poor performance
    orchestrator.update_agent_specialization("coordinator", CognitiveTaskType.REASONING, 0.0)

    # Score should decrease
    final_score = orchestrator.agent_profiles["coordinator"].specialization_score[CognitiveTaskType.REASONING]
    assert final_score < updated_score


@pytest.mark.asyncio
async def test_performance_reporting(orchestrator, mock_agents):
    """Test agent performance report generation."""
    # Add some mock performance history
    profile = orchestrator.agent_profiles["analyzer"]
    profile.performance_history = [
        {"task_type": "analysis", "completion_time": 1.0, "success": True, "estimated_time": 1.2},
        {"task_type": "analysis", "completion_time": 0.8, "success": True, "estimated_time": 1.0},
        {"task_type": "validation", "completion_time": 2.0, "success": False, "estimated_time": 1.5},
    ]

    report = await orchestrator.get_agent_performance_report("analyzer")

    assert report["agent_id"] == "analyzer"
    assert report["total_tasks"] == 3
    assert report["success_rate"] == 2 / 3  # 2 out of 3 successful
    assert "average_completion_time" in report
    assert "specialization_scores" in report


@pytest.mark.asyncio
async def test_cognitive_pipeline_creation(orchestrator, mock_agents):
    """Test creating cognitive processing pipelines."""
    pipeline_tasks = [
        {
            "type": CognitiveTaskType.REASONING,
            "content": {"task": "analyze problem"},
            "capabilities": {AgentCapability.HIGH_LEVEL_REASONING},
        },
        {
            "type": CognitiveTaskType.ANALYSIS,
            "content": {"task": "deep analysis", "depends_on": "reasoning_result"},
            "dependencies": ["0"],  # Depends on first task
            "capabilities": {AgentCapability.PATTERN_RECOGNITION},
        },
        {
            "type": CognitiveTaskType.VALIDATION,
            "content": {"task": "validate results", "depends_on": "analysis_result"},
            "dependencies": ["1"],  # Depends on second task
            "capabilities": {AgentCapability.VALIDATION_CHECKING},
        },
    ]

    pipeline_id = await orchestrator.create_cognitive_pipeline("test_pipeline", pipeline_tasks)

    assert pipeline_id.startswith("pipeline_")

    # Check that tasks were created
    status = await orchestrator.get_orchestration_status()

    # The first task should be processing, others should be pending due to dependencies
    assert status["active_tasks"] == 1  # First task assigned
    assert status["pending_tasks"] == 2  # Two tasks waiting for dependencies


@pytest.mark.asyncio
async def test_load_balancing(orchestrator, mock_agents):
    """Test load balancing across agents."""
    # Submit multiple tasks to test load distribution
    task_ids = []
    for i in range(5):
        task_id = await orchestrator.submit_cognitive_task(
            CognitiveTaskType.REASONING,
            {"query": f"Task {i}"},
            required_capabilities={AgentCapability.HIGH_LEVEL_REASONING},
        )
        task_ids.append(task_id)

    # Check load distribution
    status = await orchestrator.get_orchestration_status()
    agent_loads = {agent_id: info["load"] for agent_id, info in status["agent_status"].items()}

    # At least one agent should have some load
    assert any(load > 0 for load in agent_loads.values())

    # Total load should be reasonable
    total_load = sum(agent_loads.values())
    assert total_load > 0


@pytest.mark.asyncio
async def test_performance_benchmarking(orchestrator, mock_agents):
    """Benchmark orchestrator performance with multiple concurrent tasks."""
    import time

    # Submit multiple tasks to test performance
    num_tasks = 10  # Reduced for test
    start_time = time.time()

    task_ids = []
    for i in range(num_tasks):
        task_id = await orchestrator.submit_cognitive_task(
            CognitiveTaskType.REASONING if i % 2 == 0 else CognitiveTaskType.ANALYSIS,
            {"query": f"Task {i} performance benchmark"},
            required_capabilities=(
                {AgentCapability.HIGH_LEVEL_REASONING} if i % 2 == 0 else {AgentCapability.PATTERN_RECOGNITION}
            ),
        )
        task_ids.append(task_id)

    submission_time = time.time() - start_time

    # Simulate task completion by sending result messages
    processing_start = time.time()
    for i, task_id in enumerate(task_ids):
        # Simulate processing delay
        await asyncio.sleep(0.01)

        # Send completion message
        result_message = Message(
            from_agent="coordinator" if i % 2 == 0 else "analyzer",
            to_agent="cognitive_orchestrator",
            message_type="cognitive_task_result",
            content={"task_id": task_id, "result": f"Completed task {i}", "success": True},
        )
        await orchestrator.message_bus.send(result_message)

    processing_time = time.time() - processing_start

    # Wait for orchestrator to process results
    await asyncio.sleep(0.1)

    # Check performance metrics
    status = await orchestrator.get_orchestration_status()

    # Calculate metrics
    tasks_processed = status["total_tasks_processed"]
    total_time = submission_time + processing_time
    throughput = tasks_processed / max(total_time, 0.1)  # tasks per second

    # Check load distribution
    agent_loads = {agent_id: info["load"] for agent_id, info in status["agent_status"].items()}
    active_loads = [load for load in agent_loads.values() if load > 0]
    if active_loads:
        max_load = max(active_loads)
        min_load = min(active_loads)
        load_balance_ratio = min_load / max(max_load, 0.1)  # Higher is better balance
    else:
        load_balance_ratio = 1.0

    print(f"Performance metrics: throughput={throughput:.2f} tasks/sec, load_balance={load_balance_ratio:.2f}")
    print(f"Tasks processed: {tasks_processed}/{num_tasks}, total_time: {total_time:.3f}s")

    # Assertions
    assert tasks_processed == num_tasks  # All tasks should be processed
    assert throughput > 5  # Should handle at least 5 tasks per second
    assert status["active_agents"] == 3  # All agents active


@pytest.mark.asyncio
async def test_hierarchical_memory_integration(orchestrator, mock_agents):
    """Test hierarchical memory integration with cognitive orchestrator."""
    # Submit a task and simulate completion to test memory storage
    task_id = await orchestrator.submit_cognitive_task(
        CognitiveTaskType.REASONING,
        {"query": "Test memory integration"},
        required_capabilities={AgentCapability.HIGH_LEVEL_REASONING},
    )

    # Simulate task completion
    result_message = Message(
        from_agent="coordinator",
        to_agent="cognitive_orchestrator",
        message_type="cognitive_task_result",
        content={"task_id": task_id, "result": {"analysis": "memory test complete"}, "success": True},
    )
    await orchestrator.message_bus.send(result_message)

    # Wait for processing
    await asyncio.sleep(0.1)

    # Check that memory was stored
    memory_stats = orchestrator.get_memory_stats()
    assert "short_term" in memory_stats
    assert "context" in memory_stats
    assert "fusion_weights" in memory_stats

    # Test memory retrieval
    context = orchestrator.retrieve_task_context("coordinator", CognitiveTaskType.REASONING)
    assert isinstance(context, list)

    # Submit another similar task to test context retrieval
    task_id2 = await orchestrator.submit_cognitive_task(
        CognitiveTaskType.REASONING,
        {"query": "Similar reasoning task"},
        required_capabilities={AgentCapability.HIGH_LEVEL_REASONING},
    )

    # Check that context was included in task assignment
    # (This would be verified by checking the message content in a real scenario)

    # Test memory consolidation
    consolidation_stats = orchestrator.memory_backend.consolidate("coordinator")
    assert isinstance(consolidation_stats, dict)


@pytest.mark.asyncio
async def test_scalability_50_tasks(orchestrator, mock_agents):
    """Test scalability with 50+ concurrent cognitive tasks."""
    import time

    num_tasks = 50
    start_time = time.time()

    # Submit 50 tasks with different types and complexities
    task_ids = []
    for i in range(num_tasks):
        # Alternate between different task types and complexities
        task_type = (
            CognitiveTaskType.REASONING
            if i % 3 == 0
            else (CognitiveTaskType.ANALYSIS if i % 3 == 1 else CognitiveTaskType.VALIDATION)
        )

        # Vary complexity
        complexity = 1.0 + (i % 3) * 0.5  # 1.0, 1.5, 2.0

        task_id = await orchestrator.submit_cognitive_task(
            task_type,
            {"query": f"Scalability test task {i}", "complexity_factor": complexity},
            required_capabilities=(
                {AgentCapability.HIGH_LEVEL_REASONING}
                if i % 3 == 0
                else ({AgentCapability.PATTERN_RECOGNITION} if i % 3 == 1 else {AgentCapability.VALIDATION_CHECKING})
            ),
            estimated_complexity=complexity,
        )
        task_ids.append(task_id)

    submission_time = time.time() - start_time

    # Simulate processing with some delay to test queuing
    processing_start = time.time()
    processed_count = 0

    for i, task_id in enumerate(task_ids):
        # Simulate variable processing times
        processing_delay = 0.01 + (i % 5) * 0.005  # 0.01 to 0.035 seconds
        await asyncio.sleep(processing_delay)

        # Send completion message
        agent_for_task = "coordinator" if i % 3 == 0 else ("analyzer" if i % 3 == 1 else "validator")
        result_message = Message(
            from_agent=agent_for_task,
            to_agent="cognitive_orchestrator",
            message_type="cognitive_task_result",
            content={"task_id": task_id, "result": f"Completed scalability task {i}", "success": True},
        )
        await orchestrator.message_bus.send(result_message)
        processed_count += 1

    processing_time = time.time() - processing_start

    # Wait for orchestrator to process all results
    await asyncio.sleep(0.2)

    # Check final status
    status = await orchestrator.get_orchestration_status()

    # Calculate metrics
    tasks_processed = status["total_tasks_processed"]
    total_time = submission_time + processing_time
    throughput = tasks_processed / max(total_time, 0.1)

    # Check load distribution
    agent_loads = {agent_id: info["load"] for agent_id, info in status["agent_status"].items()}
    avg_load = sum(agent_loads.values()) / len(agent_loads) if agent_loads else 0
    load_variance = (
        sum((load - avg_load) ** 2 for load in agent_loads.values()) / len(agent_loads) if agent_loads else 0
    )

    print(f"Scalability test results:")
    print(f"  Tasks processed: {tasks_processed}/{num_tasks}")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Throughput: {throughput:.2f} tasks/sec")
    print(f"  Load variance: {load_variance:.4f}")
    print(f"  Agent loads: {agent_loads}")

    # Assertions for scalability
    assert tasks_processed == num_tasks, f"Expected {num_tasks} tasks, got {tasks_processed}"
    assert throughput > 10, f"Throughput too low: {throughput:.2f} tasks/sec"
    assert load_variance < 0.5, f"Load imbalance too high: {load_variance:.4f}"
    assert all(load >= 0 for load in agent_loads.values()), "Invalid load values"
    assert status["active_agents"] == 3, "Not all agents active"
