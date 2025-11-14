"""
Tests for CrewAI-inspired orchestration system.

Tests Crew formation, Flow execution, and delegation patterns.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.agents.crew_orchestrator import (
    CrewOrchestrator, CrewMember, CrewRole, FlowStep, FlowState
)
from src.agents.crew_templates import CrewTemplates, FlowTemplates, CrewManager
from src.core.message_bus import MessageBus, Message, MessagePriority


class TestCrewOrchestrator:
    """Test the core Crew orchestrator functionality."""

    @pytest.fixture
    def message_bus(self):
        return Mock(spec=MessageBus)

    @pytest.fixture
    def orchestrator(self, message_bus):
        return CrewOrchestrator(message_bus)

    @pytest.fixture
    def mock_agent(self):
        agent = Mock()
        agent.agent_id = "test_agent"
        return agent

    def test_create_crew(self, orchestrator, mock_agent):
        """Test crew creation with members."""
        member = CrewMember(
            agent=mock_agent,
            role=CrewRole.EXECUTOR,
            capabilities={"command_execution"}
        )

        orchestrator.create_crew("test_crew", [member])

        assert "test_crew" in orchestrator.crews
        assert len(orchestrator.crews["test_crew"]) == 1
        assert orchestrator.crews["test_crew"]["test_agent"] == member

    def test_define_flow(self, orchestrator):
        """Test flow definition."""
        steps = [
            FlowStep(
                step_id="step1",
                description="First step",
                required_role=CrewRole.EXECUTOR,
                task_type="command_execution"
            ),
            FlowStep(
                step_id="step2",
                description="Second step",
                required_role=CrewRole.ANALYZER,
                task_type="data_analysis",
                dependencies=["step1"]
            )
        ]

        orchestrator.define_flow("test_flow", steps)

        assert "test_flow" in orchestrator.active_flows
        flow = orchestrator.active_flows["test_flow"]
        assert len(flow.steps) == 2
        assert "step1" in flow.steps
        assert "step2" in flow.steps
        assert flow.steps["step2"].dependencies == ["step1"]

    @pytest.mark.asyncio
    async def test_execute_flow_simple(self, orchestrator, mock_agent, message_bus):
        """Test simple flow execution."""
        # Setup crew
        member = CrewMember(
            agent=mock_agent,
            role=CrewRole.EXECUTOR,
            capabilities={"command_execution"}
        )
        orchestrator.create_crew("test_crew", [member])

        # Register agent with message bus
        message_bus.register_agent("test_agent")

        # Setup flow
        steps = [
            FlowStep(
                step_id="execute",
                description="Execute command",
                required_role=CrewRole.EXECUTOR,
                task_type="command_execution"
            )
        ]
        orchestrator.define_flow("test_flow", steps)

        # Mock the _execute_step method to return the expected result
        async def mock_execute_step(crew, flow, step):
            return "executed"

        orchestrator._execute_step = mock_execute_step

        # Execute flow
        result = await orchestrator.execute_flow("test_crew", "test_flow")

        assert result["execute"] == "executed"
        assert orchestrator.active_flows["test_flow"].state == FlowState.COMPLETED

    @pytest.mark.asyncio
    async def test_delegate_task(self, orchestrator, mock_agent, message_bus):
        """Test task delegation."""
        # Setup crew
        member = CrewMember(
            agent=mock_agent,
            role=CrewRole.EXECUTOR,
            capabilities={"command_execution"}
        )
        orchestrator.create_crew("test_crew", [member])

        # Register agent with message bus
        message_bus.register_agent("test_agent")

        # Mock message bus response
        from src.core.message_bus import Message
        mock_response = Message(
            from_agent="test_agent",
            to_agent="crew_orchestrator",
            message_type="crew_response",
            content={"status": "success", "result": "delegated_result"}
        )
        message_bus.send_request = AsyncMock(return_value=mock_response)

        # Delegate task
        result = await orchestrator.delegate_task(
            "test_crew",
            "command_execution",
            {"command": "test"}
        )

        assert result == "delegated_result"
        message_bus.send_request.assert_called_once()

    def test_get_crew_status(self, orchestrator, mock_agent):
        """Test crew status retrieval."""
        member = CrewMember(
            agent=mock_agent,
            role=CrewRole.EXECUTOR,
            capabilities={"command_execution"},
            active_tasks=1
        )
        orchestrator.create_crew("test_crew", [member])

        status = orchestrator.get_crew_status("test_crew")

        assert status["crew_id"] == "test_crew"
        assert status["member_count"] == 1
        assert len(status["members"]) == 1
        assert status["members"][0]["active_tasks"] == 1

    def test_get_flow_status(self, orchestrator):
        """Test flow status retrieval."""
        steps = [
            FlowStep(
                step_id="step1",
                description="Test step",
                required_role=CrewRole.EXECUTOR,
                task_type="command_execution"
            )
        ]
        orchestrator.define_flow("test_flow", steps)

        status = orchestrator.get_flow_status("test_flow")

        assert status["flow_id"] == "test_flow"
        assert status["state"] == "pending"
        assert status["total_steps"] == 1


class TestCrewTemplates:
    """Test predefined Crew and Flow templates."""

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing."""
        agents = {}
        roles = ["observer", "coordinator", "validator", "executor", "analyzer", "learner"]

        for role in roles:
            agent = Mock()
            agent.agent_id = f"{role}_agent"
            agents[role] = agent

        return agents

    def test_create_task_execution_crew(self, mock_agents):
        """Test task execution crew creation."""
        templates = CrewTemplates()

        crew_members = templates.create_task_execution_crew(
            observer=mock_agents["observer"],
            coordinator=mock_agents["coordinator"],
            validator=mock_agents["validator"],
            executor=mock_agents["executor"],
            analyzer=mock_agents["analyzer"],
            learner=mock_agents["learner"]
        )

        assert len(crew_members) == 6

        # Check roles
        roles = [member.role for member in crew_members]
        assert CrewRole.COORDINATOR in roles
        assert CrewRole.OBSERVER in roles
        assert CrewRole.VALIDATOR in roles
        assert CrewRole.EXECUTOR in roles
        assert CrewRole.ANALYZER in roles
        assert CrewRole.LEARNER in roles

    def test_create_research_crew(self, mock_agents):
        """Test research crew creation."""
        templates = CrewTemplates()

        crew_members = templates.create_research_crew(
            coordinator=mock_agents["coordinator"],
            analyzer=mock_agents["analyzer"],
            learner=mock_agents["learner"]
        )

        assert len(crew_members) == 3
        roles = [member.role for member in crew_members]
        assert CrewRole.COORDINATOR in roles
        assert CrewRole.ANALYZER in roles
        assert CrewRole.LEARNER in roles

    def test_create_task_execution_flow(self):
        """Test task execution flow creation."""
        templates = FlowTemplates()

        steps = templates.create_task_execution_flow()

        assert len(steps) == 8  # Full workflow

        # Check step dependencies
        step_dict = {step.step_id: step for step in steps}
        assert "observe_initial_state" in step_dict
        assert "decompose_task" in step_dict
        assert "validate_plan" in step_dict
        assert step_dict["validate_plan"].dependencies == ["decompose_task"]

    def test_create_research_flow(self):
        """Test research flow creation."""
        templates = FlowTemplates()

        steps = templates.create_research_flow()

        assert len(steps) == 5
        step_dict = {step.step_id: step for step in steps}

        # Check parallel execution (no dependencies between gather and analyze initially)
        assert len(step_dict["gather_information"].dependencies) == 1  # depends on scope
        assert len(step_dict["analyze_patterns"].dependencies) == 1   # depends on gather


