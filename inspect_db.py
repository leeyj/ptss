import sqlite3

conn = sqlite3.connect("ptss.db")
cursor = conn.cursor()

# Get the schema of 'history' table
cursor.execute("PRAGMA table_info(history)")
columns = cursor.fetchall()

print("Schema of 'history' table:")
for col in columns:
    # col[1] is name, col[3] is notnull (1 for NOT NULL, 0 for NULL)
    name = col[1]
    notnull = col[3]
    print(f"Column: {name}, NotNull: {notnull}")

conn.close()
