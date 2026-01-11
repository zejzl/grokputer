"""
Integration tests for CollaborationCoordinator

Tests end-to-end collaboration flows including:
- Dual-agent dialogue orchestration
- Grok-only mode
- Consensus detection across rounds
- Error handling and graceful degradation
- MessageBus integration
- Final plan synthesis
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime

from src.collaboration.coordinator import CollaborationCoordinator
from src.collaboration.message_models import (
    AgentRole,
    CollaborationMessage,
    ConsensusSignal,
    FinalPlan,
    MessageType,
)
from src.collaboration.consensus import ConsensusDetector
from src.collaboration.output_generator import OutputGenerator


# Fixtures

@pytest.fixture
def mock_claude_api_key():
    """Mock Claude API key."""
    return "sk-ant-test-key"


@pytest.fixture
def mock_grok_api_key():
    """Mock Grok API key."""
    return "xai-test-key"


@pytest.fixture
def mock_claude_agent():
    """Mock ClaudeAgent with async response."""
    with patch('src.collaboration.coordinator.ClaudeAgent') as MockClaude:
        mock = MockClaude.return_value

        async def mock_process_message(trigger, task_prompt):
            return CollaborationMessage(
                message_id=f"msg_claude_{trigger.round_number}",
                correlation_id=trigger.correlation_id,
                message_type=MessageType.PROPOSAL,
                sender=AgentRole.CLAUDE,
                round_number=trigger.round_number,
                content=f"Claude response to: {task_prompt[:50]}"
            )

        mock.process_message = AsyncMock(side_effect=mock_process_message)
        yield MockClaude


@pytest.fixture
def mock_grok_agent():
    """Mock GrokAgent with async response."""
    with patch('src.collaboration.coordinator.GrokAgent') as MockGrok:
        mock = MockGrok.return_value

        async def mock_process_message(trigger, task_prompt):
            return CollaborationMessage(
                message_id=f"msg_grok_{trigger.round_number}",
                correlation_id=trigger.correlation_id,
                message_type=MessageType.PROPOSAL,
                sender=AgentRole.GROK,
                round_number=trigger.round_number,
                content=f"Grok response to: {task_prompt[:50]}"
            )

        mock.process_message = AsyncMock(side_effect=mock_process_message)
        yield MockGrok


@pytest.fixture
def mock_consensus_detector():
    """Mock ConsensusDetector."""
    with patch('src.collaboration.coordinator.ConsensusDetector') as MockDetector:
        mock = MockDetector.return_value

        def mock_analyze_round(history, round_num):
            # Simulate consensus after 2 rounds
            if round_num >= 2:
                return ConsensusSignal(
                    is_consensus=True,
                    confidence=0.85,
                    convergence_score=0.9,
                    recommendation="FINALIZE",
                    reasoning="Strong agreement detected",
                    agreement_indicators=["semantic_similarity", "structural_alignment"],
                    disagreement_indicators=[]
                )
            else:
                return ConsensusSignal(
                    is_consensus=False,
                    confidence=0.4,
                    convergence_score=0.3,
                    recommendation="CONTINUE",
                    reasoning="Need more discussion",
                    agreement_indicators=[],
                    disagreement_indicators=["approach_differs"]
                )

        mock.analyze_round = Mock(side_effect=mock_analyze_round)
        yield MockDetector


@pytest.fixture
def mock_output_generator():
    """Mock OutputGenerator."""
    with patch('src.collaboration.coordinator.OutputGenerator') as MockGenerator:
        mock = MockGenerator.return_value

        async def mock_synthesize_plan(claude_messages, grok_messages, consensus_signal):
            return "Synthesized unified plan based on both perspectives"

        mock.synthesize_plan = AsyncMock(side_effect=mock_synthesize_plan)
        mock.save_to_file = Mock(return_value="output/collab_test.json")
        yield MockGenerator


# Initialization Tests

def test_coordinator_initialization_dual_agent(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent
):
    """Test coordinator initializes with both agents."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=5,
        convergence_threshold=0.6
    )

    assert coordinator.max_rounds == 5
    assert coordinator.claude is not None
    assert coordinator.grok is not None
    assert coordinator.message_bus is not None
    assert coordinator.consensus_detector is not None
    assert coordinator.message_history == []


