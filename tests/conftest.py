import pytest
import sys
import warnings
from unittest.mock import Mock, patch

# Suppress llama_cpp warnings
warnings.filterwarnings("ignore", category=UserWarning, module="llama_cpp")


# Global mocks for common deps
@pytest.fixture(autouse=True)
def mock_external_deps():
    with patch("openai.OpenAI", return_value=Mock()) as mock_openai:
        with patch.dict("sys.modules", {"pyautogui": Mock(), "src.tools": Mock()}) as mock_modules:
            with patch("redis.Redis", return_value=Mock()) as mock_redis:
                # Mock Redis methods
                mock_redis_instance = Mock()
                mock_redis_instance.ping.return_value = True
                mock_redis_instance.get.return_value = None
                mock_redis_instance.set.return_value = True
                mock_redis_instance.exists.return_value = False
                mock_redis_instance.delete.return_value = 1
                mock_redis.return_value = mock_redis_instance
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
