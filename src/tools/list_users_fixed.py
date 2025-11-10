import sqlite3
import os
from pathlib import Path

DB_PATH = Path.cwd() / "db" / "db.db"

if not DB_PATH.exists():
    print(f"DB not found: {DB_PATH}")
else:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    if 'swarm_rolls' in [t[0] for t in tables]:
        cursor.execute("""
        SELECT DISTINCT agent_name 
        FROM swarm_rolls 
        ORDER BY agent_name;
        """)
        agents = cursor.fetchall()
        print("\nAll unique agents/users:")
        for (agent,) in agents:
            print(agent)
    else:
        print("No swarm_rolls table")
    
    conn.close()