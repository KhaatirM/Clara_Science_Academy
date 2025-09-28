#!/usr/bin/env python3
"""
Fix Production Password Fields Migration
=======================================

This script adds the missing password fields to the production User table.
This fixes the error: column user.is_temporary_password does not exist

Usage:
    python fix_production_password_fields.py
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import db
    from sqlalchemy import text
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def fix_production_password_fields():
    """Add missing password fields to the User table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' 
                    AND column_name IN ('is_temporary_password', 'password_changed_at', 'created_at', 'login_count')
                """))
                
                existing_columns = [row[0] for row in result]
                
                print("Checking existing columns...")
                print(f"Existing columns: {existing_columns}")
                
                # Add is_temporary_password column if it doesn't exist
                if 'is_temporary_password' not in existing_columns:
                    print("Adding is_temporary_password column...")
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ADD COLUMN is_temporary_password BOOLEAN DEFAULT FALSE NOT NULL
                    """))
                    conn.commit()
                    print("✅ is_temporary_password column added")
                else:
                    print("✅ is_temporary_password column already exists")
                
                # Add password_changed_at column if it doesn't exist
                if 'password_changed_at' not in existing_columns:
                    print("Adding password_changed_at column...")
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ADD COLUMN password_changed_at TIMESTAMP
                    """))
                    conn.commit()
                    print("✅ password_changed_at column added")
                else:
                    print("✅ password_changed_at column already exists")
                
                # Add created_at column if it doesn't exist
                if 'created_at' not in existing_columns:
                    print("Adding created_at column...")
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                    """))
                    conn.commit()
                    print("✅ created_at column added")
                else:
                    print("✅ created_at column already exists")
                
                # Add login_count column if it doesn't exist
                if 'login_count' not in existing_columns:
                    print("Adding login_count column...")
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ADD COLUMN login_count INTEGER DEFAULT 0 NOT NULL
                    """))
                    conn.commit()
                    print("✅ login_count column added")
                else:
                    print("✅ login_count column already exists")
                
                print("\n" + "=" * 60)
                print("MIGRATION COMPLETED SUCCESSFULLY")
                print("=" * 60)
                print("All password fields have been added to the User table.")
                print("The password change popup system should now work correctly.")
                
        except Exception as e:
            print(f"Error adding password fields: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

def main():
    """Main function."""
    print("Fixing production password fields in User table...")
    print("This will add missing columns for the password change system.")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    
    success = fix_production_password_fields()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("The production database should now work with the password change popup.")
    else:
        print("\n❌ Migration failed. Check the error messages above.")

if __name__ == '__main__':
    main()
