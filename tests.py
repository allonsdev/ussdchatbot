import sqlite3

DB = "support.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
SELECT agent_id, full_name, role, password, created_at
FROM agents
""")

for row in c.fetchall():
    print(f"Agent ID : {row['agent_id']}")
    print(f"Name     : {row['full_name']}")
    print(f"Role     : {row['role']}")
    print(f"Password : {row['password']}")
    print(f"Created  : {row['created_at']}")
    print("-" * 40)

conn.close()