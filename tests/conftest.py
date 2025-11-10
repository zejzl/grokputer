import pytest
from unittest.mock import Mock, patch

# Global mocks for common deps
@pytest.fixture(autouse=True)
def mock_external_deps():
    with patch('openai.OpenAI', return_value=Mock()) as mock_openai:
        with patch('pyautogui.*', new=Mock()) as mock_pyautogui:
            with patch('src.tools.*', new=Mock()) as mock_tools:  # Stub tools if needed
                yield

# Async fixture if needed
@pytest.fixture
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Register asyncio plugin
pytest_plugins = ['pytest_asyncio']
