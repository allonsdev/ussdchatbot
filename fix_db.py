import sqlite3

db_file = "issues.db"   # adjust if your DB file has a different name

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Try to add agent_id column if it doesn't exist
try:
    cursor.execute("ALTER TABLE issues ADD COLUMN agent_id TEXT")
    print("agent_id column added successfully.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("agent_id column already exists.")
    else:
        print("Error:", e)

conn.commit()
conn.close()
