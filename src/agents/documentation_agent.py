"""
Documentation Agent - Specialized agent for generating and maintaining documentation.

This agent handles documentation tasks like README generation, API docs, code comments,
and ensures documentation quality and completeness.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.model_client import ModelClientFactory

logger = logging.getLogger(__name__)


class DocumentationAgent(BaseAgent):
    """
    Agent specialized in documentation tasks.

    Capabilities:
    - Generate README files
    - Create API documentation
    - Add code comments and docstrings
    - Maintain documentation quality
    - Generate user guides and tutorials
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger,
        config: Dict[str, Any],
    ):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.documentation_types = {
            'readme': self._generate_readme,
            'api_docs': self._generate_api_docs,
            'code_comments': self._add_code_comments,
            'user_guide': self._generate_user_guide,
        }

        # Initialize AI client for enhanced generation
        self.ai_client = None
        self._init_ai_client()

    def _init_ai_client(self):
        """Initialize the AI client for documentation generation."""
        try:
            api_key = self.config.get("GROK_API_KEY") or os.getenv("GROK_API_KEY")
            model = self.config.get("GROK_MODEL", "grok-4-fast-reasoning")
            if api_key:
                self.ai_client = ModelClientFactory.create_client("grok", api_key, model)
            else:
                logger.warning("No GROK_API_KEY found for DocumentationAgent")
                self.ai_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize AI client for DocumentationAgent: {e}")
            self.ai_client = None

    async def process_message(self, message: Message) -> List[Message]:
        """Process documentation-related messages."""
        responses = []

        if message.message_type == 'documentation_request':
            doc_type = message.content.get('type', 'readme')
            target = message.content.get('target', '.')

            if doc_type in self.documentation_types:
                result = await self.documentation_types[doc_type](target)
                response_msg = Message(
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    message_type='documentation_complete',
                    content={'result': result, 'type': doc_type},
                    priority=MessagePriority.NORMAL
                )
                responses.append(response_msg)
            else:
                error_msg = Message(
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    message_type='documentation_error',
                    content={'error': f'Unknown documentation type: {doc_type}'},
                    priority=MessagePriority.NORMAL
                )
                responses.append(error_msg)

        return responses

    async def _generate_readme(self, target: str) -> Dict[str, Any]:
        """Generate a README file for the target project."""
        # Analyze project structure
        project_path = Path(target)
        if not project_path.exists():
            return {'error': f'Project path {target} does not exist'}

        # Gather project information
        files = list(project_path.rglob('*.py'))
        has_requirements = (project_path / 'requirements.txt').exists()
        has_setup = (project_path / 'setup.py').exists()

        # Generate README content
        readme_content = f"""# {project_path.name}

## Overview

This project contains {len(files)} Python files.

## Installation

{'pip install -r requirements.txt' if has_requirements else 'pip install .' if has_setup else 'Installation instructions TBD'}

## Usage

Usage instructions TBD

## Features

- Feature 1
- Feature 2

## Contributing

Contributions welcome!

## License

TBD
"""

        # Write README
        readme_path = project_path / 'README.md'
        readme_path.write_text(readme_content)

        return {
            'status': 'success',
            'file': str(readme_path),
            'content': readme_content
        }

    async def _generate_api_docs(self, target: str) -> Dict[str, Any]:
        """Generate API documentation."""
        # Stub implementation
        return {'status': 'success', 'message': 'API docs generation not implemented yet'}

    async def _add_code_comments(self, target: str) -> Dict[str, Any]:
        """Add comments to code files."""
        # Stub implementation
        return {'status': 'success', 'message': 'Code commenting not implemented yet'}

    async def _generate_user_guide(self, target: str) -> Dict[str, Any]:
        """Generate user guide."""
        # Stub implementation
        return {'status': 'success', 'message': 'User guide generation not implemented yet'}