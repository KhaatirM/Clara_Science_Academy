#!/usr/bin/env python3
"""
Script to recreate the database with all current models.
This will delete the existing database and create a fresh one with all tables.
"""

import os
from app import create_app
from extensions import db
from models import *

def recreate_database():
    """Recreate the database with all current models."""
    
    # Create the app instance
    app = create_app()
    
    # Get the database file path
    db_path = os.path.join(app.instance_path, 'app.db')
    
    # Remove existing database file if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    # Create the database directory if it doesn't exist
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Create all tables
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
        
        # Verify all tables were created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {', '.join(tables)}")

if __name__ == '__main__':
    print("=== Database Recreation Script ===")
    print("This will DELETE the existing database and create a fresh one.")
    print("All existing data will be lost!")
    
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        recreate_database()
        print("\n=== Database recreation complete! ===")
        print("You may need to run add_test_users.py to add test users again.")
    else:
        print("Database recreation cancelled.") 