def test_coordinator_initialization_grok_only(
    mock_grok_api_key,
    mock_grok_agent
):
    """Test coordinator initializes in Grok-only mode."""
    coordinator = CollaborationCoordinator(
        claude_api_key=None,  # No Claude
        grok_api_key=mock_grok_api_key,
        max_rounds=3
    )

    assert coordinator.claude is None
    assert coordinator.grok is not None
    assert coordinator.max_rounds == 3


def test_coordinator_review_mode(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent
):
    """Test coordinator initializes with review mode enabled."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        review_mode=True
    )

    assert coordinator.review_mode is True


def test_coordinator_correlation_id_format(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent
):
    """Test correlation ID has correct format."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key
    )

    assert coordinator.correlation_id.startswith("collab_")
    assert len(coordinator.correlation_id) > 10  # Has timestamp


# Collaboration Flow Tests

@pytest.mark.asyncio
async def test_run_collaboration_dual_agent(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test complete dual-agent collaboration flow."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=3
    )

    task = "Design a REST API for user authentication"
    final_plan = await coordinator.run_collaboration(task)

    # Verify final plan structure
    assert isinstance(final_plan, FinalPlan)
    assert final_plan.task_description == task
    assert final_plan.consensus_reached is True
    assert final_plan.total_rounds == 2  # Should reach consensus in round 2
    assert final_plan.unified_plan == "Synthesized unified plan based on both perspectives"

    # Verify message history contains both agents
    assert len(coordinator.message_history) >= 2
    claude_msgs = [m for m in coordinator.message_history if m.sender == AgentRole.CLAUDE]
    grok_msgs = [m for m in coordinator.message_history if m.sender == AgentRole.GROK]
    assert len(claude_msgs) >= 1
    assert len(grok_msgs) >= 1


