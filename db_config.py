"""
Enhanced Database Configuration for Grokputer
File: db_config.py
Description: SQLite wrapper with WAL mode, context manager, logging, and agent/Selenium methods.
Usage: Import and use with context manager for safe queries.
Enhancements (2024-11-10): WAL for concurrency, Selenium test logging, agent events, error handling, Python logging.
"""

import os
import json
import logging
import sqlite3
from pathlib import Path
from contextlib import contextmanager
import redis
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Database path
DB_PATH = Path("db") / "db.db"  # Use .db for the active file
DB_SQL_PATH = Path("db") / "db.sql"

# Ensure DB directory exists
DB_PATH.parent.mkdir(exist_ok=True)


@contextmanager
def get_connection():
    """Context manager for SQLite connection with WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Dict-like rows
    cursor = conn.cursor()

    # Enable WAL for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")  # Balance speed/safety

    try:
        yield cursor
        conn.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize DB by running schema from db.sql and creating enhanced tables if needed."""
    if not DB_SQL_PATH.exists():
        logger.warning(f"Schema file not found: {DB_SQL_PATH}")
        return

    try:
        # Check if we need to run the schema (only if conversations table doesn't exist)
        with get_connection() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            conversations_exists = cursor.fetchone()

            if not conversations_exists:
                # Only run the conversation-related parts of the schema
                logger.info("Creating conversation tables...")

                # Create conversation tables manually to avoid foreign key issues
                cursor.execute(
                    """
                    CREATE TABLE conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT UNIQUE NOT NULL,
                        user_id TEXT NOT NULL,
                        start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        end_time DATETIME,
                        status TEXT DEFAULT 'active',
                        total_messages INTEGER DEFAULT 0,
                        last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    );
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE conversation_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        message_id TEXT UNIQUE NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                    );
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        preference_key TEXT NOT NULL,
                        preference_value TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        source TEXT DEFAULT 'nli',
                        UNIQUE(user_id, preference_key)
                    );
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE conversation_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                    );
                """
                )

                # Create indexes
                cursor.execute("CREATE INDEX idx_conversations_user_id ON conversations(user_id);")
                cursor.execute("CREATE INDEX idx_conversations_status ON conversations(status);")
                cursor.execute("CREATE INDEX idx_messages_conversation_id ON conversation_messages(conversation_id);")
                cursor.execute("CREATE INDEX idx_messages_timestamp ON conversation_messages(timestamp DESC);")
                cursor.execute("CREATE INDEX idx_preferences_user_id ON user_preferences(user_id);")
                cursor.execute("CREATE INDEX idx_analytics_conversation_id ON conversation_analytics(conversation_id);")
                cursor.execute("CREATE INDEX idx_analytics_user_id ON conversation_analytics(user_id);")
                cursor.execute("CREATE INDEX idx_analytics_metric ON conversation_analytics(metric_name);")

                logger.info("Conversation tables created successfully")
            else:
                logger.info("Conversation tables already exist")

        # Ensure enhanced tables exist (always try to create)
        with get_connection() as cursor:
            # Selenium tests table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS selenium_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    url TEXT NOT NULL,
                    load_time REAL NOT NULL,
                    passed BOOLEAN NOT NULL,
                    screenshot_size INTEGER,
                    total_time REAL,
                    notes TEXT
                );
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_selenium_timestamp ON selenium_tests(timestamp DESC);")

            # Agent events table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    agent_type TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    status TEXT DEFAULT 'success'
                );
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_timestamp ON agent_events(timestamp DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_type ON agent_events(agent_type);")

            # Conversation tables (NLI)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME,
                    status TEXT DEFAULT 'active',
                    total_messages INTEGER DEFAULT 0,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                );
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    message_id TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'nli',
                    UNIQUE(user_id, preference_key)
                );
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
            """
            )

            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON conversation_messages(timestamp DESC);"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON user_preferences(user_id);")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_analytics_conversation_id ON conversation_analytics(conversation_id);"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON conversation_analytics(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_metric ON conversation_analytics(metric_name);")

        logger.info("Database initialized successfully with enhancements.")
    except Exception as e:
        logger.error(f"Failed to initialize DB: {e}")


# Generic query function (with logging)
def execute_query(sql, params=None, fetch=False, fetchone=False):
    """Execute SQL query with error handling and logging."""
    try:
        with get_connection() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            if fetch:
                return cursor.fetchall()
            elif fetchone:
                return cursor.fetchone()
            else:
                return True  # For INSERT/UPDATE
    except sqlite3.Error as e:
        logger.error(f"SQLite error in query '{sql}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}")
        return None


# Selenium-specific methods
def insert_test_result(url, load_time, passed, screenshot_size=0, total_time=0, notes=""):
    """Log a Selenium test result to the database."""
    sql = """
        INSERT INTO selenium_tests (url, load_time, passed, screenshot_size, total_time, notes)
        VALUES (?, ?, ?, ?, ?, ?);
    """
    params = (url, load_time, passed, screenshot_size, total_time, notes)
    result = execute_query(sql, params)
    if result:
        logger.info(f"Test result logged for {url}: passed={passed}, load_time={load_time}s")
        return cursor.lastrowid  # Return inserted ID
    return None


def get_test_results(limit=10, passed_only=False):
    """Retrieve recent test results."""
    sql = "SELECT * FROM selenium_tests ORDER BY timestamp DESC LIMIT ?"
    params = (limit,)
    if passed_only:
        sql += " WHERE passed = 1"
    return execute_query(sql, params, fetch=True)

    def get_test_stats():
        """Get summary stats for Selenium tests."""
        sql_total = (
            "SELECT COUNT(*) as total, AVG(load_time) as avg_load, "
            "SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) as passed "
            "FROM selenium_tests;"
        )
        stats = execute_query(sql_total, fetchone=True)
        return dict(stats) if stats else {}


# Conversation and NLI methods
def create_conversation(conversation_id: str, user_id: str, metadata: dict = None) -> bool:
    """Create a new conversation record."""
    metadata_json = json.dumps(metadata) if metadata else "{}"
    sql = """
        INSERT INTO conversations (conversation_id, user_id, metadata)
        VALUES (?, ?, ?);
    """
    params = (conversation_id, user_id, metadata_json)
    result = execute_query(sql, params)
    return result is not None


def save_conversation_message(
    conversation_id: str, message_id: str, role: str, content: str, metadata: dict = None
) -> bool:
    """Save a conversation message."""
    metadata_json = json.dumps(metadata) if metadata else "{}"
    sql = """
        INSERT INTO conversation_messages (conversation_id, message_id, role, content, metadata)
        VALUES (?, ?, ?, ?, ?);
    """
    params = (conversation_id, message_id, role, content, metadata_json)
    result = execute_query(sql, params)
    if result:
        # Update conversation last_activity and message count
        update_sql = """
            UPDATE conversations
            SET total_messages = total_messages + 1, last_activity = CURRENT_TIMESTAMP
            WHERE conversation_id = ?;
        """
        execute_query(update_sql, (conversation_id,))
    return result is not None


def get_conversation_history(conversation_id: str, limit: int = 50) -> list:
    """Get conversation message history."""
    sql = """
        SELECT message_id, role, content, timestamp, metadata
        FROM conversation_messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
        LIMIT ?;
    """
    messages = execute_query(sql, (conversation_id, limit), fetch=True)
    return [dict(msg) for msg in messages] if messages else []


def get_user_conversations(user_id: str, status: str = "active", limit: int = 10) -> list:
    """Get user's conversations."""
    sql = """
        SELECT conversation_id, start_time, total_messages, last_activity, metadata
        FROM conversations
        WHERE user_id = ? AND status = ?
        ORDER BY last_activity DESC
        LIMIT ?;
    """
    conversations = execute_query(sql, (user_id, status, limit), fetch=True)
    return [dict(conv) for conv in conversations] if conversations else []


