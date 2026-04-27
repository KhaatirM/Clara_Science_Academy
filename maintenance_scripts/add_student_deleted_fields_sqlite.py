"""
SQLite migration: add soft-delete fields to student table.

Adds:
- student.is_deleted (BOOLEAN, default 0)
- student.deleted_at (DATETIME)
- student.marked_for_removal (BOOLEAN, default 0)
- student.removal_note (TEXT)
- student.status_updated_at (DATETIME)
"""

import os
import sqlite3


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def migrate(db_path):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        print(f"[INFO] Using SQLite DB: {db_path}")

        if not _column_exists(cur, "student", "is_deleted"):
            cur.execute("ALTER TABLE student ADD COLUMN is_deleted BOOLEAN DEFAULT 0 NOT NULL")
            print("[OK] Added student.is_deleted")
        else:
            print("[SKIP] student.is_deleted exists")

        if not _column_exists(cur, "student", "deleted_at"):
            cur.execute("ALTER TABLE student ADD COLUMN deleted_at DATETIME")
            print("[OK] Added student.deleted_at")
        else:
            print("[SKIP] student.deleted_at exists")

        if not _column_exists(cur, "student", "marked_for_removal"):
            cur.execute("ALTER TABLE student ADD COLUMN marked_for_removal BOOLEAN DEFAULT 0 NOT NULL")
            print("[OK] Added student.marked_for_removal")
        else:
            print("[SKIP] student.marked_for_removal exists")

        if not _column_exists(cur, "student", "removal_note"):
            cur.execute("ALTER TABLE student ADD COLUMN removal_note TEXT")
            print("[OK] Added student.removal_note")
        else:
            print("[SKIP] student.removal_note exists")

        if not _column_exists(cur, "student", "status_updated_at"):
            cur.execute("ALTER TABLE student ADD COLUMN status_updated_at DATETIME")
            print("[OK] Added student.status_updated_at")
        else:
            print("[SKIP] student.status_updated_at exists")

        conn.commit()
        print("[DONE] Migration complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    # Default dev path used by this repo
    default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "app.db")
    migrate(os.environ.get("SQLITE_DB_PATH", default_path))

