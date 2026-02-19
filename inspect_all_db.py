import sqlite3

conn = sqlite3.connect("ptss.db")
cursor = conn.cursor()

tables = ["user", "host", "history", "config", "script", "snippet"]

for table in tables:
    print(f"\n--- Schema of '{table}' table ---")
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, PK: {col[5]}")
    except Exception as e:
        print(f"Error reading table {table}: {e}")

conn.close()
