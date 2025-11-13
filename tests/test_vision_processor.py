"""
Unit tests for vision processor.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.vision_processor import VisionProcessor


class TestVisionProcessor:
    def test_initialization(self):
        """Test vision processor initialization."""
        processor = VisionProcessor()
        assert processor is not None

    @patch("src.vision_processor.cv2")
    def test_process_image(self, mock_cv2):
        """Test image processing."""
        mock_image = MagicMock()
        mock_cv2.imread.return_value = mock_image

        processor = VisionProcessor()

        result = processor.process_image("fake_path.jpg")

        assert result is not None
        # Since mocked, just check it returns something
