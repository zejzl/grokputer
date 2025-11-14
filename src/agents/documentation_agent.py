"""
Documentation Agent - Specialized agent for generating and maintaining documentation.

This agent handles documentation tasks like README generation, API docs, code comments,
and ensures documentation quality and completeness.
"""

import asyncio
import logging
import ast
import inspect
from typing import Dict, Any, Optional, List
from pathlib import Path
import importlib.util

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
            'auto_docs': self._generate_auto_docs,
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

    async def _generate_auto_docs(self, target: str) -> Dict[str, Any]:
        """Generate comprehensive documentation from code analysis."""
        try:
            target_path = Path(target)

            if target_path.is_file() and target_path.suffix == '.py':
                # Single file analysis
                docs = self._analyze_python_file(target_path)
                output_file = target_path.with_suffix('.md')
            elif target_path.is_dir():
                # Directory analysis
                docs = self._analyze_python_directory(target_path)
                output_file = target_path / 'API_DOCUMENTATION.md'
            else:
                return {'error': f'Invalid target: {target}'}

            # Write documentation
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(docs)

            return {
                'status': 'success',
                'file': str(output_file),
                'message': f'Auto-generated documentation saved to {output_file}'
            }

        except Exception as e:
            logger.error(f"Auto-docs generation failed: {e}")
            return {'error': str(e)}

    def _analyze_python_file(self, file_path: Path) -> str:
        """Analyze a single Python file and generate documentation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code, filename=str(file_path))

            classes = []
            functions = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(self._extract_class_info(node, source_code))
                elif isinstance(node, ast.FunctionDef):
                    functions.append(self._extract_function_info(node, source_code))
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    imports.append(self._extract_import_info(node))

            # Generate markdown
            docs = f"# {file_path.name}\n\n"
            docs += f"**File:** `{file_path}`\n\n"

            if imports:
                docs += "## Imports\n\n"
                for imp in imports:
                    docs += f"- `{imp}`\n"
                docs += "\n"

            if classes:
                docs += "## Classes\n\n"
                for cls in classes:
                    docs += f"### {cls['name']}\n\n"
                    if cls['docstring']:
                        docs += f"{cls['docstring']}\n\n"
                    if cls['methods']:
                        docs += "**Methods:**\n"
                        for method in cls['methods']:
                            docs += f"- `{method['signature']}`\n"
                            if method['docstring']:
                                docs += f"  - {method['docstring'].split('.')[0]}\n"
                        docs += "\n"

            if functions:
                docs += "## Functions\n\n"
                for func in functions:
                    docs += f"### {func['name']}\n\n"
                    docs += f"```python\n{func['signature']}\n```\n\n"
                    if func['docstring']:
                        docs += f"{func['docstring']}\n\n"

            return docs

        except Exception as e:
            return f"# {file_path.name}\n\nError analyzing file: {e}\n"

    def _analyze_python_directory(self, dir_path: Path) -> str:
        """Analyze a directory of Python files."""
        docs = f"# API Documentation - {dir_path.name}\n\n"
        docs += f"**Directory:** `{dir_path}`\n\n"

        py_files = list(dir_path.rglob('*.py'))
        py_files = [f for f in py_files if not any(part.startswith('.') or part == '__pycache__' for part in f.parts)]

        if not py_files:
            return docs + "No Python files found.\n"

        docs += f"**Files analyzed:** {len(py_files)}\n\n"

        # Overview
        docs += "## Overview\n\n"
        for file_path in sorted(py_files):
            relative_path = file_path.relative_to(dir_path)
            docs += f"- [{relative_path}](#{str(relative_path).replace('/', '-').replace('.', '-')})\n"
        docs += "\n"

        # Detailed analysis
        for file_path in sorted(py_files):
            relative_path = file_path.relative_to(dir_path)
            docs += f"## {relative_path}\n\n"
            file_docs = self._analyze_python_file(file_path)
            # Remove the header since we have our own
            file_docs = '\n'.join(file_docs.split('\n')[2:])
            docs += file_docs + "\n"

        return docs

    def _extract_class_info(self, node: ast.ClassDef, source_code: str) -> Dict[str, Any]:
        """Extract information about a class."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._extract_function_info(item, source_code))

        docstring = self._get_docstring(node.body)

        return {
            'name': node.name,
            'docstring': docstring,
            'methods': methods,
            'line': node.lineno
        }

    def _extract_function_info(self, node: ast.FunctionDef, source_code: str) -> Dict[str, Any]:
        """Extract information about a function."""
        # Get signature
        args = []
        if node.args.args:
            for arg in node.args.args:
                args.append(arg.arg)
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        signature = f"def {node.name}({', '.join(args)})"

        docstring = self._get_docstring(node.body)

        return {
            'name': node.name,
            'signature': signature,
            'docstring': docstring,
            'line': node.lineno
        }

    def _extract_import_info(self, node: ast.AST) -> str:
        """Extract import information."""
        if isinstance(node, ast.Import):
            return ', '.join(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = ', '.join(alias.name for alias in node.names)
            return f"from {module} import {names}"
        return ""

    def _get_docstring(self, body: List[ast.stmt]) -> str:
        """Extract docstring from AST body."""
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Str):
            return body[0].value.s
        elif body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            return body[0].value.value
        return ""