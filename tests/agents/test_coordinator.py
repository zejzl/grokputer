import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.coordinator import Coordinator, TaskStatus
from src.core.message_bus import MessageBus, MessagePriority
from src.session_logger import SessionLogger
from src.config import config

@pytest.fixture
def mock_message_bus():
    bus = AsyncMock(spec=MessageBus)
    bus.send = AsyncMock()
    bus.receive = AsyncMock(return_value={'type': 'response', 'content': {'success': True}})
    return bus

@pytest.fixture
def mock_session_logger():
    logger = MagicMock(spec=SessionLogger)
    logger.log_coordinator_decomposition = MagicMock()
    logger.log_coordinator_delegation = MagicMock()
    logger.log_confirmation = MagicMock()
    logger.log_task_completion = MagicMock()
    logger.log_task_failure = MagicMock()
    logger.get_swarm_metrics = MagicMock(return_value=MagicMock(handoffs=0, success_rate=1.0))
    return logger

@pytest.fixture
def coordinator(mock_message_bus, mock_session_logger):
    return Coordinator(mock_message_bus, mock_session_logger, config)

class TestCoordinator:
    async def test_process_message_new_task(self, coordinator, mock_message_bus, mock_session_logger):
        """Test handling new task: decompose and delegate."""
        message = {
            'type': 'new_task',
            'task_id': 'test1',
            'from': 'user',
            'content': {'description': 'observe screen and click button'}
        }

        response = await coordinator.process_message(message)

        # Assertions
        assert response['type'] == 'task_delegated'
        assert response['content']['task_id'] == 'test1'
        assert response['content']['subtasks'] == 2  # Default observe + act

        # Check mocks
        mock_session_logger.log_coordinator_decomposition.assert_called_once()
        mock_message_bus.send.call_count >= 2  # At least two delegations

    async def test_decompose_task_heuristics(self, coordinator):
        """Test task decomposition rules."""
        # Observe task
        subtasks = coordinator._decompose_task('observe screen')
        assert len(subtasks) == 1
        assert subtasks[0]['agent'] == 'observer'
        assert subtasks[0]['action'] == 'capture_screen'

        # Action task
        subtasks = coordinator._decompose_task('click button')
        assert len(subtasks) == 1
        assert subtasks[0]['agent'] == 'actor'
        assert subtasks[0]['action'] == 'perform_action'

        # Default (split)
        subtasks = coordinator._decompose_task('analyze file')
        assert len(subtasks) == 2
        assert subtasks[0]['agent'] == 'observer'
        assert subtasks[1]['agent'] == 'actor'

    async def test_handle_response_aggregation(self, coordinator, mock_message_bus, mock_session_logger):
        """Test response aggregation and completion."""
        # Setup active task
        task_id = 'test2'
        coordinator.active_tasks[task_id] = {
            'status': TaskStatus.DELEGATED,
            'description': 'test task',
            'subtasks': [{'agent': 'observer'}],
            'results': {}
        }
        coordinator.pending_responses[task_id] = ['observer']

        message = {
            'type': 'response',
            'task_id': task_id,
            'from': 'observer',
            'content': {'success': True}
        }

        response = await coordinator.process_message(message)

        # Assertions
        assert response['type'] == 'task_complete'
        assert coordinator.active_tasks.get(task_id) is None  # Task removed
        assert len(coordinator.pending_responses.get(task_id, [])) == 0
        mock_session_logger.log_task_completion.assert_called_once()

    async def test_handle_error_recovery(self, coordinator, mock_message_bus, mock_session_logger):
        """Test error handling and failure logging."""
        task_id = 'test3'
        coordinator.active_tasks[task_id] = {
            'status': TaskStatus.DELEGATED,
            'description': 'test task',
            'subtasks': [],
            'results': {}
        }

        message = {
            'type': 'error',
            'task_id': task_id,
            'from': 'actor',
            'content': {'error': 'Action failed'}
        }

        response = await coordinator.process_message(message)

        # Assertions
        assert response['type'] == 'task_failed'
        assert coordinator.active_tasks[task_id]['status'] == TaskStatus.FAILED
        mock_session_logger.log_task_failure.assert_called_once_with(task_id, 'Action failed')

    async def test_request_confirmation(self, coordinator):
        """Test confirmation prompt (mock input)."""
        task_id = 'test4'
        action = 'bash'
        params = {'command': 'rm file.txt'}

        # Mock input to 'y'
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_input:
            mock_input.return_value = 'y'
            confirmed = await coordinator._request_confirmation(task_id, action, params)

        assert confirmed is True
        coordinator.session_logger.log_confirmation.assert_called_once()

    def test_requires_confirmation(self, coordinator):
        """Test safety check for confirmations."""
        # Risky action
        assert coordinator._requires_confirmation('bash', {'command': 'rm -rf'})
        # Safe action
        assert not coordinator._requires_confirmation('observe', {})

    async def test_stop_graceful_shutdown(self, coordinator, mock_session_logger):
        """Test graceful shutdown with pending tasks."""
        # Add interrupted task
        task_id = 'test5'
        coordinator.active_tasks[task_id] = {
            'status': TaskStatus.DELEGATED,
            'description': 'interrupted task'
        }

        await coordinator.stop()

        mock_session_logger.log_task_interrupted.assert_called_once_with(task_id)
        coordinator.session_logger.log_agent_stop.assert_called_once_with('coordinator')