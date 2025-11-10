import sqlite3
from db_config import get_connection

conn = get_connection()
cursor = conn.cursor()

query = """
SELECT DISTINCT agent_name 
FROM swarm_rolls 
ORDER BY agent_name;
"""

cursor.execute(query)
agents = cursor.fetchall()

print("All unique agents/users:")
for (agent,) in agents:
    print(agent)

conn.close()