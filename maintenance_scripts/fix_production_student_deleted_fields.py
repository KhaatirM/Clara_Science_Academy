"""
Production-safe migration to add soft-delete / removal-tracking columns to student table.

Why this exists:
- The SQLAlchemy Student model includes these columns (is_deleted, deleted_at, marked_for_removal, removal_note, status_updated_at)
- If production DB is missing them, any Student query will fail with UndefinedColumn.
"""

import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("ERROR: psycopg2 not installed. This script requires psycopg2 for PostgreSQL connections.")
    sys.exit(1)


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name = %s
        )
        """,
        (table_name, column_name),
    )
    return bool(cursor.fetchone()[0])


def migrate_database() -> bool:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        return False

    # psycopg2 accepts postgresql://; Render sometimes provides postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    try:
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("✓ Connected to production database")
        print(f"   Database: {database_url.split('/')[-1]}\n")

        print("Migrating student table (soft-delete fields)...")

        if not check_column_exists(cursor, "student", "is_deleted"):
            cursor.execute(
                """
                ALTER TABLE student
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL
                """
            )
            print("  ✓ Added 'student.is_deleted' column")
        else:
            print("  → Column 'student.is_deleted' already exists")

        if not check_column_exists(cursor, "student", "deleted_at"):
            cursor.execute(
                """
                ALTER TABLE student
                ADD COLUMN deleted_at TIMESTAMP
                """
            )
            print("  ✓ Added 'student.deleted_at' column")
        else:
            print("  → Column 'student.deleted_at' already exists")

        if not check_column_exists(cursor, "student", "marked_for_removal"):
            cursor.execute(
                """
                ALTER TABLE student
                ADD COLUMN marked_for_removal BOOLEAN DEFAULT FALSE NOT NULL
                """
            )
            print("  ✓ Added 'student.marked_for_removal' column")
        else:
            print("  → Column 'student.marked_for_removal' already exists")

        if not check_column_exists(cursor, "student", "removal_note"):
            cursor.execute(
                """
                ALTER TABLE student
                ADD COLUMN removal_note TEXT
                """
            )
            print("  ✓ Added 'student.removal_note' column")
        else:
            print("  → Column 'student.removal_note' already exists")

        if not check_column_exists(cursor, "student", "status_updated_at"):
            cursor.execute(
                """
                ALTER TABLE student
                ADD COLUMN status_updated_at TIMESTAMP
                """
            )
            print("  ✓ Added 'student.status_updated_at' column")
        else:
            print("  → Column 'student.status_updated_at' already exists")

        cursor.close()
        conn.close()
        print("\n✅ Migration completed successfully!")
        return True
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = migrate_database()
    raise SystemExit(0 if ok else 1)

