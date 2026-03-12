import sqlite3

conn = sqlite3.connect("issues.db")
cursor = conn.cursor()

cursor.execute("SELECT id, phone_number, status FROM issues")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
