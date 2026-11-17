import sqlite3

db_path = r"D:\development\m1m-business-workflow-agent\m1m.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:", tables)

conn.close()
