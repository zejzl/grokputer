# Grokputer Exception Hierarchy
# Standardized error handling across the system

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GrokputerError(Exception):
    """Base exception for all Grokputer errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class APIError(GrokputerError):
    """API-related errors (Grok, Claude, Gemini, etc.)."""

    pass


class MemoryError(GrokputerError):
    """Memory system errors."""

    pass


class AgentError(GrokputerError):
    """Agent-related errors."""

    pass


class MessageBusError(GrokputerError):
    """Message bus communication errors."""

    pass


class VisionError(GrokputerError):
    """Computer vision and image processing errors."""

    pass


class ConfigurationError(GrokputerError):
    """Configuration and setup errors."""

    pass


class ValidationError(GrokputerError):
    """Data validation errors."""

    pass


class TimeoutError(GrokputerError):
    """Timeout-related errors."""

    pass


class ResourceError(GrokputerError):
    """Resource exhaustion or availability errors."""

    pass


# Standardized error handling utilities
def handle_error(error: Exception, context: str = "", log_level: str = "error") -> None:
    """
    Standardized error handling with logging and context.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        log_level: Logging level ('debug', 'info', 'warning', 'error', 'critical')
    """
    error_msg = f"[{context}] {type(error).__name__}: {error}" if context else f"{type(error).__name__}: {error}"

    log_func = getattr(logger, log_level, logger.error)
    log_func(error_msg)

    # For custom GrokputerError, log additional details
    if isinstance(error, GrokputerError) and error.details:
        logger.debug(f"[{context}] Error details: {error.details}")


def retry_with_backoff(func, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry (should be async)
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Result of the function call

    Raises:
        Last exception encountered
    """
    import asyncio
    import time

    async def wrapper(*args, **kwargs):
        delay = base_delay

        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    logger.error(f"All {max_attempts} attempts failed. Last error: {e}")
                    raise

                logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
                delay = min(delay * 2, max_delay)

    return wrapper
