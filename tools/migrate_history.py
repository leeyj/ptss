import sqlite3


def migrate_history_table():
    db_path = "ptss.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Check current schema
        print("Checking current schema...")
        cursor.execute("PRAGMA table_info(history)")
        columns = cursor.fetchall()

        # 2. Rename old table
        print("Renaming old table to history_backup...")
        cursor.execute("ALTER TABLE history RENAME TO history_backup")

        # 3. Create new table with correct schema (host_id nullable)
        # Note: In SQLite, INTEGER PRIMARY KEY is auto-incrementing by default if not specified otherwise
        print("Creating new history table...")
        create_table_sql = """
        CREATE TABLE history (
            id INTEGER PRIMARY KEY,
            host_id INTEGER,
            user_id INTEGER,
            action_type VARCHAR(20) NOT NULL,
            detail TEXT NOT NULL,
            extra_info TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(host_id) REFERENCES host(id),
            FOREIGN KEY(user_id) REFERENCES user(id)
        );
        """
        cursor.execute(create_table_sql)

        # 4. Copy data
        print("Copying data...")
        # Get column names from backup to map correctly
        cursor.execute("PRAGMA table_info(history_backup)")
        old_cols = [col[1] for col in cursor.fetchall()]
        col_list = ", ".join(old_cols)

        insert_sql = (
            f"INSERT INTO history ({col_list}) SELECT {col_list} FROM history_backup"
        )
        cursor.execute(insert_sql)

        # 5. Drop old table
        print("Dropping backup table...")
        cursor.execute("DROP TABLE history_backup")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        # Attempt to restore if possible?
        # If renamed but new table creation failed, we might be in weird state.
        # But transaction rollback should handle most DML. DDL in SQLite is transactional.
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_history_table()
