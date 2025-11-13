"""
Unit tests for multimodal processor.
"""

import pytest
from unittest.mock import patch, MagicMock

# Skip entire module if cv2 is not available
cv2 = pytest.importorskip("cv2", reason="opencv-python not installed")

try:
    from src.multimodal_processor import MultimodalProcessor
except ImportError as e:
    pytest.skip(f"MultimodalProcessor not available: {e}", allow_module_level=True)


class TestMultimodalProcessor:
    def test_initialization(self):
        """Test multimodal processor initialization."""
        processor = MultimodalProcessor()
        assert processor is not None

    def test_process_text(self):
        """Test text processing."""
        processor = MultimodalProcessor()

        result = processor.process_text("Hello world")

        assert result is not None
        assert "text" in result

    @patch("src.multimodal_processor.VisionProcessor")
    def test_process_image(self, mock_vision):
        """Test image processing."""
        mock_vision.return_value.process_image.return_value = {"features": []}

        processor = MultimodalProcessor()

        result = processor.process_image("fake.jpg")

        assert result is not None
