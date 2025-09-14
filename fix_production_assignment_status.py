#!/usr/bin/env python3
"""
Quick fix script for production assignment status column.
Run this on Render shell to add the missing status column.
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def fix_assignment_status():
    """Add status field to Assignment table in production."""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 Fixing assignment status column in production...")
            
            with db.engine.connect() as connection:
                # Add status column with default value 'Active'
                print("Adding status column to assignment table...")
                connection.execute(text("""
                    ALTER TABLE assignment 
                    ADD COLUMN status VARCHAR(20) DEFAULT 'Active' NOT NULL
                """))
                
                # Update all existing assignments to have 'Active' status
                print("Updating existing assignments to Active status...")
                connection.execute(text("""
                    UPDATE assignment 
                    SET status = 'Active' 
                    WHERE status IS NULL OR status = ''
                """))
                
                connection.commit()
                print("✅ Status column added successfully!")
                print("✅ All existing assignments set to 'Active' status")
                
                # Verify the fix
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM assignment WHERE status = 'Active'
                """)).scalar()
                print(f"✅ Verified: {result} assignments now have 'Active' status")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            print("💡 Try running the SQL commands directly in psql:")
            print("   ALTER TABLE assignment ADD COLUMN status VARCHAR(20) DEFAULT 'Active' NOT NULL;")
            print("   UPDATE assignment SET status = 'Active' WHERE status IS NULL OR status = '';")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting production assignment status fix...")
    success = fix_assignment_status()
    
    if success:
        print("🎉 Production fix completed successfully!")
        print("🌐 Your application should now work properly!")
    else:
        print("💥 Fix failed! Please try the manual SQL approach.")
        sys.exit(1)
