"""
Production Migration Script: Add voided fields to Grade and GroupGrade tables.

This script should be run on Render to add the missing database columns:
- grade.is_voided, grade.voided_by, grade.voided_at, grade.voided_reason
- group_grade.is_voided, group_grade.voided_by, group_grade.voided_at, group_grade.voided_reason

Usage on Render:
1. SSH into your Render service
2. Run: python migrate_voided_fields_production.py

Or run directly as a one-time script.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name = %s
        );
    """
    cursor.execute(query, (table_name, column_name))
    return cursor.fetchone()[0]

def migrate_database():
    """Add voided fields to Grade and GroupGrade tables if they don't exist."""
    # Get production database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        print("   This script must be run in an environment with DATABASE_URL set")
        return False
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✓ Connected to production database")
        print(f"   Database: {os.getenv('DATABASE_URL').split('/')[-1]}\n")
        
        # Migration for Grade table
        print("Migrating Grade table...")
        grade_fields = [
            ('is_voided', 'BOOLEAN DEFAULT FALSE'),
            ('voided_by', 'INTEGER'),
            ('voided_at', 'TIMESTAMP'),
            ('voided_reason', 'TEXT')
        ]
        
        for field_name, field_type in grade_fields:
            if not check_column_exists(cursor, 'grade', field_name):
                try:
                    query = sql.SQL("ALTER TABLE grade ADD COLUMN {} {}").format(
                        sql.Identifier(field_name),
                        sql.SQL(field_type)
                    )
                    cursor.execute(query)
                    print(f"  ✓ Added 'grade.{field_name}' column")
                except psycopg2.Error as e:
                    print(f"  ✗ Error adding 'grade.{field_name}': {e}")
            else:
                print(f"  → Column 'grade.{field_name}' already exists")
        
        # Migration for GroupGrade table
        print("\nMigrating GroupGrade table...")
        for field_name, field_type in grade_fields:
            if not check_column_exists(cursor, 'group_grade', field_name):
                try:
                    query = sql.SQL("ALTER TABLE group_grade ADD COLUMN {} {}").format(
                        sql.Identifier(field_name),
                        sql.SQL(field_type)
                    )
                    cursor.execute(query)
                    print(f"  ✓ Added 'group_grade.{field_name}' column")
                except psycopg2.Error as e:
                    print(f"  ✗ Error adding 'group_grade.{field_name}': {e}")
            else:
                print(f"  → Column 'group_grade.{field_name}' already exists")
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("  Database Migration: Adding Voided Fields")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    if success:
        print("✅ Migration successful! Your database is now up to date.")
        sys.exit(0)
    else:
        print("❌ Migration failed! Please check the errors above.")
        sys.exit(1)

