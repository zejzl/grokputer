"""
Configuration tests.
"""

import pytest
from src import config


def test_config_loaded():
    """Test that configuration is loaded."""
    assert config.PROJECT_ROOT is not None
    assert config.XAI_BASE_URL is not None
    assert config.GROK_MODEL is not None


def test_directories_exist():
    """Test that required directories exist."""
    assert config.VAULT_DIR.exists()
    assert config.LOGS_DIR.exists()


def test_system_prompt():
    """Test system prompt is defined."""
    assert config.SYSTEM_PROMPT is not None
    assert len(config.SYSTEM_PROMPT) > 0
    assert "Grokputer" in config.SYSTEM_PROMPT


def test_tools_defined():
    """Test that tools are defined."""
    assert config.TOOLS is not None
    assert isinstance(config.TOOLS, list)
    assert len(config.TOOLS) > 0

    # Check for required tools
    tool_names = [tool["function"]["name"] for tool in config.TOOLS]
    assert "bash" in tool_names
    assert "computer" in tool_names
    assert "scan_vault" in tool_names
    assert "invoke_prayer" in tool_names
