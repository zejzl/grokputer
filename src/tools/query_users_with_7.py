import sqlite3
from db_config import get_connection

# Query for unique agents who have a 7 in any individual_rolls
conn = get_connection()
cursor = conn.cursor()

# SQL: Find rows with '7' in individual_rolls string
query = """
SELECT DISTINCT agent_name 
FROM swarm_rolls 
WHERE individual_rolls LIKE '%7%'
ORDER BY agent_name;
"""

cursor.execute(query)
agents_with_7 = cursor.fetchall()

if agents_with_7:
    print("🤖 Agents who rolled a 7 (in any individual die):")
    for (agent,) in agents_with_7:
        # Also fetch their rolls with 7 for context
        cursor.execute("""
            SELECT notation, individual_rolls, total 
            FROM swarm_rolls 
            WHERE agent_name = ? AND individual_rolls LIKE '%7%'
            ORDER BY roll_number;
        """, (agent,))
        rolls = cursor.fetchall()
        print(f"\n  - {agent}:")
        for roll in rolls:
            print(f"    {roll['notation']}: {roll['individual_rolls']} (Total: {roll['total']})")
else:
    print("No agents rolled a 7.")

conn.close()