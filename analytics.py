#!/usr/bin/env python3
"""
Simple Analytics Tracker for Grokputer
Tracks API calls, agent iterations, success rates, and performance metrics.
Uses SQLite for persistence (integrates with existing db/).
"""

import sqlite3
import json
import time
import os
from datetime import datetime
from typing import Dict, Any

DB_PATH = './db/metrics.db'  # Separate DB for metrics to avoid conflicts

def init_db():
    """Initialize metrics database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            task TEXT,
            provider TEXT,
            model TEXT,
            iterations INTEGER,
            api_calls INTEGER DEFAULT 0,
            success BOOLEAN,
            duration REAL,
            notes TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT,
            endpoint TEXT,
            response_time REAL,
            status_code INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    conn.commit()
    conn.close()

def start_session(task: str, provider: str = 'grok', model: str = 'default') -> int:
    """Start a new session and return session ID."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO sessions (start_time, task, provider, model) VALUES (?, ?, ?, ?)',
        (datetime.now().isoformat(), task, provider, model)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def log_api_call(session_id: int, endpoint: str, response_time: float, status_code: int = 200):
    """Log an API call."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO api_calls (session_id, timestamp, endpoint, response_time, status_code) VALUES (?, ?, ?, ?, ?)',
        (session_id, datetime.now().isoformat(), endpoint, response_time, status_code)
    )
    conn.commit()
    conn.close()

def end_session(session_id: int, iterations: int, success: bool, duration: float, notes: str = ''):
    """End session and update metrics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Count API calls for this session
    cursor.execute('SELECT COUNT(*) FROM api_calls WHERE session_id = ?', (session_id,))
    api_calls = cursor.fetchone()[0]
    
    cursor.execute(
        'UPDATE sessions SET end_time = ?, iterations = ?, api_calls = ?, success = ?, duration = ?, notes = ? WHERE id = ?',
        (datetime.now().isoformat(), iterations, api_calls, success, duration, notes, session_id)
    )
    conn.commit()
    conn.close()

def generate_report(days: int = 7) -> Dict[str, Any]:
    """Generate analytics report for last N days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Total sessions
    cursor.execute('SELECT COUNT(*) FROM sessions WHERE start_time > ?', (cutoff,))
    total_sessions = cursor.fetchone()[0]
    
    # Success rate
    cursor.execute('SELECT COUNT(*) FROM sessions WHERE success = 1 AND start_time > ?', (cutoff,))
    successful = cursor.fetchone()[0]
    success_rate = (successful / total_sessions * 100) if total_sessions > 0 else 0
    
    # Avg duration
    cursor.execute('SELECT AVG(duration) FROM sessions WHERE start_time > ?', (cutoff,))
    avg_duration = cursor.fetchone()[0] or 0
    
    # Total API calls
    cursor.execute('SELECT SUM(api_calls) FROM sessions WHERE start_time > ?', (cutoff,))
    total_api_calls = cursor.fetchone()[0] or 0
    
    # Provider breakdown
    cursor.execute('SELECT provider, COUNT(*) as count, AVG(api_calls) as avg_calls FROM sessions WHERE start_time > ? GROUP BY provider', (cutoff,))
    providers = {row[0]: {'sessions': row[1], 'avg_api_calls': row[2] or 0} for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        'period_days': days,
        'total_sessions': total_sessions,
        'success_rate_percent': round(success_rate, 2),
        'avg_duration_seconds': round(avg_duration, 2),
        'total_api_calls': total_api_calls,
        'providers': providers,
        'generated_at': datetime.now().isoformat()
    }

if __name__ == '__main__':
    # Example usage
    from datetime import timedelta  # Fix import for timedelta
    print("Grokputer Analytics Initialized")
    print(json.dumps(generate_report(30), indent=2))