"""
Make group_grade.graded_by nullable so grades can be saved when no teacher is available
(e.g. School Administrator grading with no TeacherStaff record).

Run once on production (e.g. Render):
  python maintenance_scripts/group_grade_graded_by_nullable.py

PostgreSQL: ALTER TABLE group_grade ALTER COLUMN graded_by DROP NOT NULL;
"""

import os
import sys

def migrate_postgres():
    import psycopg2
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set; skipping PostgreSQL migration.")
        return False
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'group_grade' AND column_name = 'graded_by'
    """)
    row = cur.fetchone()
    if not row:
        print("Column group_grade.graded_by not found.")
        cur.close()
        conn.close()
        return False
    if row[0] == 'YES':
        print("group_grade.graded_by is already nullable.")
        cur.close()
        conn.close()
        return True
    cur.execute("ALTER TABLE group_grade ALTER COLUMN graded_by DROP NOT NULL")
    print("Made group_grade.graded_by nullable.")
    cur.close()
    conn.close()
    return True

def migrate_sqlite():
    # SQLite does not support ALTER COLUMN; would require table recreate. Skip for local dev.
    print("SQLite: run Flask app with updated model; new DBs get nullable column.")
    return True

if __name__ == '__main__':
    if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL', '').lower():
        ok = migrate_postgres()
    else:
        ok = migrate_sqlite()
    sys.exit(0 if ok else 1)
