"""
Observer Agent - Visual perception for the Pantheon

Captures screen observations and processes visual information.
Part of the core ORA (Observe-Reason-Act) loop.
"""

import logging
from typing import Dict, Any, Optional
from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessagePriority
from src.screen_observer import ScreenObserver

logger = logging.getLogger(__name__)


class ObserverAgent(BaseAgent):
    """
    Observer Agent - The eyes of the swarm.

    Responsibilities:
    - Capture screenshots on demand
    - Monitor screen changes
    - Extract visual information
    - Send observations to coordinator

    Message Types Handled:
    - 'observe_screen': Take a screenshot and return base64 data
    - 'get_mouse_position': Return current cursor position
    - 'get_screen_size': Return screen dimensions
    """

    async def on_start(self):
        """Initialize the screen observer when agent starts."""
        self.screen = ScreenObserver()
        logger.info(f"[{self.agent_id}] Screen observer initialized")

        # Send ready signal to coordinator
        # Send ready signal (disabled for Phase 1 - coordinator doesn't handle this yet)
        # msg = Message(

    #            from_agent=self.agent_id,
    #            to_agent="coordinator",
    #            message_type="agent_ready",
    #            content={
    #                "agent_id": self.agent_id,
    #                "capabilities": ["observe_screen", "get_mouse_position", "get_screen_size"]
    #            },
    #            priority=MessagePriority.NORMAL
    #        )
    # await self.message_bus.send(msg)

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process observation requests.

        Args:
            message: Message dict with 'type' and optional parameters

        Returns:
            Response dict with observation data, or None
        """
        msg_type = message.get("type")

        if msg_type == "observe_screen":
            return await self._observe_screen(message)

        elif msg_type == "get_mouse_position":
            return await self._get_mouse_position(message)

        elif msg_type == "get_screen_size":
            return await self._get_screen_size(message)

        else:
            logger.warning(f"[{self.agent_id}] Unknown message type: {msg_type}")
            return None

    async def _observe_screen(self, message: Message) -> Dict[str, Any]:
        """
        Capture screenshot and return as base64.

        Args:
            message: May contain 'region' for partial screenshot

        Returns:
            Dict with screenshot data
        """
        try:
            content = message.content
            region = content.get("region", None)
            format = content.get("format", "PNG")

            logger.info(f"[{self.agent_id}] Capturing screenshot (format={format})")

            # Capture screenshot using async screen observer
            screenshot_base64 = await self.screen.screenshot_to_base64(region=region, format=format)

            # Get screen dimensions for context
            width, height = self.screen.get_screen_size()

            logger.info(f"[{self.agent_id}] Screenshot captured: {len(screenshot_base64)} bytes")

            return {
                "to": message.get("from", "coordinator"),
                "type": "observation",
                "subtype": "screenshot",
                "data": screenshot_base64,
                "screen_size": {"width": width, "height": height},
                "format": format,
                "region": region,
                "timestamp": message.get("timestamp"),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"[{self.agent_id}] Screenshot failed: {e}")
            return {
                "to": message.get("from", "coordinator"),
                "type": "observation",
                "subtype": "screenshot",
                "status": "error",
                "error": str(e),
            }

    async def _get_mouse_position(self, message: Message) -> Dict[str, Any]:
        """
        Get current mouse cursor position.

        Returns:
            Dict with x, y coordinates
        """
        try:
            x, y = self.screen.get_mouse_position()

            logger.debug(f"[{self.agent_id}] Mouse position: ({x}, {y})")

            return {
                "to": message.get("from", "coordinator"),
                "type": "observation",
                "subtype": "mouse_position",
                "position": {"x": x, "y": y},
                "status": "success",
            }

        except Exception as e:
            logger.error(f"[{self.agent_id}] Get mouse position failed: {e}")
            return {
                "to": message.get("from", "coordinator"),
                "type": "observation",
                "subtype": "mouse_position",
                "status": "error",
                "error": str(e),
            }

    async def _get_screen_size(self, message: Message) -> Dict[str, Any]:
        """
        Get screen dimensions.

        Returns:
            Dict with width and height
        """
        try:
            width, height = self.screen.get_screen_size()

            logger.debug(f"[{self.agent_id}] Screen size: {width}x{height}")

            return {
                "to": message.get("from", "coordinator"),
                "type": "observation",
                "subtype": "screen_size",
                "size": {"width": width, "height": height},
                "status": "success",
            }

        except Exception as e:
            logger.error(f"[{self.agent_id}] Get screen size failed: {e}")
            return {
                "to": message.get("from", "coordinator"),
                "type": "observation",
                "subtype": "screen_size",
                "status": "error",
                "error": str(e),
            }

    async def on_stop(self):
        """Cleanup when agent stops."""
        logger.info(f"[{self.agent_id}] Observer agent shutting down")
