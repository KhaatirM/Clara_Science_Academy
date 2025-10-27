"""
Migration script to add voided fields to Grade and GroupGrade models in production (PostgreSQL).
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def add_voided_fields():
    """Add voided fields to Grade and GroupGrade tables in production."""
    # Get production database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    try:
        # Parse the database URL
        # Format: postgresql://user:password@host:port/dbname
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Connected to production database")
        
        # Add voided fields to grade table
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN is_voided BOOLEAN DEFAULT FALSE")
            print("✓ Added 'is_voided' field to Grade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'is_voided' field already exists in Grade table")
        
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN voided_by INTEGER")
            print("✓ Added 'voided_by' field to Grade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'voided_by' field already exists in Grade table")
        
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN voided_at TIMESTAMP")
            print("✓ Added 'voided_at' field to Grade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'voided_at' field already exists in Grade table")
        
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN voided_reason TEXT")
            print("✓ Added 'voided_reason' field to Grade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'voided_reason' field already exists in Grade table")
        
        # Add voided fields to group_grade table
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN is_voided BOOLEAN DEFAULT FALSE")
            print("✓ Added 'is_voided' field to GroupGrade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'is_voided' field already exists in GroupGrade table")
        
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN voided_by INTEGER")
            print("✓ Added 'voided_by' field to GroupGrade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'voided_by' field already exists in GroupGrade table")
        
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN voided_at TIMESTAMP")
            print("✓ Added 'voided_at' field to GroupGrade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'voided_at' field already exists in GroupGrade table")
        
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN voided_reason TEXT")
            print("✓ Added 'voided_reason' field to GroupGrade table")
        except psycopg2.errors.DuplicateColumn:
            print("✓ 'voided_reason' field already exists in GroupGrade table")
        
        print("\n✅ Successfully added all voided fields to production database!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    add_voided_fields()

