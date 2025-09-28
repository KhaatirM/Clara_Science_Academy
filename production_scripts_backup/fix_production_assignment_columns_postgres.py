#!/usr/bin/env python3
"""
Fix missing assignment table columns in production PostgreSQL database on Render.
This script adds the missing columns: allow_save_and_continue, max_save_attempts, save_timeout_minutes
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def fix_production_assignment_columns():
    """Add missing columns to the assignment table in production database."""
    
    # Get database URL from environment variable
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not found!")
        print("Make sure you're running this in the Render environment.")
        return False
    
    try:
        # Parse the database URL
        # Format: postgresql://username:password@hostname:port/database
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgres://')
        
        print(f"Connecting to production database...")
        
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Connected to production database successfully!")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'assignment' 
            AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Add missing columns
        columns_to_add = []
        
        if 'allow_save_and_continue' not in existing_columns:
            columns_to_add.append("allow_save_and_continue BOOLEAN DEFAULT FALSE")
            
        if 'max_save_attempts' not in existing_columns:
            columns_to_add.append("max_save_attempts INTEGER DEFAULT 3")
            
        if 'save_timeout_minutes' not in existing_columns:
            columns_to_add.append("save_timeout_minutes INTEGER DEFAULT 30")
        
        if not columns_to_add:
            print("All required columns already exist. No changes needed.")
            return True
        
        # Add the missing columns
        for column_def in columns_to_add:
            column_name = column_def.split()[0]
            print(f"Adding column: {column_def}")
            
            try:
                cursor.execute(f"ALTER TABLE assignment ADD COLUMN {column_def}")
                print(f"✓ Successfully added column: {column_name}")
            except psycopg2.Error as e:
                print(f"✗ Error adding column {column_name}: {e}")
                continue
        
        # Verify the columns were added
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'assignment' 
            AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes')
            ORDER BY column_name
        """)
        
        print("\nFinal column status:")
        for row in cursor.fetchall():
            column_name, data_type, default_value = row
            print(f"  {column_name}: {data_type} (default: {default_value})")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Production database fix completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing Production Assignment Table Columns")
    print("=" * 50)
    
    success = fix_production_assignment_columns()
    
    if success:
        print("\n🎉 Production database is now fixed!")
        print("The assignment table now has all required columns.")
        print("You can now access the management dashboard without errors.")
    else:
        print("\n💥 Fix failed. Please check the error messages above.")
        sys.exit(1)
