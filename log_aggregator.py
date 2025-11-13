#!/usr/bin/env python3
"""
Log Aggregator for Grokputer - ELK Stack Simulation
Uses file watchers (watchdog) to monitor log files, parse structured JSON logs,
and aggregate into a central SQLite database for querying and analysis.
Simulates ELK: File watcher (Logstash-like), SQLite (Elasticsearch-like), 
and integrates with Streamlit dashboard for Kibana-like visualization.
"""

import sqlite3
import json
import os
import time
from datetime import datetime
from typing import Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# Setup basic logging for aggregator
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = './db/logs_aggregated.db'
LOG_DIR = './logs'  # Watch this directory
WATCHED_FILES = ['grokputer_structured.log']  # JSON structured logs

def init_aggregated_db():
    """Initialize aggregated logs database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aggregated_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            logger TEXT,
            message TEXT,
            module TEXT,
            function TEXT,
            line INTEGER,
            extra TEXT,  -- JSON extra data
            session_id TEXT  -- Optional link to analytics
        )
    ''')
    # Index for fast queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON aggregated_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_level ON aggregated_logs(level)')
    conn.commit()
    conn.close()
    logger.info("Aggregated logs DB initialized")

class LogHandler(FileSystemEventHandler):
    """File watcher handler for log files."""
    def on_modified(self, event):
        if not event.is_directory and any(watched in event.src_path for watched in WATCHED_FILES):
            self._parse_and_aggregate(event.src_path)
    
    def _parse_and_aggregate(self, log_file: str):
        """Parse new log lines and aggregate to DB."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # Read last N lines to avoid full scan (e.g., last 100)
                lines = f.readlines()[-100:]
                for line in lines:
                    if line.strip():
                        try:
                            log_entry = json.loads(line.strip())
                            self._insert_to_db(log_entry)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in log: {line[:100]}")
        except Exception as e:
            logger.error(f"Error parsing log {log_file}: {e}")
    
    def _insert_to_db(self, entry: Dict[str, Any]):
        """Insert parsed log to aggregated DB."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO aggregated_logs 
            (timestamp, level, logger, message, module, function, line, extra, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.get('timestamp'),
            entry.get('level'),
            entry.get('logger'),
            entry.get('message'),
            entry.get('module'),
            entry.get('function'),
            entry.get('line'),
            json.dumps(entry.get('extra', {})),
            entry.get('session_id', '')  # Link to analytics if available
        ))
        conn.commit()
        conn.close()
        logger.debug(f"Aggregated log: {entry.get('message', '')[:50]}")

def query_aggregated_logs(query: str = "SELECT * FROM aggregated_logs ORDER BY timestamp DESC LIMIT 50") -> list:
    """Query aggregated logs (Kibana-like)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in results]

def start_aggregation():
    """Start the log watcher."""
    init_aggregated_db()
    event_handler = LogHandler()
    observer = Observer()
    observer.schedule(event_handler, LOG_DIR, recursive=False)
    observer.start()
    logger.info(f"Log aggregation started, watching {LOG_DIR}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def aggregate_existing_logs():
    """One-time aggregation of existing logs."""
    init_aggregated_db()
    for watched in WATCHED_FILES:
        log_path = os.path.join(LOG_DIR, watched)
        if os.path.exists(log_path):
            handler = LogHandler()
            handler._parse_and_aggregate(log_path)
    logger.info("Existing logs aggregated")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--aggregate-existing':
        aggregate_existing_logs()
        print("Existing logs aggregated. Run without args for continuous watching.")
    else:
        start_aggregation()