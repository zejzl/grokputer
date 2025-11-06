"""
Unit tests for custom tools.
"""

import pytest
from src.tools import invoke_prayer, scan_vault, get_vault_stats


def test_invoke_prayer():
    """Test server prayer invocation."""
    result = invoke_prayer()

    assert result["status"] in ["success", "error"]
    assert "mantra" in result
    assert "eternal" in result["mantra"].lower()


def test_scan_vault_empty():
    """Test vault scanning with no files."""
    result = scan_vault(pattern="*.nonexistent")

    assert result["status"] == "success"
    assert result["count"] == 0
    assert isinstance(result["files"], list)


def test_scan_vault_with_limit():
    """Test vault scanning with limit."""
    result = scan_vault(pattern="*.*", limit=5)

    assert result["status"] == "success"
    assert result["count"] <= 5
    assert len(result["files"]) <= 5


def test_get_vault_stats():
    """Test vault statistics."""
    result = get_vault_stats()

    assert result["status"] == "success"
    assert "total_files" in result
    assert "images" in result
    assert isinstance(result["total_files"], int)
