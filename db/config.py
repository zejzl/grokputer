import sqlite3
import os

DB_PATH = 'db.db'
SQL_SCRIPT = 'db.sql'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict-like rows
    return conn

SCHEMA = """
CREATE TABLE IF NOT EXISTS swarm_rolls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    roll_number INTEGER NOT NULL,
    notation TEXT NOT NULL,
    individual_rolls TEXT NOT NULL,  -- JSON-like string: '[3,5]'
    total INTEGER NOT NULL,
    modifier INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_name ON swarm_rolls(agent_name);
CREATE INDEX IF NOT EXISTS idx_total ON swarm_rolls(total);
"""

QUERIES = {
    "all_rolls": "SELECT * FROM swarm_rolls",
    "top_rolls": "SELECT * FROM swarm_rolls ORDER BY total DESC LIMIT ?",
    "insert_roll": "INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES (?, ?, ?, ?, ?, ?)",
    "avg_per_agent": "SELECT agent_name, AVG(total) as avg_total FROM swarm_rolls GROUP BY agent_name",
    "rolls_by_agent": "SELECT * FROM swarm_rolls WHERE agent_name = ?",
}

def init_db():
    if not os.path.exists(DB_PATH):
        # Execute the SQL script to create and populate the DB
        with open(SQL_SCRIPT, 'r') as f:
            sql_script = f.read()
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(sql_script)
        conn.commit()
        conn.close()
        print(f"Database created and initialized from {SQL_SCRIPT}: {DB_PATH}")
    else:
        # Ensure schema is up to date
        conn = get_connection()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        print(f"Database initialized: {DB_PATH}")

if __name__ == "__main__":
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM swarm_rolls")
    result = cursor.fetchone()
    print(f"Total rolls in DB: {result['count']}")
    conn.close()