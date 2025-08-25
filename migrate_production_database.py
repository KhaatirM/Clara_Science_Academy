#!/usr/bin/env python3
"""Migration script to add missing columns to production PostgreSQL database"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def migrate_production_database():
    """Add missing columns to production database"""
    
    # Get database connection details from environment variables
    # These should be set in your Render environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not found!")
        print("Please ensure DATABASE_URL is set in your Render environment variables.")
        return False
    
    try:
        # Parse the DATABASE_URL
        # Format: postgresql://username:password@host:port/database
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgres://')
        
        # Connect to the database
        print("🔌 Connecting to production database...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        
        # Check current table structure
        print("\n📋 Checking current table structure...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'teacher_staff' 
            ORDER BY ordinal_position
        """)
        
        existing_columns = {row[0] for row in cursor.fetchall()}
        print(f"Current columns: {sorted(existing_columns)}")
        
        # Define the new columns to add
        new_columns = [
            ('middle_initial', 'VARCHAR(1)'),
            ('dob', 'VARCHAR(20)'),
            ('staff_ssn', 'VARCHAR(20)'),
            ('assigned_role', 'VARCHAR(100)'),
            ('subject', 'VARCHAR(200)'),
            ('employment_type', 'VARCHAR(20)'),
            ('grades_taught', 'TEXT'),
            ('resume_filename', 'VARCHAR(255)'),
            ('other_document_filename', 'VARCHAR(255)'),
            ('image', 'VARCHAR(255)')
        ]
        
        # Add missing columns
        print("\n🔧 Adding missing columns...")
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    print(f"  Adding column: {col_name} ({col_type})")
                    cursor.execute(f"ALTER TABLE teacher_staff ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ Added {col_name}")
                except Exception as e:
                    print(f"  ❌ Error adding {col_name}: {e}")
            else:
                print(f"  ⏭️  Column {col_name} already exists")
        
        # Verify the final structure
        print("\n📋 Verifying final table structure...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'teacher_staff' 
            ORDER BY ordinal_position
        """)
        
        final_columns = {row[0] for row in cursor.fetchall()}
        print(f"Final columns: {sorted(final_columns)}")
        
        # Check if all required columns are present
        required_columns = {col[0] for col in new_columns}
        missing_columns = required_columns - final_columns
        
        if missing_columns:
            print(f"\n❌ Missing columns: {missing_columns}")
            return False
        else:
            print("\n✅ All required columns are present!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting production database migration...")
    success = migrate_production_database()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("The teacher dashboard should now work properly.")
    else:
        print("\n💥 Migration failed!")
        print("Please check the error messages above and try again.")
