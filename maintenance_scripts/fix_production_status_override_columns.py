"""
Production-safe migration to add status_override and status_override_until columns
to assignment and group_assignment tables.

These columns support temporary status overrides (e.g. "Active until date X") that revert
to automatic status when the override period ends.
"""

import os
import sys

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("ERROR: psycopg2 not installed. This script requires psycopg2 for PostgreSQL connections.")
    sys.exit(1)


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name = %s
        )
    """, (table_name, column_name))
    return cursor.fetchone()[0]


def migrate_database():
    """Add status_override and status_override_until columns to assignment and group_assignment if they don't exist."""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        print("   This script must be run in an environment with DATABASE_URL set")
        return False

    # Fix postgres:// to postgresql:// if needed (psycopg2 requires postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    try:
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("✓ Connected to production database")
        print(f"   Database: {database_url.split('/')[-1]}\n")

        tables = [
            ('assignment', 'individual assignments'),
            ('group_assignment', 'group assignments'),
        ]

        for table_name, label in tables:
            print(f"Migrating {table_name} table ({label})...")

            # Add status_override column
            if not check_column_exists(cursor, table_name, 'status_override'):
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN status_override VARCHAR(20)
                    """)
                    print(f"  ✓ Added '{table_name}.status_override' column")
                except psycopg2.Error as e:
                    print(f"  ✗ Error adding '{table_name}.status_override': {e}")
                    cursor.close()
                    conn.close()
                    return False
            else:
                print(f"  → Column '{table_name}.status_override' already exists")

            # Add status_override_until column
            if not check_column_exists(cursor, table_name, 'status_override_until'):
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN status_override_until TIMESTAMP
                    """)
                    print(f"  ✓ Added '{table_name}.status_override_until' column")
                except psycopg2.Error as e:
                    print(f"  ✗ Error adding '{table_name}.status_override_until': {e}")
                    cursor.close()
                    conn.close()
                    return False
            else:
                print(f"  → Column '{table_name}.status_override_until' already exists")

            print()

        cursor.close()
        conn.close()

        print("✅ Migration completed successfully!")
        return True

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
