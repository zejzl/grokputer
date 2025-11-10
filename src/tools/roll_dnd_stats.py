import sqlite3
import random
from pathlib import Path
from collections import defaultdict

DB_PATH = Path.cwd() / "db" / "db.db"

# List of agents from DB
agents = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack', 'Kara', 'Leo']

stats_order = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

def roll_stat():
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort()
    return sum(rolls[1:])  # drop lowest

def roll_character_stats():
    return {stat: roll_stat() for stat in stats_order}

# Roll for each agent
dnd_stats = {}
for agent in agents:
    dnd_stats[agent] = roll_character_stats()
    print(f"{agent}: {dnd_stats[agent]}")

# Now, to store in DB, create table if not exists
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS dnd_characters (
    agent_name TEXT PRIMARY KEY,
    STR INTEGER,
    DEX INTEGER,
    CON INTEGER,
    INT_ INTEGER,  -- INT is keyword
    WIS INTEGER,
    CHA INTEGER,
    FOREIGN KEY (agent_name) REFERENCES swarm_rolls (agent_name)
)
""")

# Insert or update stats
for agent, stats in dnd_stats.items():
    cursor.execute("""
    INSERT OR REPLACE INTO dnd_characters (agent_name, STR, DEX, CON, INT_, WIS, CHA)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (agent, stats['STR'], stats['DEX'], stats['CON'], stats['INT'], stats['WIS'], stats['CHA']))

conn.commit()
conn.close()

print("\nStats rolled and inserted into database.")