def update_conversation_status(conversation_id: str, status: str) -> bool:
    """Update conversation status."""
    sql = """
        UPDATE conversations
        SET status = ?, end_time = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE end_time END
        WHERE conversation_id = ?;
    """
    params = (status, status, conversation_id)
    result = execute_query(sql, params)
    return result is not None


def save_user_preference(user_id: str, key: str, value: str, confidence: float = 1.0, source: str = "nli") -> bool:
    """Save or update user preference."""
    sql = """
        INSERT INTO user_preferences (user_id, preference_key, preference_value, confidence, source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, preference_key) DO UPDATE SET
            preference_value = excluded.preference_value,
            confidence = excluded.confidence,
            source = excluded.source,
            last_updated = CURRENT_TIMESTAMP;
    """
    params = (user_id, key, value, confidence, source)
    result = execute_query(sql, params)
    return result is not None


def get_user_preferences(user_id: str) -> dict:
    """Get all user preferences."""
    sql = "SELECT preference_key, preference_value, confidence FROM user_preferences WHERE user_id = ?;"
    prefs = execute_query(sql, (user_id,), fetch=True)
    return (
        {
            pref["preference_key"]: {"value": pref["preference_value"], "confidence": pref["confidence"]}
            for pref in prefs
        }
        if prefs
        else {}
    )


