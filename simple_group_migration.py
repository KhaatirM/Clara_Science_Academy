#!/usr/bin/env python3
"""
Simple Group Assignment Migration Script
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def run_migration():
    """Run the group assignment migration."""
    
    print("Creating Flask app...")
    app = create_app()
    
    with app.app_context():
        print("Starting migration...")
        
        try:
            # Check if database file exists
            db_path = os.path.join(app.instance_path, 'database.db')
            print(f"Database path: {db_path}")
            print(f"Database exists: {os.path.exists(db_path)}")
            
            # Try to create all tables (this will add new columns and tables)
            print("Creating/updating database tables...")
            db.create_all()
            print("Database tables created/updated successfully!")
            
            # Check what tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Tables in database: {tables}")
            
            # Check if group_assignment table has new columns
            if 'group_assignment' in tables:
                columns = [col['name'] for col in inspector.get_columns('group_assignment')]
                print(f"Group assignment columns: {columns}")
                
                new_columns = ['assignment_type', 'status', 'allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes']
                missing_columns = [col for col in new_columns if col not in columns]
                
                if missing_columns:
                    print(f"Missing columns: {missing_columns}")
                    print("Adding missing columns...")
                    
                    # Add missing columns using raw SQL
                    with db.engine.connect() as connection:
                        if 'assignment_type' in missing_columns:
                            connection.execute(db.text("ALTER TABLE group_assignment ADD COLUMN assignment_type VARCHAR(20) DEFAULT 'pdf' NOT NULL"))
                            print("Added assignment_type column")
                        
                        if 'status' in missing_columns:
                            connection.execute(db.text("ALTER TABLE group_assignment ADD COLUMN status VARCHAR(20) DEFAULT 'Active' NOT NULL"))
                            print("Added status column")
                        
                        if 'allow_save_and_continue' in missing_columns:
                            connection.execute(db.text("ALTER TABLE group_assignment ADD COLUMN allow_save_and_continue BOOLEAN DEFAULT FALSE NOT NULL"))
                            print("Added allow_save_and_continue column")
                        
                        if 'max_save_attempts' in missing_columns:
                            connection.execute(db.text("ALTER TABLE group_assignment ADD COLUMN max_save_attempts INTEGER DEFAULT 10 NOT NULL"))
                            print("Added max_save_attempts column")
                        
                        if 'save_timeout_minutes' in missing_columns:
                            connection.execute(db.text("ALTER TABLE group_assignment ADD COLUMN save_timeout_minutes INTEGER DEFAULT 30 NOT NULL"))
                            print("Added save_timeout_minutes column")
                        
                        connection.commit()
                else:
                    print("All required columns already exist!")
            
            print("\nMigration completed successfully!")
            print("New features available:")
            print("- PDF/Paper group assignments")
            print("- Quiz group assignments") 
            print("- Discussion group assignments")
            print("- Enhanced group settings")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == '__main__':
    success = run_migration()
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
