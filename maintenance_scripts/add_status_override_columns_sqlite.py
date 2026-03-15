#!/usr/bin/env python3
"""
Add status_override and status_override_until columns to assignment and group_assignment
for local SQLite development. Run this if the app startup migration didn't run.
"""

import os
import sys
import sqlite3

# Project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Common SQLite DB paths
DB_PATHS = [
    os.path.join(project_root, 'instance', 'app.db'),
    os.path.join(project_root, 'instance', 'school_management.db'),
]


def add_columns(db_path):
    """Add status_override columns to assignment and group_assignment tables."""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        for table_name in ('assignment', 'group_assignment'):
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            if 'status_override' not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN status_override VARCHAR(20)")
                print(f"  Added {table_name}.status_override")
            if 'status_override_until' not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN status_override_until TIMESTAMP")
                print(f"  Added {table_name}.status_override_until")
        conn.commit()
        print("Done.")
        return True
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    for path in DB_PATHS:
        if os.path.exists(path):
            print(f"Updating {path}...")
            add_columns(path)
            break
    else:
        print("No SQLite database found.")
        sys.exit(1)