class TestCrewManager:
    """Test the high-level Crew manager."""

    @pytest.fixture
    def message_bus(self):
        return Mock(spec=MessageBus)

    @pytest.fixture
    def orchestrator(self, message_bus):
        return CrewOrchestrator(message_bus)

    @pytest.fixture
    def crew_manager(self, orchestrator):
        return CrewManager(orchestrator)

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing."""
        agents = {}
        roles = ["observer", "coordinator", "validator", "executor", "analyzer", "learner"]

        for role in roles:
            agent = Mock()
            agent.agent_id = f"{role}_agent"
            agents[role] = agent

        return agents

    def test_setup_standard_task_crew(self, crew_manager, mock_agents):
        """Test setting up a standard task execution crew."""
        flow_id = crew_manager.setup_standard_task_crew(
            crew_id="task_crew",
            observer=mock_agents["observer"],
            coordinator=mock_agents["coordinator"],
            validator=mock_agents["validator"],
            executor=mock_agents["executor"],
            analyzer=mock_agents["analyzer"],
            learner=mock_agents["learner"]
        )

        assert "task_crew" in crew_manager.orchestrator.crews
        assert flow_id == "task_crew_task_execution"
        assert flow_id in crew_manager.orchestrator.active_flows

    def test_setup_research_crew(self, crew_manager, mock_agents):
        """Test setting up a research crew."""
        flow_id = crew_manager.setup_research_crew(
            crew_id="research_crew",
            coordinator=mock_agents["coordinator"],
            analyzer=mock_agents["analyzer"],
            learner=mock_agents["learner"]
        )

        assert "research_crew" in crew_manager.orchestrator.crews
        assert flow_id == "research_crew_research"
        assert flow_id in crew_manager.orchestrator.active_flows

    def test_task_classification(self, crew_manager):
        """Test automatic task type classification."""
        assert crew_manager._classify_task("execute this command") == "task_execution"
        assert crew_manager._classify_task("analyze this data") == "research"
        assert crew_manager._classify_task("write some code") == "code_review"
        assert crew_manager._classify_task("unknown task") == "task_execution"  # default


class TestCrewIntegration:
    """Integration tests for CrewAI patterns."""

    @pytest.mark.asyncio
    async def test_full_crew_workflow(self):
        """Test a complete crew workflow from setup to execution."""
        # This would be a full integration test with real agents
        # For now, just test the orchestration logic
        pass

    def test_crew_scalability(self):
        """Test crew performance with multiple members."""
        # Test with larger crews
        pass

    def test_flow_error_handling(self):
        """Test error handling in flow execution."""
        # Test retry logic, failure handling
        pass