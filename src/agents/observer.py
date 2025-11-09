"""
Observer Agent for Grokputer Swarm

Captures and analyzes screen state for the swarm:
- Screenshot capture with quality modes
- Perceptual hashing for duplicate detection
- Grok vision API integration for analysis
- Efficient caching to minimize redundant captures
- Region-specific capture support

Extends BaseAgent for lifecycle management.
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, Any, Optional, Tuple

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger
from src.screen_observer import ScreenObserver
from src.grok_client import GrokClient
from src import config

logger = logging.getLogger(__name__)


class ScreenshotCache:
    """
    Caches recent screenshots to avoid redundant captures and analysis.

    Uses perceptual hashing (simplified) to detect similar screenshots.
    Phase 1: MD5 hash (Phase 2 will use imagehash.phash for true perceptual hashing)
    """
    def __init__(self, max_size: int = 10, similarity_threshold: float = 0.95):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.cache: Dict[str, Dict[str, Any]] = {}  # hash -> {screenshot, analysis, timestamp}

    def compute_hash(self, screenshot_b64: str) -> str:
        """Compute hash of screenshot (simplified perceptual hash)."""
        # Phase 1: Use MD5 hash (Phase 2: use imagehash.phash)
        return hashlib.md5(screenshot_b64.encode()).hexdigest()

    def get(self, screenshot_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached screenshot and analysis if available."""
        if screenshot_hash in self.cache:
            entry = self.cache[screenshot_hash]
            logger.info(f"[ScreenshotCache] Cache hit: {screenshot_hash[:8]}...")
            return entry
        return None

    def put(self, screenshot_hash: str, screenshot_b64: str, analysis: Dict[str, Any]):
        """Add screenshot and analysis to cache."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
            logger.debug(f"[ScreenshotCache] Evicted oldest entry: {oldest_key[:8]}...")

        self.cache[screenshot_hash] = {
            'screenshot': screenshot_b64,
            'analysis': analysis,
            'timestamp': time.time()
        }
        logger.info(f"[ScreenshotCache] Cached: {screenshot_hash[:8]}... (size: {len(self.cache)})")

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("[ScreenshotCache] Cache cleared")


class Observer(BaseAgent):
    """
    Observer Agent: Captures and analyzes screen state.

    Capabilities:
    - Screenshot capture (full screen or region)
    - Quality modes: high/medium/low (via config)
    - Perceptual hashing for duplicate detection
    - Grok vision API integration
    - Efficient caching (10 recent screenshots)
    - Async operation with proper error handling

    Performance:
    - Cache hits: <50ms (no API call)
    - Cache miss: ~2-3s (Grok API call)
    - Screenshot capture: ~200ms
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config_dict: Dict[str, Any],
        heartbeat_interval: float = 10.0
    ):
        super().__init__('observer', message_bus, session_logger, config_dict, heartbeat_interval)

        # Initialize screen observer
        quality = config_dict.get("screenshot_quality", config.SCREENSHOT_QUALITY)
        max_size = (
            config_dict.get("max_screenshot_width", config.MAX_SCREENSHOT_WIDTH),
            config_dict.get("max_screenshot_height", config.MAX_SCREENSHOT_HEIGHT)
        )
        self.screen_observer = ScreenObserver(quality=quality, max_size=max_size)

        # Initialize Grok client for vision analysis
        self.grok_client = GrokClient()

        # Initialize screenshot cache
        cache_size = config_dict.get("screenshot_cache_size", 10)
        self.cache = ScreenshotCache(max_size=cache_size)

        # Statistics
        self.stats = {
            "screenshots_captured": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "grok_calls": 0,
            "total_capture_time": 0.0,
            "total_analysis_time": 0.0
        }

        logger.info("[Observer] Initialized with ScreenObserver and GrokClient")

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process incoming messages from Coordinator.

        Handles:
        - subtask: Capture and analyze screen
        - capture_screen: Legacy direct capture
        - analyze_screen: Analyze existing screenshot

        Returns response message or None.
        """
        msg_type = message.message_type
        content = message.content

        if msg_type == "subtask":
            return await self._handle_subtask(message)
        elif msg_type == "capture_screen":
            return await self._handle_capture(message)
        elif msg_type == "analyze_screen":
            return await self._handle_analysis(message)
        else:
            logger.warning(f"[Observer] Unknown message type: {msg_type}")
            return None

    async def _handle_subtask(self, message: Message) -> Dict:
        """Handle subtask from Coordinator."""
        action = message.content.get("action")
        params = message.content.get("params", {})
        task_id = message.content.get("task_id", "unknown")

        logger.info(f"[Observer] Received subtask: {action} for task {task_id}")

        if action == "capture_screen":
            return await self._execute_capture_and_analyze(task_id, params)
        else:
            logger.error(f"[Observer] Unknown action: {action}")
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": f"Unknown action: {action}"
                },
                "priority": MessagePriority.NORMAL
            }

    async def _execute_capture_and_analyze(self, task_id: str, params: Dict) -> Dict:
        """
        Capture screenshot and analyze with Grok vision.

        Checks cache first for performance optimization.
        """
        region = params.get("region", None)
        force_refresh = params.get("force_refresh", False)

        try:
            # Capture screenshot
            start_time = time.time()
            screenshot_b64 = await self._capture_screenshot(region)
            capture_time = time.time() - start_time

            self.stats["screenshots_captured"] += 1
            self.stats["total_capture_time"] += capture_time

            # Compute hash
            screenshot_hash = self.cache.compute_hash(screenshot_b64)

            # Check cache
            if not force_refresh:
                cached = self.cache.get(screenshot_hash)
                if cached:
                    self.stats["cache_hits"] += 1
                    logger.info(f"[Observer] Cache hit for task {task_id}")

                    return {
                        "to": "coordinator",
                        "type": "response",
                        "content": {
                            "task_id": task_id,
                            "status": "success",
                            "result": {
                                "screenshot_b64": screenshot_b64,
                                "analysis": cached['analysis'],
                                "from_cache": True,
                                "dimensions": self.screen_observer.get_screen_size()
                            }
                        },
                        "priority": MessagePriority.NORMAL
                    }

            # Cache miss - analyze with Grok
            self.stats["cache_misses"] += 1
            start_time = time.time()
            analysis = await self._analyze_screenshot(screenshot_b64)
            analysis_time = time.time() - start_time

            self.stats["total_analysis_time"] += analysis_time

            # Cache the result
            self.cache.put(screenshot_hash, screenshot_b64, analysis)

            # Log execution
            self.session_logger.log_tool_execution(
                tool_name="screenshot_analysis",
                params={"region": region},
                result={"analysis": analysis, "cache": "miss"},
                status="success"
            )

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "success",
                    "result": {
                        "screenshot_b64": screenshot_b64,
                        "analysis": analysis,
                        "from_cache": False,
                        "capture_time_ms": int(capture_time * 1000),
                        "analysis_time_ms": int(analysis_time * 1000),
                        "dimensions": self.screen_observer.get_screen_size()
                    }
                },
                "priority": MessagePriority.NORMAL
            }

        except Exception as e:
            logger.error(f"[Observer] Capture and analysis failed: {e}")
            self.session_logger.log_agent_error(self.agent_id, f"Capture failed: {e}")

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e)
                },
                "priority": MessagePriority.HIGH
            }

    async def _capture_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        Capture screenshot and return base64 string.

        Args:
            region: Optional (left, top, width, height) tuple

        Returns:
            Base64-encoded screenshot
        """
        # Run in thread pool (PyAutoGUI is blocking)
        screenshot_b64 = await asyncio.to_thread(
            self.screen_observer.screenshot_to_base64,
            region=region,
            format="PNG"
        )

        logger.info(f"[Observer] Screenshot captured: {len(screenshot_b64)} bytes (base64)")
        return screenshot_b64

    async def _analyze_screenshot(self, screenshot_b64: str) -> Dict[str, Any]:
        """
        Analyze screenshot using Grok vision API.

        Args:
            screenshot_b64: Base64-encoded screenshot

        Returns:
            Analysis results from Grok
        """
        self.stats["grok_calls"] += 1

        # Build vision prompt
        prompt = (
            "Analyze this screenshot and provide:\n"
            "1. What is visible on the screen?\n"
            "2. What applications/windows are open?\n"
            "3. Any UI elements that could be interacted with?\n"
            "4. Current state of the screen.\n\n"
            "Be concise and focus on actionable information."
        )

        # Call Grok vision API
        response = await asyncio.to_thread(
            self.grok_client.create_message,
            task=prompt,
            screenshot_base64=screenshot_b64
        )

        if response.get("status") == "success":
            analysis = {
                "content": response.get("content", ""),
                "model": response.get("model", "unknown"),
                "finish_reason": response.get("finish_reason", "unknown"),
                "timestamp": time.time()
            }
            logger.info(f"[Observer] Grok analysis complete: {len(analysis['content'])} chars")
            return analysis
        else:
            error = response.get("error", "Unknown error")
            logger.error(f"[Observer] Grok analysis failed: {error}")
            return {
                "error": error,
                "timestamp": time.time()
            }

    async def _handle_capture(self, message: Message) -> Dict:
        """Handle legacy capture_screen message."""
        region = message.content.get("region", None)
        task_id = message.content.get("task_id", "legacy")

        return await self._execute_capture_and_analyze(task_id, {"region": region})

    async def _handle_analysis(self, message: Message) -> Dict:
        """Handle analyze_screen message with existing screenshot."""
        screenshot_b64 = message.content.get("screenshot_b64", "")
        task_id = message.content.get("task_id", "analysis")

        if not screenshot_b64:
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": "No screenshot provided"
                },
                "priority": MessagePriority.NORMAL
            }

        try:
            analysis = await self._analyze_screenshot(screenshot_b64)

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "success",
                    "result": {"analysis": analysis}
                },
                "priority": MessagePriority.NORMAL
            }

        except Exception as e:
            logger.error(f"[Observer] Analysis failed: {e}")
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e)
                },
                "priority": MessagePriority.HIGH
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get Observer statistics."""
        total_captures = self.stats["screenshots_captured"]
        cache_total = self.stats["cache_hits"] + self.stats["cache_misses"]

        return {
            "screenshots_captured": total_captures,
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": f"{self.stats['cache_hits'] / cache_total * 100:.1f}%" if cache_total > 0 else "N/A",
            "grok_api_calls": self.stats["grok_calls"],
            "avg_capture_time_ms": int(self.stats["total_capture_time"] / total_captures * 1000) if total_captures > 0 else 0,
            "avg_analysis_time_ms": int(self.stats["total_analysis_time"] / self.stats["grok_calls"] * 1000) if self.stats["grok_calls"] > 0 else 0,
            "cache_size": len(self.cache.cache)
        }

    async def on_start(self):
        """Observer-specific startup."""
        logger.info("[Observer] Starting screen observation")

        # Test Grok connection
        try:
            connected = await asyncio.to_thread(self.grok_client.test_connection)
            if connected:
                logger.info("[Observer] Grok API connection successful")
            else:
                logger.warning("[Observer] Grok API connection failed (will retry on demand)")
        except Exception as e:
            logger.warning(f"[Observer] Could not test Grok connection: {e}")

    async def on_stop(self):
        """Observer-specific shutdown."""
        logger.info("[Observer] Shutting down...")
        logger.info(f"[Observer] Final stats: {self.get_stats()}")
        self.cache.clear()
        logger.info("[Observer] Shutdown complete")
