"""
State Management for GG Workflow Framework

This module provides persistent state management for workflows with:
- In-memory state for fast access
- Persistent storage (SQLite/Redis)
- State versioning and snapshots
- State recovery and rollback
- State compression and optimization

Author: Grokputer Team
Date: 2026-01-11
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from .nodes.base import NodeContext

logger = logging.getLogger(__name__)


class StateSnapshot:
    """
    Represents a snapshot of workflow state at a point in time.

    Attributes:
        snapshot_id: Unique identifier for this snapshot
        workflow_id: ID of the workflow this snapshot belongs to
        timestamp: When the snapshot was created
        data: The actual state data
        metadata: Additional metadata about the snapshot
    """

    def __init__(
        self,
        snapshot_id: str,
        workflow_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.snapshot_id = snapshot_id
        self.workflow_id = workflow_id
        self.timestamp = datetime.now()
        self.data = data.copy() if data else {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for serialization."""
        return {
            "snapshot_id": self.snapshot_id,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        """Create snapshot from dictionary."""
        snapshot = cls(
            snapshot_id=data["snapshot_id"],
            workflow_id=data["workflow_id"],
            data=data["data"],
            metadata=data.get("metadata", {}),
        )
        snapshot.timestamp = datetime.fromisoformat(data["timestamp"])
        return snapshot


class StateManager:
    """
    Manages workflow state with persistence and versioning.

    Features:
    - In-memory state for fast access
    - Persistent storage with SQLite/Redis
    - Automatic snapshots and versioning
    - State recovery and rollback
    - Compression for large states
    """

    def __init__(
        self,
        workflow_id: str,
        storage_path: Optional[str] = None,
        enable_redis: bool = True,
        max_snapshots: int = 10,
    ):
        """
        Initialize state manager.

        Args:
            workflow_id: Unique identifier for the workflow
            storage_path: Path for persistent storage (defaults to ./workflow_states)
            enable_redis: Whether to use Redis for caching
            max_snapshots: Maximum number of snapshots to keep
        """
        self.workflow_id = workflow_id
        self.max_snapshots = max_snapshots

        # Storage setup
        self.storage_path = Path(storage_path or "workflow_states")
        self.storage_path.mkdir(exist_ok=True)

        # In-memory state
        self.current_state: Dict[str, Any] = {}
        self.state_lock = threading.Lock()

        # Snapshots
        self.snapshots: List[StateSnapshot] = []
        self.snapshots_lock = threading.Lock()

        # SQLite setup
        self.db_path = self.storage_path / f"{workflow_id}.db"
        self.db_conn = sqlite3.connect(str(self.db_path))
        self._create_tables()

        # Redis setup
        self.redis_client = None
        if enable_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost', port=6379, db=1, decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"StateManager: Redis connected for workflow {workflow_id}")
            except redis.ConnectionError:
                logger.warning("StateManager: Redis connection failed, using SQLite only")
                self.redis_client = None

        # Load existing state
        self._load_state_from_persistence()

        logger.info(f"StateManager initialized for workflow {workflow_id}")

    def _create_tables(self):
        """Create necessary database tables."""
        cursor = self.db_conn.cursor()

        # States table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS states (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # Snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT
            )
        ''')

        self.db_conn.commit()

    def _load_state_from_persistence(self):
        """Load state from persistent storage."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT key, value FROM states')
            rows = cursor.fetchall()

            with self.state_lock:
                for key, value in rows:
                    try:
                        self.current_state[key] = json.loads(value)
                    except json.JSONDecodeError:
                        # Store as string if not JSON
                        self.current_state[key] = value

            # Load recent snapshots
            cursor.execute('''
                SELECT snapshot_id, workflow_id, timestamp, data, metadata
                FROM snapshots
                WHERE workflow_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (self.workflow_id, self.max_snapshots))

            snapshot_rows = cursor.fetchall()
            with self.snapshots_lock:
                for row in snapshot_rows:
                    snapshot_data = {
                        "snapshot_id": row[0],
                        "workflow_id": row[1],
                        "timestamp": row[2],
                        "data": json.loads(row[3]),
                        "metadata": json.loads(row[4]) if row[4] else {}
                    }
                    self.snapshots.append(StateSnapshot.from_dict(snapshot_data))

            logger.info(f"Loaded {len(self.current_state)} state keys and {len(self.snapshots)} snapshots")

        except Exception as e:
            logger.warning(f"Failed to load state from persistence: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from state.

        Args:
            key: State key
            default: Default value if key not found

        Returns:
            State value
        """
        with self.state_lock:
            return self.current_state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in state.

        Args:
            key: State key
            value: Value to store
        """
        with self.state_lock:
            self.current_state[key] = value

        # Persist to storage
        self._persist_key(key, value)

        # Update Redis cache
        if self.redis_client:
            try:
                redis_key = f"workflow:{self.workflow_id}:state:{key}"
                self.redis_client.set(redis_key, json.dumps(value))
            except Exception as e:
                logger.warning(f"Failed to update Redis cache: {e}")

    def delete(self, key: str) -> bool:
        """
        Delete a key from state.

        Args:
            key: State key to delete

        Returns:
            True if key existed and was deleted
        """
        with self.state_lock:
            if key in self.current_state:
                del self.current_state[key]

                # Remove from persistence
                self._delete_key(key)

                # Remove from Redis
                if self.redis_client:
                    try:
                        redis_key = f"workflow:{self.workflow_id}:state:{key}"
                        self.redis_client.delete(redis_key)
                    except Exception as e:
                        logger.warning(f"Failed to delete from Redis: {e}")

                return True
        return False

    def _persist_key(self, key: str, value: Any):
        """Persist a key-value pair to SQLite."""
        try:
            cursor = self.db_conn.cursor()
            json_value = json.dumps(value)
            timestamp = datetime.now().isoformat()

            cursor.execute('''
                INSERT OR REPLACE INTO states (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, json_value, timestamp))

            self.db_conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist key {key}: {e}")

    def _delete_key(self, key: str):
        """Delete a key from SQLite."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('DELETE FROM states WHERE key = ?', (key,))
            self.db_conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")

    def create_snapshot(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a snapshot of current state.

        Args:
            metadata: Optional metadata for the snapshot

        Returns:
            Snapshot ID
        """
        snapshot_id = f"{self.workflow_id}_{int(datetime.now().timestamp())}"

        with self.state_lock:
            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                workflow_id=self.workflow_id,
                data=self.current_state.copy(),
                metadata=metadata,
            )

        with self.snapshots_lock:
            self.snapshots.append(snapshot)

            # Limit number of snapshots
            if len(self.snapshots) > self.max_snapshots:
                # Remove oldest snapshots
                self.snapshots = self.snapshots[-self.max_snapshots:]

        # Persist snapshot
        self._persist_snapshot(snapshot)

        logger.info(f"Created snapshot {snapshot_id} for workflow {self.workflow_id}")
        return snapshot_id

    def _persist_snapshot(self, snapshot: StateSnapshot):
        """Persist snapshot to SQLite."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO snapshots
                (snapshot_id, workflow_id, timestamp, data, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                snapshot.snapshot_id,
                snapshot.workflow_id,
                snapshot.timestamp.isoformat(),
                json.dumps(snapshot.data),
                json.dumps(snapshot.metadata) if snapshot.metadata else None,
            ))
            self.db_conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist snapshot {snapshot.snapshot_id}: {e}")

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore state from a snapshot.

        Args:
            snapshot_id: ID of snapshot to restore

        Returns:
            True if snapshot was found and restored
        """
        with self.snapshots_lock:
            for snapshot in self.snapshots:
                if snapshot.snapshot_id == snapshot_id:
                    with self.state_lock:
                        self.current_state = snapshot.data.copy()

                    # Re-persist all keys
                    for key, value in self.current_state.items():
                        self._persist_key(key, value)

                    logger.info(f"Restored snapshot {snapshot_id} for workflow {self.workflow_id}")
                    return True

        logger.warning(f"Snapshot {snapshot_id} not found")
        return False

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all available snapshots.

        Returns:
            List of snapshot information
        """
        with self.snapshots_lock:
            return [
                {
                    "snapshot_id": s.snapshot_id,
                    "timestamp": s.timestamp.isoformat(),
                    "metadata": s.metadata,
                }
                for s in self.snapshots
            ]

    def get_workflow_context(self) -> NodeContext:
        """
        Get current state as a NodeContext for workflow execution.

        Returns:
            NodeContext with current state
        """
        with self.state_lock:
            return NodeContext(
                data=self.current_state.copy(),
                metadata={
                    "workflow_id": self.workflow_id,
                    "snapshot_count": len(self.snapshots),
                    "state_keys": list(self.current_state.keys()),
                },
                state=self.current_state.copy(),
            )

    def update_from_context(self, context: NodeContext) -> None:
        """
        Update state from a NodeContext.

        Args:
            context: Context to update from
        """
        # Update data
        for key, value in context.data.items():
            self.set(key, value)

        # Update state
        for key, value in context.state.items():
            self.set(f"_state_{key}", value)

    def clear(self) -> None:
        """Clear all state data."""
        with self.state_lock:
            keys_to_delete = list(self.current_state.keys())
            self.current_state.clear()

        # Delete from persistence
        for key in keys_to_delete:
            self._delete_key(key)

        # Clear Redis
        if self.redis_client:
            try:
                # Delete all keys for this workflow
                pattern = f"workflow:{self.workflow_id}:state:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Failed to clear Redis cache: {e}")

        logger.info(f"Cleared all state for workflow {self.workflow_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        with self.state_lock:
            state_size = len(self.current_state)

        with self.snapshots_lock:
            snapshot_count = len(self.snapshots)

        return {
            "workflow_id": self.workflow_id,
            "state_keys": state_size,
            "snapshots": snapshot_count,
            "storage_path": str(self.storage_path),
            "redis_enabled": self.redis_client is not None,
            "db_path": str(self.db_path),
        }

    def close(self):
        """Close state manager and cleanup resources."""
        if self.db_conn:
            self.db_conn.close()
        logger.info(f"StateManager closed for workflow {self.workflow_id}")


# Global state managers cache
_state_managers: Dict[str, StateManager] = {}
_state_managers_lock = threading.Lock()


def get_state_manager(workflow_id: str, **kwargs) -> StateManager:
    """
    Get or create a state manager for a workflow.

    Args:
        workflow_id: Workflow identifier
        **kwargs: Additional arguments for StateManager constructor

    Returns:
        StateManager instance
    """
    with _state_managers_lock:
        if workflow_id not in _state_managers:
            _state_managers[workflow_id] = StateManager(workflow_id, **kwargs)

        return _state_managers[workflow_id]


def close_all_state_managers():
    """Close all cached state managers."""
    with _state_managers_lock:
        for manager in _state_managers.values():
            manager.close()
        _state_managers.clear()