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
from pathlib import Path
from contextlib import contextmanager
import sqlite3
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        # Run the main schema
        with open(DB_SQL_PATH, 'r') as f:
            sql_script = f.read()
        
        with get_connection() as cursor:
            cursor.executescript(sql_script)
        
        # Ensure enhanced tables exist
        with get_connection() as cursor:
            cursor.execute("""
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
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_selenium_timestamp ON selenium_tests(timestamp DESC);")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    agent_type TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    status TEXT DEFAULT 'success'
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_timestamp ON agent_events(timestamp DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_type ON agent_events(agent_type);")
        
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
    sql_total = "SELECT COUNT(*) as total, AVG(load_time) as avg_load, SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) as passed FROM selenium_tests;"
    stats = execute_query(sql_total, fetchone=True)
    return dict(stats) if stats else {}

# Agent events methods
def log_agent_event(agent_type, event_type, payload=None, status='success'):
    """Log an agent event (e.g., from Redis message)."""
    payload_json = json.dumps(payload) if payload else '{}'
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