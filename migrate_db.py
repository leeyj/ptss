import sqlite3
import os

db_path = "ptss.db"
if not os.path.exists(db_path):
    print("Database does not exist yet. It will be created on app start.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [c[1] for c in cursor.fetchall()]
        if "role" not in columns:
            cursor.execute(
                "ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'"
            )
            cursor.execute("UPDATE user SET role='admin' WHERE username='admin'")
            conn.commit()
            print("Successfully added 'role' column.")
        else:
            print("'role' column already exists.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()
