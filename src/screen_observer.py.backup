"""
Screen observation module for Grokputer.
Captures screenshots and converts them to base64 for Grok analysis.
"""

import base64
import logging
from io import BytesIO
from typing import Optional, Tuple
import pyautogui
from PIL import Image
from src import config

logger = logging.getLogger(__name__)


class ScreenObserver:
    """
    Handles screen capture and observation for the Grokputer system.
    """

    def __init__(
        self,
        quality: int = None,
        max_size: Tuple[int, int] = None
    ):
        """
        Initialize the screen observer.

        Args:
            quality: JPEG quality (1-100), defaults to config value
            max_size: Maximum (width, height), defaults to config value
        """
        self.quality = quality or config.SCREENSHOT_QUALITY
        self.max_width = max_size[0] if max_size else config.MAX_SCREENSHOT_WIDTH
        self.max_height = max_size[1] if max_size else config.MAX_SCREENSHOT_HEIGHT

        # Disable pyautogui failsafe for automated control
        pyautogui.FAILSAFE = True  # Keep failsafe enabled for safety
        pyautogui.PAUSE = 0.1  # Small pause between actions

        logger.info(
            f"Screen observer initialized: quality={self.quality}, "
            f"max_size={self.max_width}x{self.max_height}"
        )

    def capture_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """
        Capture a screenshot of the entire screen or a specific region.

        Args:
            region: Optional (left, top, width, height) tuple for partial capture

        Returns:
            PIL Image object
        """
        try:
            if region:
                logger.info(f"Capturing screenshot region: {region}")
                screenshot = pyautogui.screenshot(region=region)
            else:
                logger.info("Capturing full screenshot")
                screenshot = pyautogui.screenshot()

            # Resize if needed
            screenshot = self._resize_if_needed(screenshot)

            return screenshot

        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            raise

    def screenshot_to_base64(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        format: str = "PNG"
    ) -> str:
        """
        Capture screenshot and convert to base64 string.

        Args:
            region: Optional region to capture
            format: Image format (PNG, JPEG)

        Returns:
            Base64-encoded image string
        """
        try:
            screenshot = self.capture_screenshot(region)

            # Convert to base64
            buffered = BytesIO()
            if format.upper() == "JPEG":
                screenshot.save(buffered, format="JPEG", quality=self.quality)
            else:
                screenshot.save(buffered, format="PNG")

            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            logger.info(f"Screenshot encoded to base64: {len(img_base64)} characters")
            return img_base64

        except Exception as e:
            logger.error(f"Error converting screenshot to base64: {e}")
            raise

    def save_screenshot(
        self,
        filepath: str,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """
        Capture and save screenshot to file.

        Args:
            filepath: Path to save the screenshot
            region: Optional region to capture

        Returns:
            True if successful, False otherwise
        """
        try:
            screenshot = self.capture_screenshot(region)
            screenshot.save(filepath)
            logger.info(f"Screenshot saved to: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return False

    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """
        Resize image if it exceeds maximum dimensions.

        Args:
            image: PIL Image to resize

        Returns:
            Resized image (or original if no resize needed)
        """
        width, height = image.size

        if width <= self.max_width and height <= self.max_height:
            return image

        # Calculate scaling factor
        scale = min(self.max_width / width, self.max_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        logger.info(f"Resizing screenshot from {width}x{height} to {new_width}x{new_height}")

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get the current screen resolution.

        Returns:
            Tuple of (width, height)
        """
        size = pyautogui.size()
        logger.debug(f"Screen size: {size.width}x{size.height}")
        return (size.width, size.height)

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Get current mouse cursor position.

        Returns:
            Tuple of (x, y) coordinates
        """
        pos = pyautogui.position()
        return (pos.x, pos.y)

    def locate_on_screen(
        self,
        template_path: str,
        confidence: float = 0.8
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Locate an image template on the screen.

        Args:
            template_path: Path to template image
            confidence: Match confidence (0.0-1.0)

        Returns:
            Tuple of (left, top, width, height) or None if not found
        """
        try:
            location = pyautogui.locateOnScreen(template_path, confidence=confidence)
            if location:
                logger.info(f"Template found at: {location}")
                return location
            else:
                logger.info(f"Template not found: {template_path}")
                return None

        except Exception as e:
            logger.error(f"Error locating template: {e}")
            return None
