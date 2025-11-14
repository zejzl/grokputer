"""
Memory Backend Factory for Grokputer.
Creates appropriate memory backend based on configuration with graceful fallback.
"""

import logging
from ..interfaces import MemoryConfig, MemoryBackend
from ..backends.redis_store import RedisMemoryBackend

try:
    from ..backends.pinecone_store import PineconeStore
    PINECONE_STORE_AVAILABLE = True
except ImportError:
    PINECONE_STORE_AVAILABLE = False

from .persistent_manager import PersistentMemoryManager
from ..hierarchical_memory import HierarchicalMemoryManager

logger = logging.getLogger(__name__)


def create_memory_backend(config: MemoryConfig) -> MemoryBackend:
    """
    Create memory backend based on configuration with automatic fallback.

    Args:
        config: Memory configuration specifying backend type

    Returns:
        MemoryBackend instance (with fallback to SQLite if preferred backend fails)

    Raises:
        RuntimeError: If all backends fail to initialize
    """
    backend_type = config.backend.lower()

    # Try requested backend first
    try:
        if backend_type == "hierarchical":
            # Create hierarchical memory with Redis as long-term backend
            try:
                long_term_backend = RedisMemoryBackend(config)
                logger.info("Hierarchical memory initialized with Redis backend")
                return HierarchicalMemoryManager(config, long_term_backend)
            except Exception as e:
                logger.warning(f"Redis unavailable for hierarchical memory: {e}, falling back to SQLite")
                long_term_backend = PersistentMemoryManager(config)
                return HierarchicalMemoryManager(config, long_term_backend)

        elif backend_type == "redis":
            backend = RedisMemoryBackend(config)
            logger.info("Redis memory backend initialized")
            return backend

        elif backend_type == "pinecone":
            if not PINECONE_STORE_AVAILABLE:
                logger.warning("Pinecone store not available (library not installed), falling back to SQLite")
                return PersistentMemoryManager(config)
            try:
                backend = PineconeStore(config, enable_hyde=config.enable_hyde)
                logger.info("Pinecone memory backend initialized with HyDE support")
                return backend
            except Exception as e:
                logger.warning(f"Pinecone backend failed: {e}, falling back to SQLite")
                return PersistentMemoryManager(config)

        elif backend_type == "sqlite":
            backend = PersistentMemoryManager(config)
            logger.info("SQLite memory backend initialized")
            return backend

        else:
            # Default to SQLite
            logger.info(f"Unknown backend '{backend_type}', defaulting to SQLite")
            return PersistentMemoryManager(config)

    except Exception as e:
        logger.error(f"Failed to initialize {backend_type} backend: {e}")

        # Fallback to SQLite if primary backend fails
        if backend_type != "sqlite":
            try:
                logger.warning(f"Falling back to SQLite memory backend")
                return PersistentMemoryManager(config)
            except Exception as fallback_error:
                logger.error(f"SQLite fallback also failed: {fallback_error}")
                raise RuntimeError(f"All memory backends failed to initialize") from fallback_error
        else:
            raise RuntimeError(f"SQLite backend initialization failed") from e
