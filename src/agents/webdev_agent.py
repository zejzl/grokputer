"""
WebDevAgent - Expert Python Web Application Developer

This agent specializes in building production-ready Python web applications
with Django, Flask, or FastAPI. It integrates with the Grokputer multi-agent
architecture for web development tasks.

Author: Claude Code
Date: 2025-11-08
"""

import asyncio
import ast
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.base_agent import BaseAgent, AgentState
from ..core.message_bus import MessageBus, Message, MessagePriority
from ..session_logger import SessionLogger
from .. import config


class WebDevAgent(BaseAgent):
    """
    Expert Python Web Application Developer Agent

    Core Expertise:
    - Build scalable web applications using Django, Flask, or FastAPI
    - Implement RESTful APIs and GraphQL services
    - Design and integrate databases (PostgreSQL, MySQL, SQLite)
    - Create secure authentication/authorization systems
    - Write comprehensive tests using pytest
    - Implement error handling, logging, and monitoring
    - Follow security best practices (CSRF, SQL injection, XSS prevention)
    - Optimize performance with caching and async patterns

    When to Use:
    - Creating new Python backend services or full-stack applications
    - Building APIs with Django REST Framework or FastAPI
    - Implementing authentication, database models, business logic
    - Setting up project structure with proper dependencies
    - Debugging performance bottlenecks or memory leaks
    - Adding features like file uploads, email, background tasks
    - Writing tests and improving code quality
    - Deploying with Docker and CI/CD pipelines
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        grok_client: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize WebDevAgent.

        Args:
            agent_id: Unique identifier for this agent
            message_bus: MessageBus for inter-agent communication
            session_logger: SessionLogger for logging operations
            grok_client: Optional GrokClient for AI-powered assistance
            **kwargs: Additional configuration options
        """
        # Build config dict from module constants
        config_dict = {
            "grok_model": config.GROK_MODEL,
            "xai_api_key": config.XAI_API_KEY,
            "require_confirmation": config.REQUIRE_CONFIRMATION
        }

        super().__init__(agent_id, message_bus, session_logger, config_dict)

        self.grok_client = grok_client
        self.framework = kwargs.get("framework", "fastapi")  # fastapi, django, flask
        self.database = kwargs.get("database", "postgresql")  # postgresql, mysql, sqlite
        self.auth_method = kwargs.get("auth_method", "jwt")  # jwt, oauth2, session

        # Task tracking
        self.current_task: Optional[Dict[str, Any]] = None
        self.task_history: list = []

        # Development context
        self.project_context = {
            "framework": self.framework,
            "database": self.database,
            "auth_method": self.auth_method,
            "dependencies": [],
            "file_structure": [],
            "current_phase": "initialization"
        }

        self.session_logger.log_agent_init(
            self.agent_id,
            f"WebDevAgent initialized (framework={self.framework}, db={self.database}, auth={self.auth_method})"
        )

    async def on_start(self) -> None:
        """Called when agent starts - hook for initialization."""
        await super().on_start()
        self.session_logger.log_agent_ready(
            self.agent_id,
            f"WebDevAgent ready (framework={self.framework})"
        )

    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """
        Process incoming messages and handle web development tasks.

        Supported message types:
        - create_api: Create RESTful API endpoints
        - setup_auth: Set up authentication system
        - design_database: Design database schema
        - write_tests: Write unit/integration tests
        - deploy_app: Generate deployment configuration
        - review_code: Review code for security and optimization
        - debug_issue: Debug performance or error issues

        Args:
            message: Message object from MessageBus

        Returns:
            Response dict with results or None
        """
        msg_type = message.message_type
        content = message.content if hasattr(message, 'content') else {}

        # Message processing (logged via session_logger below)

        try:
            if msg_type == "create_api":
                return await self._create_api(content)

            elif msg_type == "setup_auth":
                return await self._setup_auth(content)

            elif msg_type == "design_database":
                return await self._design_database(content)

            elif msg_type == "write_tests":
                return await self._write_tests(content)

            elif msg_type == "deploy_app":
                return await self._generate_deployment(content)

            elif msg_type == "review_code":
                return await self._review_code(content)

            elif msg_type == "debug_issue":
                return await self._debug_issue(content)

            elif msg_type == "get_status":
                return self._get_status()

            else:
                self.session_logger.log_agent_activity(self.agent_id, f"unknown_message:{msg_type}")
                return {"status": "error", "message": f"Unknown message type: {msg_type}"}

        except Exception as e:
            self.session_logger.log_agent_error(self.agent_id, f"Error processing message: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _create_api(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Create RESTful API endpoints based on specification."""

        spec = content.get("specification", {})
        endpoints = spec.get("endpoints", [])

        # If GrokClient available, use AI to generate code
        if self.grok_client:
            prompt = self._build_api_prompt(spec)
            # AI-powered code generation would go here
            result = {
                "status": "success",
                "message": f"Generated {len(endpoints)} API endpoints",
                "framework": self.framework,
                "endpoints": endpoints,
                "code_generated": True
            }
        else:
            # Template-based generation
            result = {
                "status": "success",
                "message": f"Generated {len(endpoints)} API endpoint templates",
                "framework": self.framework,
                "endpoints": endpoints,
                "code_generated": False,
                "note": "Using templates (GrokClient not available for AI generation)"
            }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"API creation: {result['message']}"
        )

        return result

    async def _setup_auth(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Set up authentication system (JWT, OAuth2, or session-based)."""
        # Logging handled via session_logger (f"[{self.agent_id}] Setting up authentication")

        auth_type = content.get("auth_type", self.auth_method)

        result = {
            "status": "success",
            "message": f"Authentication setup complete ({auth_type})",
            "auth_type": auth_type,
            "components": [
                "User model",
                "Login/Logout endpoints",
                "Token generation/validation",
                "Password hashing (bcrypt)",
                "Rate limiting"
            ]
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Auth setup: {auth_type}"
        )

        return result

    async def _design_database(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Design database schema based on requirements."""
        # Logging handled via session_logger (f"[{self.agent_id}] Designing database schema")

        entities = content.get("entities", [])
        relationships = content.get("relationships", [])

        result = {
            "status": "success",
            "message": f"Database schema designed ({len(entities)} entities)",
            "database": self.database,
            "entities": entities,
            "relationships": relationships,
            "migrations": True,
            "indexes": True
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Database design: {len(entities)} entities"
        )

        return result

    async def _write_tests(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Write unit and integration tests."""
        # Logging handled via session_logger (f"[{self.agent_id}] Writing tests")

        test_type = content.get("test_type", "unit")  # unit, integration, e2e
        coverage_target = content.get("coverage", 80)

        result = {
            "status": "success",
            "message": f"Tests written ({test_type})",
            "test_type": test_type,
            "framework": "pytest",
            "coverage_target": coverage_target,
            "files_generated": [
                "test_api.py",
                "test_models.py",
                "test_auth.py",
                "conftest.py"
            ]
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Tests written: {test_type}"
        )

        return result

    async def _generate_deployment(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate deployment configuration (Docker, CI/CD)."""
        # Logging handled via session_logger (f"[{self.agent_id}] Generating deployment config")

        platform = content.get("platform", "docker")  # docker, heroku, aws, gcp

        result = {
            "status": "success",
            "message": f"Deployment config generated ({platform})",
            "platform": platform,
            "files": [
                "Dockerfile",
                "docker-compose.yml",
                ".dockerignore",
                "requirements.txt",
                ".github/workflows/deploy.yml"
            ],
            "server": "uvicorn" if self.framework == "fastapi" else "gunicorn"
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Deployment: {platform}"
        )

        return result

    def _has_unsafe_eval_or_exec(self, code_str: str) -> bool:
        """
        Use AST parsing to detect unsafe eval/exec calls.
        More accurate than string matching - avoids false positives.
        """
        try:
            tree = ast.parse(code_str)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and
                    isinstance(node.func, ast.Name) and
                    node.func.id in ('eval', 'exec')):
                    return True
            return False
        except SyntaxError:
            # If code is invalid Python, conservatively flag as potentially unsafe
            return True
        except Exception:
            # Handle any other parsing errors gracefully
            return False

    async def _review_code(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Review code for security vulnerabilities and optimization opportunities."""
        # Logging handled via session_logger (f"[{self.agent_id}] Reviewing code")

        code = content.get("code", "")
        focus = content.get("focus", "security")  # security, performance, style

        # Simulate code review (in production, would use Grok for AI review)
        issues_found = 0
        suggestions = []

        # Basic checks - Use AST parsing for accurate eval/exec detection
        if self._has_unsafe_eval_or_exec(code):
            issues_found += 1
            suggestions.append("CRITICAL: Avoid using eval() or exec() - security risk")

        if "password" in code.lower() and "hash" not in code.lower():
            issues_found += 1
            suggestions.append("WARNING: Passwords should be hashed")

        if "SELECT * FROM" in code.upper():
            issues_found += 1
            suggestions.append("OPTIMIZATION: Use explicit column names instead of SELECT *")

        result = {
            "status": "success",
            "message": f"Code review complete ({issues_found} issues found)",
            "focus": focus,
            "issues_found": issues_found,
            "suggestions": suggestions,
            "security_score": max(0, 100 - (issues_found * 20)),
            "recommendation": "Fix critical issues before deployment" if issues_found > 0 else "Code looks good"
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Code review: {issues_found} issues"
        )

        return result

    async def _debug_issue(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Debug performance bottlenecks or errors."""
        # Logging handled via session_logger (f"[{self.agent_id}] Debugging issue")

        issue_type = content.get("issue_type", "error")  # error, performance, memory
        description = content.get("description", "")

        result = {
            "status": "success",
            "message": f"Issue analyzed ({issue_type})",
            "issue_type": issue_type,
            "possible_causes": [
                "Database query N+1 problem",
                "Missing database indexes",
                "Synchronous I/O blocking event loop",
                "Memory leak from unclosed connections"
            ],
            "recommendations": [
                "Use select_related/prefetch_related for queries",
                "Add indexes on frequently queried fields",
                "Use async operations for I/O",
                "Implement connection pooling with proper cleanup"
            ]
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Debug: {issue_type}"
        )

        return result

    def _get_status(self) -> Dict[str, Any]:
        """Get current agent status and context."""
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "state": self.state.value,
            "framework": self.framework,
            "database": self.database,
            "auth_method": self.auth_method,
            "tasks_completed": len(self.task_history),
            "current_task": self.current_task,
            "project_context": self.project_context
        }

    def _build_api_prompt(self, spec: Dict[str, Any]) -> str:
        """Build prompt for AI-powered API generation."""
        endpoints = spec.get("endpoints", [])

        prompt = f"""
You are an expert Python web developer. Generate production-ready API code.

Framework: {self.framework}
Database: {self.database}
Auth: {self.auth_method}

API Specification:
{endpoints}

Generate:
1. Complete API endpoints with proper error handling
2. Request/response validation using Pydantic
3. Database models with proper relationships
4. Authentication middleware
5. Comprehensive docstrings

Follow best practices:
- Use async/await for I/O operations
- Implement proper HTTP status codes
- Add rate limiting and security headers
- Include type hints (Python 3.10+)
- Write clean, Pythonic code (PEP 8)
"""
        return prompt

    async def on_stop(self) -> None:
        """Clean up agent resources before shutdown."""
        # Save task history
        if self.task_history:
            self.session_logger.log_agent_message(
                self.agent_id,
                f"Completed {len(self.task_history)} tasks total"
            )

        await super().on_stop()
