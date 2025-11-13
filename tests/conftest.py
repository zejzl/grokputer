import pytest
import sys
from unittest.mock import Mock, patch


# Global mocks for common deps
@pytest.fixture(autouse=True)
def mock_external_deps():
    with patch("openai.OpenAI", return_value=Mock()) as mock_openai:
        with patch.dict("sys.modules", {"pyautogui": Mock(), "src.tools": Mock()}) as mock_modules:
            yield


# Async fixture if needed
@pytest.fixture
def event_loop():
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Register asyncio plugin
pytest_plugins = ["pytest_asyncio"]
