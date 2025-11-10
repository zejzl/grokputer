import sqlite3
from pathlib import Path

DB_PATH = Path.cwd() / "db" / "db.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM dnd_characters ORDER BY agent_name;")
rows = cursor.fetchall()

print("D&D Stats in Database:")
for row in rows:
    print(row)

conn.close()