def save_conversation_analytics(
    conversation_id: str, user_id: str, metric_name: str, metric_value: float, metadata: dict = None
) -> bool:
    """Save conversation analytics."""
    metadata_json = json.dumps(metadata) if metadata else "{}"
    sql = """
        INSERT INTO conversation_analytics (conversation_id, user_id, metric_name, metric_value, metadata)
        VALUES (?, ?, ?, ?, ?);
    """
    params = (conversation_id, user_id, metric_name, metric_value, metadata_json)
    result = execute_query(sql, params)
    return result is not None


def get_conversation_analytics(
    conversation_id: str = None, user_id: str = None, metric_name: str = None, limit: int = 100
) -> list:
    """Get conversation analytics with optional filters."""
    conditions = []
    params = []

    if conversation_id:
        conditions.append("conversation_id = ?")
        params.append(conversation_id)
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    if metric_name:
        conditions.append("metric_name = ?")
        params.append(metric_name)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT conversation_id, user_id, metric_name, metric_value, timestamp, metadata
        FROM conversation_analytics
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ?;
    """
    params.append(limit)

    analytics = execute_query(sql, params, fetch=True)
    return [dict(analytic) for analytic in analytics] if analytics else []


def cleanup_old_conversations(days_old: int = 30) -> int:
    """Archive conversations older than specified days."""
    sql = """
        UPDATE conversations
        SET status = 'archived'
        WHERE status = 'active' AND last_activity < datetime('now', '-{} days');
    """.format(
        days_old
    )
    result = execute_query(sql)
    return result if isinstance(result, int) else 0


# Agent events methods
def log_agent_event(agent_type, event_type, payload=None, status="success"):
    """Log an agent event (e.g., from Redis message)."""
    payload_json = json.dumps(payload) if payload else "{}"
    sql = """
        INSERT INTO agent_events (agent_type, event_type, payload, status)
        VALUES (?, ?, ?, ?);
    """
    params = (agent_type, event_type, payload_json, status)
    result = execute_query(sql, params)
    if result:
        logger.info(f"Agent event logged: {agent_type} - {event_type}")
        return True
    return False


def get_agent_events(agent_type=None, limit=20):
    """Retrieve recent agent events."""
    sql = "SELECT * FROM agent_events ORDER BY timestamp DESC LIMIT ?"
    params = (limit,)
    if agent_type:
        sql = "SELECT * FROM agent_events WHERE agent_type = ? ORDER BY timestamp DESC LIMIT ?"
        params = (agent_type, limit)
    events = execute_query(sql, params, fetch=True)
    return [dict(event) for event in events] if events else []


# Example usage and init
if __name__ == "__main__":
    init_db()

    # Test Selenium insert
    test_id = insert_test_result("https://google.com", 1.23, True, 192000, 2.45, "All good")
    print(f"Inserted test ID: {test_id}")

    # Test agent event
    log_agent_event("selenium_agent", "browser_ready", {"status": "initialized"})

    # Test queries
    results = get_test_results(5)
    print(f"Recent tests: {len(results)}")
    events = get_agent_events("selenium_agent", 5)
    print(f"Recent events: {len(events)}")

    stats = get_test_stats()
    print(f"Test stats: {stats}")
