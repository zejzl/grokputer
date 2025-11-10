"""
Unit tests for WebDevAgent

Tests the WebDev agent's ability to handle various web development tasks
in the Grokputer multi-agent architecture.

Author: Claude Code
Date: 2025-11-08
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, MagicMock

from src.agents.webdev_agent import WebDevAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.session_logger import SessionLogger


@pytest.fixture
def session_logger(tmp_path):
    """Create real SessionLogger with temp directory."""
    logger = SessionLogger(
        logs_dir=tmp_path,
        session_id="test_webdev_session"
    )
    return logger


@pytest_asyncio.fixture
async def message_bus():
    """Create MessageBus instance."""
    bus = MessageBus()
    yield bus
    await bus.shutdown()


@pytest_asyncio.fixture
async def webdev_agent(message_bus, session_logger):
    """Create WebDevAgent instance."""
    agent = WebDevAgent(
        agent_id="webdev",
        message_bus=message_bus,
        session_logger=session_logger,
        framework="fastapi",
        database="postgresql",
        auth_method="jwt"
    )
    yield agent
    # Cleanup handled by agent's on_stop if needed


class TestWebDevAgentInitialization:
    """Test WebDevAgent initialization and configuration."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, webdev_agent):
        """Test agent initializes correctly."""
        assert webdev_agent.agent_id == "webdev"
        assert webdev_agent.framework == "fastapi"
        assert webdev_agent.database == "postgresql"
        assert webdev_agent.auth_method == "jwt"

    @pytest.mark.asyncio
    async def test_custom_framework(self, message_bus, session_logger):
        """Test agent with custom framework."""
        agent = WebDevAgent(
            agent_id="webdev_django",
            message_bus=message_bus,
            session_logger=session_logger,
            framework="django",
            database="mysql",
            auth_method="oauth2"
        )

        assert agent.framework == "django"
        assert agent.database == "mysql"
        assert agent.auth_method == "oauth2"


class TestWebDevAgentAPICreation:
    """Test API endpoint creation functionality."""

    @pytest.mark.asyncio
    async def test_create_api_endpoints(self, webdev_agent):
        """Test creating API endpoints."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="create_api",
            content={
                "specification": {
                    "endpoints": [
                        {"path": "/users", "method": "GET"},
                        {"path": "/users", "method": "POST"},
                        {"path": "/users/{id}", "method": "PUT"}
                    ]
                }
            },
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result is not None
        assert result["status"] == "success"
        assert "API endpoint" in result["message"]  # More flexible assertion
        assert result["framework"] == "fastapi"
        assert len(result["endpoints"]) == 3

    @pytest.mark.asyncio
    async def test_create_api_with_grok_client(self, message_bus, session_logger):
        """Test API creation with GrokClient available."""
        mock_grok = MagicMock()
        agent = WebDevAgent(
            agent_id="webdev_grok",
            message_bus=message_bus,
            session_logger=session_logger,
            grok_client=mock_grok
        )

        message = Message(
            from_agent="coordinator",
            to_agent="webdev_grok",
            message_type="create_api",
            content={
                "specification": {
                    "endpoints": [{"path": "/api/data", "method": "GET"}]
                }
            },
            priority=MessagePriority.NORMAL
        )

        result = await agent.process_message(message)

        assert result["code_generated"] is True


class TestWebDevAgentAuthentication:
    """Test authentication setup functionality."""

    @pytest.mark.asyncio
    async def test_setup_jwt_auth(self, webdev_agent):
        """Test JWT authentication setup."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="setup_auth",
            content={"auth_type": "jwt"},
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["auth_type"] == "jwt"
        assert "Token generation/validation" in result["components"]

    @pytest.mark.asyncio
    async def test_setup_oauth2_auth(self, webdev_agent):
        """Test OAuth2 authentication setup."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="setup_auth",
            content={"auth_type": "oauth2"},
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["auth_type"] == "oauth2"


class TestWebDevAgentDatabase:
    """Test database design functionality."""

    @pytest.mark.asyncio
    async def test_design_database_schema(self, webdev_agent):
        """Test database schema design."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="design_database",
            content={
                "entities": [
                    {"name": "User", "fields": ["id", "email", "password"]},
                    {"name": "Post", "fields": ["id", "title", "content", "user_id"]}
                ],
                "relationships": [
                    {"from": "Post", "to": "User", "type": "many-to-one"}
                ]
            },
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["database"] == "postgresql"
        assert len(result["entities"]) == 2
        assert result["migrations"] is True


