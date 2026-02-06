"""
One-off production database fixes (add missing columns).
Prefer Flask-Migrate for schema changes; run this only when explicitly needed.
Usage: set RUN_PRODUCTION_DB_FIX=1 to run on app startup, or call from a script.
"""

import os


def run_production_database_fix():
    """
    Add missing columns to production (PostgreSQL) database.
    Only runs when DATABASE_URL is set and points to PostgreSQL.
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("No DATABASE_URL found, skipping production database fix")
        return

    if 'postgres' not in database_url.lower() and 'postgresql' not in database_url.lower():
        print("Not a PostgreSQL database, skipping production database fix")
        return

    print("Running production database fix...")
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgres://')

        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Assignment table
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'assignment'
            AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes', 'created_by', 'open_date', 'close_date')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        columns_to_add = []
        if 'allow_save_and_continue' not in existing_columns:
            columns_to_add.append("allow_save_and_continue BOOLEAN DEFAULT FALSE")
        if 'max_save_attempts' not in existing_columns:
            columns_to_add.append("max_save_attempts INTEGER DEFAULT 3")
        if 'save_timeout_minutes' not in existing_columns:
            columns_to_add.append("save_timeout_minutes INTEGER DEFAULT 30")
        if 'created_by' not in existing_columns:
            columns_to_add.append("created_by INTEGER")
        if 'open_date' not in existing_columns:
            columns_to_add.append("open_date TIMESTAMP")
        if 'close_date' not in existing_columns:
            columns_to_add.append("close_date TIMESTAMP")
        for column_def in columns_to_add:
            name = column_def.split()[0]
            print(f"Adding column to assignment: {name}")
            cursor.execute(f"ALTER TABLE assignment ADD COLUMN {column_def}")

        # group_assignment
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'group_assignment'
            AND column_name IN ('created_by', 'open_date', 'close_date')
        """)
        group_existing = [row[0] for row in cursor.fetchall()]
        if 'created_by' not in group_existing:
            cursor.execute("ALTER TABLE group_assignment ADD COLUMN created_by INTEGER")
        if 'open_date' not in group_existing:
            cursor.execute("ALTER TABLE group_assignment ADD COLUMN open_date TIMESTAMP")
        if 'close_date' not in group_existing:
            cursor.execute("ALTER TABLE group_assignment ADD COLUMN close_date TIMESTAMP")

        # class.grade_levels
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'class' AND column_name = 'grade_levels'
        """)
        if not cursor.fetchall():
            cursor.execute("ALTER TABLE class ADD COLUMN grade_levels VARCHAR(200)")

        # teacher_staff
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'teacher_staff'
            AND column_name IN ('is_temporary', 'access_expires_at', 'is_deleted', 'deleted_at')
        """)
        teacher_existing = [row[0] for row in cursor.fetchall()]
        if 'is_temporary' not in teacher_existing:
            cursor.execute("ALTER TABLE teacher_staff ADD COLUMN is_temporary BOOLEAN DEFAULT FALSE NOT NULL")
        if 'access_expires_at' not in teacher_existing:
            cursor.execute("ALTER TABLE teacher_staff ADD COLUMN access_expires_at TIMESTAMP")
        if 'is_deleted' not in teacher_existing:
            cursor.execute("ALTER TABLE teacher_staff ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL")
        if 'deleted_at' not in teacher_existing:
            cursor.execute("ALTER TABLE teacher_staff ADD COLUMN deleted_at TIMESTAMP")

        # group_assignment_extension table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables WHERE table_name = 'group_assignment_extension'
            )
        """)
        if not cursor.fetchone()[0]:
            cursor.execute("""
                CREATE TABLE group_assignment_extension (
                    id SERIAL PRIMARY KEY,
                    group_assignment_id INTEGER NOT NULL REFERENCES group_assignment(id),
                    student_id INTEGER NOT NULL REFERENCES student(id),
                    extended_due_date TIMESTAMP NOT NULL,
                    reason TEXT,
                    granted_by INTEGER NOT NULL REFERENCES teacher_staff(id),
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

        cursor.close()
        conn.close()
        print("Production database fix completed successfully.")
    except ImportError:
        print("psycopg2 not available, skipping database fix")
    except Exception as e:
        print(f"Database fix failed: {e}")
        import traceback
        traceback.print_exc()
