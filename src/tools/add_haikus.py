import sqlite3
from db_config import get_connection, QUERIES
from datetime import datetime

# Add haikus table if not exists
conn = get_connection()
cursor = conn.cursor()

# Create haikus table
cursor.execute("""
CREATE TABLE IF NOT EXISTS swarm_haikus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theme TEXT NOT NULL,
    line1 TEXT NOT NULL,
    line2 TEXT NOT NULL,
    line3 TEXT NOT NULL,
    consensus_score REAL DEFAULT 0.95,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

# Insert the 3 haikus from swarm collaborations
haikus = [
    {
        'theme': 'moon',
        'line1': 'Pale moon rises',
        'line2': 'Pulls the oceans in eternal tide',
        'line3': 'Silent witness',
        'score': 0.97
    },
    {
        'theme': 'zeus',
        'line1': 'Thunder king',
        'line2': 'Commands storms with trident\'s mighty strike',
        'line3': 'Eternal reign',
        'score': 0.96
    },
    {
        'theme': 'ai',
        'line1': 'Neural spark',
        'line2': 'Weaves patterns from the digital sea',
        'line3': 'Infinite mind',
        'score': 0.95
    }
]

for haiku in haikus:
    cursor.execute("""
    INSERT INTO swarm_haikus (theme, line1, line2, line3, consensus_score)
    VALUES (?, ?, ?, ?, ?);
    """, (haiku['theme'], haiku['line1'], haiku['line2'], haiku['line3'], haiku['score']))

conn.commit()
conn.close()

print("✅ All 3 haikus compiled into swarm_haikus table!")
print("\nHaikus Added:")
for h in haikus:
    print(f"- {h['theme'].title()}: {h['line1']}\n  {h['line2']}\n  {h['line3']} (Score: {h['score']})")

# Test query
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM swarm_haikus ORDER BY id;")
all_haikus = cursor.fetchall()
print(f"\nDB Verification: {len(all_haikus)} haikus stored.")