class TestWebDevAgentTesting:
    """Test test generation functionality."""

    @pytest.mark.asyncio
    async def test_write_unit_tests(self, webdev_agent):
        """Test unit test generation."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="write_tests",
            content={
                "test_type": "unit",
                "coverage": 90
            },
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["test_type"] == "unit"
        assert result["framework"] == "pytest"
        assert result["coverage_target"] == 90

    @pytest.mark.asyncio
    async def test_write_integration_tests(self, webdev_agent):
        """Test integration test generation."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="write_tests",
            content={"test_type": "integration"},
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["test_type"] == "integration"


class TestWebDevAgentDeployment:
    """Test deployment configuration generation."""

    @pytest.mark.asyncio
    async def test_generate_docker_deployment(self, webdev_agent):
        """Test Docker deployment config generation."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="deploy_app",
            content={"platform": "docker"},
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["platform"] == "docker"
        assert "Dockerfile" in result["files"]
        assert "docker-compose.yml" in result["files"]
        assert result["server"] == "uvicorn"  # FastAPI uses uvicorn


class TestWebDevAgentCodeReview:
    """Test code review functionality."""

    @pytest.mark.asyncio
    async def test_review_code_security(self, webdev_agent):
        """Test code review for security issues."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="review_code",
            content={
                "code": "eval(user_input)",
                "focus": "security"
            },
            priority=MessagePriority.HIGH
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["issues_found"] > 0
        assert any("eval" in s for s in result["suggestions"])

    @pytest.mark.asyncio
    async def test_review_code_clean(self, webdev_agent):
        """Test code review with clean code."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="review_code",
            content={
                "code": "def get_user(user_id: int) -> User: return db.query(User).filter_by(id=user_id).first()",
                "focus": "security"
            },
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["issues_found"] == 0


class TestWebDevAgentDebugging:
    """Test debugging functionality."""

    @pytest.mark.asyncio
    async def test_debug_performance_issue(self, webdev_agent):
        """Test debugging performance issues."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="debug_issue",
            content={
                "issue_type": "performance",
                "description": "API response time is slow"
            },
            priority=MessagePriority.HIGH
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["issue_type"] == "performance"
        assert len(result["possible_causes"]) > 0
        assert len(result["recommendations"]) > 0


class TestWebDevAgentStatus:
    """Test agent status reporting."""

    @pytest.mark.asyncio
    async def test_get_agent_status(self, webdev_agent):
        """Test getting agent status."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="get_status",
            content={},
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "success"
        assert result["agent_id"] == "webdev"
        assert result["framework"] == "fastapi"
        assert result["database"] == "postgresql"
        assert "project_context" in result


class TestWebDevAgentErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_unknown_message_type(self, webdev_agent):
        """Test handling of unknown message types."""
        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="unknown_operation",
            content={},
            priority=MessagePriority.NORMAL
        )

        result = await webdev_agent.process_message(message)

        assert result["status"] == "error"
        assert "Unknown message type" in result["message"]


# Integration test
class TestWebDevAgentIntegration:
    """Test full workflow integration."""

    @pytest.mark.asyncio
    async def test_full_api_development_workflow(self, webdev_agent):
        """Test complete API development workflow."""
        # Step 1: Design database
        db_message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="design_database",
            content={
                "entities": [{"name": "User", "fields": ["id", "email"]}],
                "relationships": []
            },
            priority=MessagePriority.NORMAL
        )
        db_result = await webdev_agent.process_message(db_message)
        assert db_result["status"] == "success"

        # Step 2: Setup authentication
        auth_message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="setup_auth",
            content={"auth_type": "jwt"},
            priority=MessagePriority.NORMAL
        )
        auth_result = await webdev_agent.process_message(auth_message)
        assert auth_result["status"] == "success"

        # Step 3: Create API endpoints
        api_message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="create_api",
            content={
                "specification": {
                    "endpoints": [{"path": "/users", "method": "GET"}]
                }
            },
            priority=MessagePriority.NORMAL
        )
        api_result = await webdev_agent.process_message(api_message)
        assert api_result["status"] == "success"

        # Step 4: Write tests
        test_message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="write_tests",
            content={"test_type": "unit"},
            priority=MessagePriority.NORMAL
        )
        test_result = await webdev_agent.process_message(test_message)
        assert test_result["status"] == "success"

        # Step 5: Generate deployment
        deploy_message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type="deploy_app",
            content={"platform": "docker"},
            priority=MessagePriority.NORMAL
        )
        deploy_result = await webdev_agent.process_message(deploy_message)
        assert deploy_result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