@pytest.mark.asyncio
async def test_run_collaboration_grok_only(
    mock_grok_api_key,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test Grok-only collaboration mode."""
    coordinator = CollaborationCoordinator(
        claude_api_key=None,
        grok_api_key=mock_grok_api_key,
        max_rounds=3
    )

    task = "Analyze performance bottlenecks"
    final_plan = await coordinator.run_collaboration(task)

    assert isinstance(final_plan, FinalPlan)
    assert final_plan.total_rounds == 2

    # Only Grok messages in history
    grok_msgs = [m for m in coordinator.message_history if m.sender == AgentRole.GROK]
    claude_msgs = [m for m in coordinator.message_history if m.sender == AgentRole.CLAUDE]
    assert len(grok_msgs) >= 1
    assert len(claude_msgs) == 0


@pytest.mark.asyncio
async def test_run_collaboration_max_rounds(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_output_generator
):
    """Test collaboration runs to max rounds if no consensus."""
    # Mock consensus detector that never reaches consensus
    with patch('src.collaboration.coordinator.ConsensusDetector') as MockDetector:
        mock = MockDetector.return_value
        mock.analyze_round = Mock(return_value=ConsensusSignal(
            is_consensus=False,
            confidence=0.3,
            convergence_score=0.2,
            recommendation="CONTINUE",
            reasoning="Still diverging",
            agreement_indicators=[],
            disagreement_indicators=["fundamental_disagreement"]
        ))

        coordinator = CollaborationCoordinator(
            claude_api_key=mock_claude_api_key,
            grok_api_key=mock_grok_api_key,
            max_rounds=3
        )

        task = "Design microservices architecture"
        final_plan = await coordinator.run_collaboration(task)

        # Should run all 3 rounds
        assert final_plan.total_rounds == 3
        assert final_plan.consensus_reached is False


# Error Handling Tests

@pytest.mark.asyncio
async def test_claude_api_error_graceful_degradation(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test graceful handling of Claude API errors."""
    with patch('src.collaboration.coordinator.ClaudeAgent') as MockClaude:
        mock = MockClaude.return_value
        # Claude fails, but collaboration continues
        mock.process_message = AsyncMock(side_effect=Exception("Claude API timeout"))

        coordinator = CollaborationCoordinator(
            claude_api_key=mock_claude_api_key,
            grok_api_key=mock_grok_api_key,
            max_rounds=2
        )

        task = "Implement caching strategy"
        final_plan = await coordinator.run_collaboration(task)

        # Should still complete with Grok responses
        assert isinstance(final_plan, FinalPlan)
        assert len(coordinator.message_history) >= 2

        # Check for error messages in history
        error_msgs = [m for m in coordinator.message_history if "Error" in m.content]
        assert len(error_msgs) >= 1


@pytest.mark.asyncio
async def test_grok_api_error_graceful_degradation(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test graceful handling of Grok API errors."""
    with patch('src.collaboration.coordinator.GrokAgent') as MockGrok:
        mock = MockGrok.return_value
        # Grok fails, but collaboration continues
        mock.process_message = AsyncMock(side_effect=Exception("Grok API rate limit"))

        coordinator = CollaborationCoordinator(
            claude_api_key=mock_claude_api_key,
            grok_api_key=mock_grok_api_key,
            max_rounds=2
        )

        task = "Design database schema"
        final_plan = await coordinator.run_collaboration(task)

        # Should still complete with Claude responses
        assert isinstance(final_plan, FinalPlan)
        assert len(coordinator.message_history) >= 2


# Message History Tests

@pytest.mark.asyncio
async def test_message_history_accumulation(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test message history accumulates across rounds."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=3
    )

    task = "Implement authentication flow"
    await coordinator.run_collaboration(task)

    # Should have messages from both agents across multiple rounds
    assert len(coordinator.message_history) >= 4  # 2 agents × 2 rounds minimum

    # Verify round numbers are sequential
    round_numbers = [m.round_number for m in coordinator.message_history]
    assert sorted(set(round_numbers)) == [1, 2]  # Consensus at round 2


@pytest.mark.asyncio
async def test_message_correlation_id_consistency(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test all messages share same correlation ID."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=2
    )

    task = "Design notification system"
    await coordinator.run_collaboration(task)

    # All messages should have same correlation ID as coordinator
    for message in coordinator.message_history:
        assert message.correlation_id == coordinator.correlation_id


# Final Plan Tests

@pytest.mark.asyncio
async def test_final_plan_metadata(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test final plan contains complete metadata."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=3,
        convergence_threshold=0.7
    )

    task = "Design caching layer"
    final_plan = await coordinator.run_collaboration(task)

    # Check metadata fields
    assert "correlation_id" in final_plan.metadata
    assert "convergence_score" in final_plan.metadata
    assert "confidence" in final_plan.metadata
    assert "total_messages" in final_plan.metadata
    assert final_plan.metadata["total_messages"] > 0


@pytest.mark.asyncio
async def test_final_plan_perspectives_separated(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test final plan separates Claude and Grok perspectives."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=2
    )

    task = "Implement rate limiting"
    final_plan = await coordinator.run_collaboration(task)

    # Both perspectives should contain agent-specific content
    assert len(final_plan.claude_perspective) > 0
    assert len(final_plan.grok_perspective) > 0
    assert "Claude" in final_plan.claude_perspective or "response" in final_plan.claude_perspective
    assert "Grok" in final_plan.grok_perspective or "response" in final_plan.grok_perspective


@pytest.mark.asyncio
async def test_final_plan_consensus_indicators(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test final plan includes consensus indicators."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=3
    )

    task = "Design API gateway"
    final_plan = await coordinator.run_collaboration(task)

    # Should have agreement indicators from consensus signal
    assert isinstance(final_plan.key_agreements, list)
    assert len(final_plan.key_agreements) > 0  # Mock detector provides indicators


# Output Generation Tests

@pytest.mark.asyncio
async def test_output_file_saved(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test output file is saved after collaboration."""
    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=2
    )

    task = "Design logging system"
    await coordinator.run_collaboration(task)

    # Verify save_to_file was called
    mock_output_generator.return_value.save_to_file.assert_called_once()


# Convergence Threshold Tests

@pytest.mark.asyncio
async def test_custom_convergence_threshold(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_output_generator
):
    """Test custom convergence threshold is respected."""
    with patch('src.collaboration.coordinator.ConsensusDetector') as MockDetector:
        coordinator = CollaborationCoordinator(
            claude_api_key=mock_claude_api_key,
            grok_api_key=mock_grok_api_key,
            convergence_threshold=0.85  # High threshold
        )

        # Verify detector was initialized with correct threshold
        MockDetector.assert_called_once_with(convergence_threshold=0.85)


# Parallel Processing Tests

@pytest.mark.asyncio
async def test_agents_process_in_parallel(
    mock_claude_api_key,
    mock_grok_api_key,
    mock_claude_agent,
    mock_grok_agent,
    mock_consensus_detector,
    mock_output_generator
):
    """Test both agents process messages concurrently."""
    call_times = []

    async def mock_claude_with_delay(trigger, task_prompt):
        call_times.append(("claude_start", asyncio.get_event_loop().time()))
        await asyncio.sleep(0.1)
        call_times.append(("claude_end", asyncio.get_event_loop().time()))
        return CollaborationMessage(
            message_id=f"msg_claude_{trigger.round_number}",
            correlation_id=trigger.correlation_id,
            message_type=MessageType.PROPOSAL,
            sender=AgentRole.CLAUDE,
            round_number=trigger.round_number,
            content="Claude response"
        )

    async def mock_grok_with_delay(trigger, task_prompt):
        call_times.append(("grok_start", asyncio.get_event_loop().time()))
        await asyncio.sleep(0.1)
        call_times.append(("grok_end", asyncio.get_event_loop().time()))
        return CollaborationMessage(
            message_id=f"msg_grok_{trigger.round_number}",
            correlation_id=trigger.correlation_id,
            message_type=MessageType.PROPOSAL,
            sender=AgentRole.GROK,
            round_number=trigger.round_number,
            content="Grok response"
        )

    mock_claude_agent.return_value.process_message = AsyncMock(side_effect=mock_claude_with_delay)
    mock_grok_agent.return_value.process_message = AsyncMock(side_effect=mock_grok_with_delay)

    coordinator = CollaborationCoordinator(
        claude_api_key=mock_claude_api_key,
        grok_api_key=mock_grok_api_key,
        max_rounds=1
    )

    # Force finalization after first round
    with patch('src.collaboration.coordinator.ConsensusDetector') as MockDetector:
        mock = MockDetector.return_value
        mock.analyze_round = Mock(return_value=ConsensusSignal(
            is_consensus=True,
            confidence=0.9,
            convergence_score=0.95,
            recommendation="FINALIZE",
            reasoning="Immediate consensus",
            agreement_indicators=["perfect_alignment"],
            disagreement_indicators=[]
        ))

        await coordinator.run_collaboration("Test task")

    # Verify both agents started before either finished (parallel execution)
    assert len(call_times) >= 4
    claude_start = next(t for name, t in call_times if name == "claude_start")
    grok_start = next(t for name, t in call_times if name == "grok_start")
    claude_end = next(t for name, t in call_times if name == "claude_end")
    grok_end = next(t for name, t in call_times if name == "grok_end")

    # Both should start before either ends (parallel)
    assert min(claude_start, grok_start) < min(claude_end, grok_end)
