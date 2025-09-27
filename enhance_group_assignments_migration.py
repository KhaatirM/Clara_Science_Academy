#!/usr/bin/env python3
"""
Enhanced Group Assignments Migration Script

This script enhances the GroupAssignment model to support all assignment types:
- PDF/Paper assignments
- Quiz assignments  
- Discussion assignments

It adds the necessary database columns and creates new tables for group quiz functionality.
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import GroupAssignment, GroupQuizQuestion, GroupQuizOption, GroupQuizAnswer

def enhance_group_assignments():
    """Enhance GroupAssignment model with new assignment types and quiz functionality."""
    
    app = create_app()
    
    with app.app_context():
        print("Starting Group Assignment Enhancement Migration...")
        
        try:
            # Check if the new columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            
            print(f"Existing columns in group_assignment table: {existing_columns}")
            
            # Add new columns to GroupAssignment table if they don't exist
            new_columns = [
                'assignment_type',
                'status', 
                'allow_save_and_continue',
                'max_save_attempts',
                'save_timeout_minutes'
            ]
            
            for column in new_columns:
                if column not in existing_columns:
                    if column == 'assignment_type':
                        with db.engine.connect() as connection:
                            connection.execute(db.text(f"ALTER TABLE group_assignment ADD COLUMN {column} VARCHAR(20) DEFAULT 'pdf' NOT NULL"))
                            connection.commit()
                        print(f"Added column: {column}")
                    elif column == 'status':
                        with db.engine.connect() as connection:
                            connection.execute(db.text(f"ALTER TABLE group_assignment ADD COLUMN {column} VARCHAR(20) DEFAULT 'Active' NOT NULL"))
                            connection.commit()
                        print(f"Added column: {column}")
                    elif column == 'allow_save_and_continue':
                        with db.engine.connect() as connection:
                            connection.execute(db.text(f"ALTER TABLE group_assignment ADD COLUMN {column} BOOLEAN DEFAULT FALSE NOT NULL"))
                            connection.commit()
                        print(f"Added column: {column}")
                    elif column == 'max_save_attempts':
                        with db.engine.connect() as connection:
                            connection.execute(db.text(f"ALTER TABLE group_assignment ADD COLUMN {column} INTEGER DEFAULT 10 NOT NULL"))
                            connection.commit()
                        print(f"Added column: {column}")
                    elif column == 'save_timeout_minutes':
                        with db.engine.connect() as connection:
                            connection.execute(db.text(f"ALTER TABLE group_assignment ADD COLUMN {column} INTEGER DEFAULT 30 NOT NULL"))
                            connection.commit()
                        print(f"Added column: {column}")
                else:
                    print(f"Column {column} already exists")
            
            # Create new tables for group quiz functionality
            print("\nCreating new tables for group quiz functionality...")
            
            # Create GroupQuizQuestion table
            try:
                db.create_all()
                print("Created GroupQuizQuestion table")
            except Exception as e:
                print(f"Error creating GroupQuizQuestion table: {e}")
            
            # Create GroupQuizOption table
            try:
                db.create_all()
                print("Created GroupQuizOption table")
            except Exception as e:
                print(f"Error creating GroupQuizOption table: {e}")
            
            # Create GroupQuizAnswer table
            try:
                db.create_all()
                print("Created GroupQuizAnswer table")
            except Exception as e:
                print(f"Error creating GroupQuizAnswer table: {e}")
            
            # Update existing group assignments to have default values
            print("\nUpdating existing group assignments...")
            
            existing_assignments = GroupAssignment.query.all()
            updated_count = 0
            
            for assignment in existing_assignments:
                if not hasattr(assignment, 'assignment_type') or assignment.assignment_type is None:
                    assignment.assignment_type = 'pdf'
                    updated_count += 1
                
                if not hasattr(assignment, 'status') or assignment.status is None:
                    assignment.status = 'Active'
                    updated_count += 1
                
                if not hasattr(assignment, 'allow_save_and_continue'):
                    assignment.allow_save_and_continue = False
                    updated_count += 1
                
                if not hasattr(assignment, 'max_save_attempts'):
                    assignment.max_save_attempts = 10
                    updated_count += 1
                
                if not hasattr(assignment, 'save_timeout_minutes'):
                    assignment.save_timeout_minutes = 30
                    updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
                print(f"Updated {updated_count} existing group assignments with default values")
            else:
                print("No existing group assignments needed updates")
            
            print("\nGroup Assignment Enhancement Migration completed successfully!")
            print("New features available:")
            print("- PDF/Paper group assignments with file uploads")
            print("- Quiz group assignments with multiple question types")
            print("- Discussion group assignments with structured prompts")
            print("- Enhanced group settings and collaboration options")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            db.session.rollback()
            raise e

if __name__ == '__main__':
    enhance_group_assignments()
