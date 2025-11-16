"""
Test Vision Integration

Tests the integration of vision processing, UI understanding, and multi-modal reasoning components.
"""

import asyncio
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw

# Skip all tests if required dependencies are missing
pytest.importorskip("PIL", reason="PIL not installed")
pytest.importorskip("cv2", reason="opencv-python not installed")

try:
    from src.vision_processor import VisionProcessor, VisualAnalysis
    from src.ui_understanding import UIUnderstandingModule, UIUnderstanding
    from src.multimodal_reasoning import MultiModalReasoningEngine, ReasoningContext
    from src.multimodal_processor import MultiModalInput
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class TestVisionIntegration:
    """Test suite for vision integration components."""

    @pytest.fixture
    def vision_processor(self):
        """Create vision processor instance."""
        return VisionProcessor()

    @pytest.fixture
    def ui_understanding(self):
        """Create UI understanding instance."""
        return UIUnderstandingModule()

    @pytest.fixture
    def multimodal_reasoning(self):
        """Create multi-modal reasoning instance."""
        return MultiModalReasoningEngine()

    @pytest.fixture
    def sample_image_path(self):
        """Create a sample test image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Create a simple test image with some UI-like elements
            img = Image.new("RGB", (400, 300), color="white")
            draw = ImageDraw.Draw(img)

            # Draw a rectangle (like a button)
            draw.rectangle([50, 50, 150, 100], fill="blue", outline="black")
            # Draw some text
            draw.text((60, 60), "Click Me", fill="white")

            # Draw another rectangle (like an input field)
            draw.rectangle([50, 150, 350, 180], fill="lightgray", outline="black")

            img.save(tmp.name)
            return tmp.name

    @pytest.mark.asyncio
    async def test_vision_processor_basic_analysis(self, vision_processor, sample_image_path):
        """Test basic vision processing functionality."""
        analysis = await vision_processor.analyze_image(sample_image_path)

        assert isinstance(analysis, VisualAnalysis)
        assert analysis.image_path == sample_image_path
        assert analysis.image_metadata is not None
        assert "width" in analysis.image_metadata
        assert "height" in analysis.image_metadata

    @pytest.mark.asyncio
    async def test_screenshot_analysis(self, vision_processor, sample_image_path):
        """Test screenshot-specific analysis."""
        ui_analysis = await vision_processor.analyze_screenshot(sample_image_path)

        assert isinstance(ui_analysis, dict)
        assert "ui_elements" in ui_analysis
        assert "layout_structure" in ui_analysis
        assert "interactive_elements" in ui_analysis
        assert "color_scheme" in ui_analysis
        assert "accessibility_score" in ui_analysis

        # Should detect some UI elements
        assert isinstance(ui_analysis["ui_elements"], list)

    @pytest.mark.asyncio
    async def test_ui_understanding(self, ui_understanding, sample_image_path):
        """Test UI understanding functionality."""
        understanding = await ui_understanding.understand_ui(sample_image_path)

        assert isinstance(understanding, UIUnderstanding)
        assert understanding.screenshot_path == sample_image_path
        assert isinstance(understanding.ui_hierarchy, list)
        assert isinstance(understanding.primary_actions, list)
        assert isinstance(understanding.accessibility_issues, list)

    @pytest.mark.asyncio
    async def test_multimodal_reasoning_basic(self, multimodal_reasoning):
        """Test basic multi-modal reasoning functionality."""
        # Create mock input
        input_data = MultiModalInput(
            text="Please analyze this screenshot and tell me what to do", image_path="/fake/path/screenshot.png"
        )

        context = ReasoningContext(user_intent="analyze screenshot", task_type="ui_analysis")

        # Mock the multimodal processor to avoid actual file processing
        with patch.object(multimodal_reasoning.multimodal_processor, "process_multimodal_input") as mock_process:
            mock_analysis = Mock()
            mock_analysis.confidence_score = 0.8
            mock_analysis.cross_modal_insights = [
                {"type": "text_visual_consistency", "description": "Text matches visual content", "confidence": 0.9}
            ]
            mock_process.return_value = mock_analysis

            result = await multimodal_reasoning.reason_multimodal(input_data, context)

            assert result is not None
            assert result.decision != ""
            assert isinstance(result.confidence, float)
            assert isinstance(result.reasoning_chain, list)
            assert isinstance(result.recommended_actions, list)
            assert isinstance(result.insights, list)

    @pytest.mark.asyncio
    async def test_end_to_end_integration(
        self, vision_processor, ui_understanding, multimodal_reasoning, sample_image_path
    ):
        """Test end-to-end integration of vision components."""
        # Step 1: Vision processing
        visual_analysis = await vision_processor.analyze_image(sample_image_path)
        assert visual_analysis is not None

        # Step 2: Screenshot analysis
        screenshot_analysis = await vision_processor.analyze_screenshot(sample_image_path)
        assert screenshot_analysis is not None

        # Step 3: UI understanding
        ui_understanding_result = await ui_understanding.understand_ui(sample_image_path)
        assert ui_understanding_result is not None

        # Step 4: Multi-modal reasoning (mocked)
        input_data = MultiModalInput(text="Analyze this UI screenshot", image_path=sample_image_path)

        context = ReasoningContext(user_intent="ui analysis", task_type="interface_understanding")

        # Mock to avoid full processing
        with patch.object(multimodal_reasoning.multimodal_processor, "process_multimodal_input") as mock_process:
            mock_analysis = Mock()
            mock_analysis.confidence_score = 0.85
            mock_analysis.cross_modal_insights = [
                {"type": "ui_element_detection", "description": "Detected UI elements", "confidence": 0.8}
            ]
            mock_process.return_value = mock_analysis

            reasoning_result = await multimodal_reasoning.reason_multimodal(input_data, context)

            assert reasoning_result is not None
            assert reasoning_result.confidence > 0

    def test_reasoning_context_creation(self):
        """Test reasoning context creation."""
        context = ReasoningContext(
            user_intent="test intent",
            task_type="test task",
            constraints={"time_limit": 30},
            domain_knowledge={"ui_patterns": ["button", "input"]},
        )

        assert context.user_intent == "test intent"
        assert context.task_type == "test task"
        assert context.constraints["time_limit"] == 30
        assert "ui_patterns" in context.domain_knowledge

    @pytest.mark.asyncio
    async def test_error_handling(self, multimodal_reasoning):
        """Test error handling in vision integration."""
        # Test with invalid input
        input_data = MultiModalInput(text="test")
        context = ReasoningContext()

        # Should handle gracefully
        result = await multimodal_reasoning.reason_multimodal(input_data, context)

        # Should still return a result (even if with low confidence)
        assert result is not None
        assert isinstance(result, dict) or hasattr(result, "decision")

    def test_component_imports(self):
        """Test that all components can be imported."""
        try:
            from src.vision_processor import VisionProcessor
            from src.ui_understanding import UIUnderstandingModule
            from src.multimodal_reasoning import MultiModalReasoningEngine
            from src.multimodal_processor import MultiModalProcessor

            # Test instantiation
            vp = VisionProcessor()
            uu = UIUnderstandingModule()
            mmr = MultiModalReasoningEngine()
            mmp = MultiModalProcessor()

            assert vp is not None
            assert uu is not None
            assert mmr is not None
            assert mmp is not None

        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    @pytest.fixture(autouse=True)
    def cleanup_sample_image(self, sample_image_path):
        """Clean up sample image after tests."""
        yield
        if os.path.exists(sample_image_path):
            os.unlink(sample_image_path)


async def run_basic_test():
    print("Running basic vision integration test...")

    # Create sample image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new("RGB", (200, 100), color="lightblue")
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 190, 90], fill="white", outline="black")
        draw.text((20, 20), "Test Button", fill="black")
        img.save(tmp.name)
        image_path = tmp.name

    try:
        # Test vision processor
        vp = VisionProcessor()
        analysis = await vp.analyze_image(image_path)
        print(f"✓ Vision analysis completed: {analysis.scene_description}")

        # Test screenshot analysis
        screenshot_analysis = await vp.analyze_screenshot(image_path)
        print(f"✓ Screenshot analysis completed: {len(screenshot_analysis['ui_elements'])} UI elements detected")

        # Test UI understanding
        uu = UIUnderstandingModule()
        understanding = await uu.understand_ui(image_path)
        print(f"✓ UI understanding completed: {understanding.page_type}")

        print("All vision integration tests passed!")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        if os.path.exists(image_path):
            os.unlink(image_path)


if __name__ == "__main__":
    asyncio.run(run_basic_test())
