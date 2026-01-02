#!/usr/bin/env python3
"""
Migration script to add assignment_description column to cleaning_team_member table
This allows storing detailed job assignments for each team member.
"""

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_assignment_description_column():
    """Add assignment_description column to cleaning_team_member table"""
    with app.app_context():
        try:
            print("="*70)
            print("ADDING ASSIGNMENT_DESCRIPTION COLUMN TO CLEANING_TEAM_MEMBER")
            print("="*70)
            
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cleaning_team_member' 
                AND column_name='assignment_description'
            """))
            
            if result.fetchone():
                print("✓ Column 'assignment_description' already exists. Skipping migration.")
                return
            
            # Add the column
            print("\n[1] Adding assignment_description column to cleaning_team_member table...")
            db.session.execute(text("""
                ALTER TABLE cleaning_team_member 
                ADD COLUMN assignment_description TEXT
            """))
            
            db.session.commit()
            print("✓ Successfully added assignment_description column")
            
            print("\n" + "="*70)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("="*70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error during migration: {e}")
            print("Please check the database connection and permissions.")
            raise

if __name__ == "__main__":
    add_assignment_description_column()

