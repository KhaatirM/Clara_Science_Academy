#!/usr/bin/env python3
"""
Unified Database Manager

This script consolidates database creation and management functionality
into a single, comprehensive system.
"""

import os
from app import create_app, db
from models import db as models_db
from werkzeug.security import generate_password_hash
from datetime import datetime

class DatabaseManager:
    """Manages database operations for the application."""
    
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_context.pop()
    
    def create_all_tables(self):
        """Create all database tables."""
        print("Creating all database tables...")
        try:
            db.create_all()
            print("✅ All tables created successfully!")
            return True
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
    
    def drop_all_tables(self):
        """Drop all database tables."""
        print("Dropping all database tables...")
        try:
            db.drop_all()
            print("✅ All tables dropped successfully!")
            return True
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return False
    
    def recreate_database(self):
        """Recreate the entire database (drop and create all tables)."""
        print("Recreating database...")
        try:
            # Drop all tables
            self.drop_all_tables()
            
            # Create all tables
            self.create_all_tables()
            
            print("✅ Database recreated successfully!")
            return True
        except Exception as e:
            print(f"❌ Error recreating database: {e}")
            return False
    
    def create_admin_user(self):
        """Create a default admin user."""
        print("Creating admin user...")
        try:
            from models import User
            
            # Check if admin user already exists
            existing_admin = User.query.filter_by(email='admin@school.edu').first()
            if existing_admin:
                print("Admin user already exists")
                return existing_admin
            
            # Create admin user
            admin_user = User(
                email='admin@school.edu',
                password_hash=generate_password_hash('admin123'),
                first_name='Admin',
                last_name='User',
                role='Director',
                is_active=True,
                created_at=datetime.now()
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Admin user created successfully!")
            print("Email: admin@school.edu")
            print("Password: admin123")
            return admin_user
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            db.session.rollback()
            return None
    
    def get_database_info(self):
        """Get information about the current database."""
        print("Database Information:")
        print(f"Database URL: {db.engine.url}")
        print(f"Tables: {list(db.engine.table_names())}")
        
        # Count records in each table
        from models import User, Student, TeacherStaff, Class, Assignment, SchoolYear
        
        tables_info = {
            'Users': User.query.count(),
            'Students': Student.query.count(),
            'Teachers': TeacherStaff.query.count(),
            'Classes': Class.query.count(),
            'Assignments': Assignment.query.count(),
            'School Years': SchoolYear.query.count()
        }
        
        print("\nRecord counts:")
        for table, count in tables_info.items():
            print(f"  {table}: {count}")
    
    def setup_fresh_database(self):
        """Set up a completely fresh database with admin user."""
        print("Setting up fresh database...")
        
        try:
            # Recreate database
            if not self.recreate_database():
                return False
            
            # Create admin user
            admin_user = self.create_admin_user()
            if not admin_user:
                return False
            
            print("✅ Fresh database setup completed!")
            print("You can now log in with:")
            print("Email: admin@school.edu")
            print("Password: admin123")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up fresh database: {e}")
            return False

def main():
    """Main function with command line interface."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python database_manager.py [command]")
        print("Commands:")
        print("  create    - Create all tables")
        print("  drop      - Drop all tables")
        print("  recreate  - Recreate all tables")
        print("  fresh     - Setup fresh database with admin user")
        print("  info      - Show database information")
        return
    
    command = sys.argv[1].lower()
    
    with DatabaseManager() as manager:
        if command == 'create':
            manager.create_all_tables()
        elif command == 'drop':
            manager.drop_all_tables()
        elif command == 'recreate':
            manager.recreate_database()
        elif command == 'fresh':
            manager.setup_fresh_database()
        elif command == 'info':
            manager.get_database_info()
        else:
            print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()



