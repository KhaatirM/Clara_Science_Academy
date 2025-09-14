#!/usr/bin/env python3
"""
Production migration script to add status field to Assignment model (PostgreSQL version).
This script adds the status field with default value 'Active' to all existing assignments.
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def add_assignment_status_field():
    """Add status field to Assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            with db.engine.connect() as connection:
                # Check if status column already exists (PostgreSQL syntax)
                result = connection.execute(text("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'assignment' AND column_name = 'status'
                """)).scalar()
                
                if result:
                    print("✅ Status column already exists in assignment table")
                    return True
                
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
                print("✅ Status column added successfully to assignment table")
                print("✅ All existing assignments set to 'Active' status")
                
        except Exception as e:
            print(f"❌ Error adding status column: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Starting assignment status migration for production...")
    success = add_assignment_status_field()
    
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")
        sys.exit(1)
