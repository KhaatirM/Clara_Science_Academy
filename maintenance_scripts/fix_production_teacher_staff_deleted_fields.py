"""
Production-safe migration to add is_deleted and deleted_at columns to teacher_staff table.
This script is designed to run on the live production database (PostgreSQL) without downtime.
"""

import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from psycopg2 import sql
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
    """Add is_deleted and deleted_at columns to teacher_staff table if they don't exist."""
    # Get production database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        print("   This script must be run in an environment with DATABASE_URL set")
        return False
    
    # Fix postgres:// to postgresql:// if needed (psycopg2 requires postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✓ Connected to production database")
        print(f"   Database: {database_url.split('/')[-1]}\n")
        
        # Migration for teacher_staff table
        print("Migrating teacher_staff table...")
        
        # Add is_deleted column
        if not check_column_exists(cursor, 'teacher_staff', 'is_deleted'):
            try:
                cursor.execute("""
                    ALTER TABLE teacher_staff 
                    ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL
                """)
                print("  ✓ Added 'teacher_staff.is_deleted' column")
            except psycopg2.Error as e:
                print(f"  ✗ Error adding 'teacher_staff.is_deleted': {e}")
                return False
        else:
            print("  → Column 'teacher_staff.is_deleted' already exists")
        
        # Add deleted_at column
        if not check_column_exists(cursor, 'teacher_staff', 'deleted_at'):
            try:
                cursor.execute("""
                    ALTER TABLE teacher_staff 
                    ADD COLUMN deleted_at TIMESTAMP
                """)
                print("  ✓ Added 'teacher_staff.deleted_at' column")
            except psycopg2.Error as e:
                print(f"  ✗ Error adding 'teacher_staff.deleted_at': {e}")
                return False
        else:
            print("  → Column 'teacher_staff.deleted_at' already exists")
        
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

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)

