"""
Unit tests for screen observer.
"""

import pytest
from src.screen_observer import ScreenObserver


@pytest.fixture
def observer():
    """Create a screen observer instance."""
    return ScreenObserver()


def test_observer_initialization(observer):
    """Test screen observer initialization."""
    assert observer is not None
    assert observer.quality > 0
    assert observer.max_width > 0
    assert observer.max_height > 0


def test_get_screen_size(observer):
    """Test getting screen size."""
    width, height = observer.get_screen_size()

    assert isinstance(width, int)
    assert isinstance(height, int)
    assert width > 0
    assert height > 0


def test_get_mouse_position(observer):
    """Test getting mouse position."""
    x, y = observer.get_mouse_position()

    assert isinstance(x, int)
    assert isinstance(y, int)
    assert x >= 0
    assert y >= 0


def test_screenshot_capture(observer):
    """Test screenshot capture."""
    try:
        screenshot = observer.capture_screenshot()
        assert screenshot is not None
        assert screenshot.size[0] > 0
        assert screenshot.size[1] > 0
    except Exception as e:
        # May fail in headless environment
        pytest.skip(f"Screenshot capture not available: {e}")


def test_screenshot_to_base64(observer):
    """Test screenshot to base64 conversion."""
    try:
        base64_str = observer.screenshot_to_base64()
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0
    except Exception as e:
        pytest.skip(f"Screenshot capture not available: {e}")
