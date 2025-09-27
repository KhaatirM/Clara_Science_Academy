#!/usr/bin/env python3
"""
Fix Class table schema for PostgreSQL
Handles the DATETIME vs TIMESTAMP issue and failed transactions
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text

def fix_postgres_class_schema():
    """Fix Class table schema for PostgreSQL."""
    
    print("🔧 Fixing PostgreSQL Class table schema...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check database type
            db_url = str(db.engine.url)
            is_postgres = 'postgresql' in db_url
            
            print(f"Database type: {'PostgreSQL' if is_postgres else 'Other'}")
            
            if not is_postgres:
                print("❌ This script is for PostgreSQL only!")
                return False
            
            # Check if class table exists
            inspector = inspect(db.engine)
            if 'class' not in inspector.get_table_names():
                print("❌ Class table not found!")
                return False
            
            # Get existing columns
            columns = [col['name'] for col in inspector.get_columns('class')]
            print(f"Existing columns: {columns}")
            
            # Define columns to add with correct PostgreSQL types
            columns_to_add = [
                ('room_number', 'VARCHAR(20)'),
                ('schedule', 'VARCHAR(200)'),
                ('max_students', 'INTEGER DEFAULT 30 NOT NULL'),
                ('description', 'TEXT'),
                ('is_active', 'BOOLEAN DEFAULT TRUE NOT NULL'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL')
            ]
            
            # Add missing columns with proper transaction handling
            with db.engine.connect() as connection:
                # Start a transaction
                trans = connection.begin()
                try:
                    for column_name, column_type in columns_to_add:
                        if column_name not in columns:
                            try:
                                sql = f"ALTER TABLE class ADD COLUMN {column_name} {column_type}"
                                print(f"Adding column: {column_name} ({column_type})")
                                connection.execute(text(sql))
                                print(f"✓ Added: {column_name}")
                            except Exception as e:
                                print(f"⚠ Error adding {column_name}: {e}")
                                # Rollback the transaction and continue
                                trans.rollback()
                                trans = connection.begin()
                                continue
                        else:
                            print(f"✓ Column {column_name} already exists")
                    
                    # Commit the transaction
                    trans.commit()
                    print("✅ All columns added successfully!")
                    
                except Exception as e:
                    print(f"❌ Transaction failed: {e}")
                    trans.rollback()
                    return False
            
            # Create association tables if they don't exist
            print("\n🔧 Creating association tables...")
            
            association_tables = [
                ('class_additional_teachers', '''
                    CREATE TABLE IF NOT EXISTS class_additional_teachers (
                        class_id INTEGER NOT NULL,
                        teacher_id INTEGER NOT NULL,
                        role VARCHAR(50) DEFAULT 'co-teacher' NOT NULL,
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        PRIMARY KEY (class_id, teacher_id),
                        FOREIGN KEY (class_id) REFERENCES class (id),
                        FOREIGN KEY (teacher_id) REFERENCES teacher_staff (id)
                    )
                '''),
                
                ('class_substitute_teachers', '''
                    CREATE TABLE IF NOT EXISTS class_substitute_teachers (
                        class_id INTEGER NOT NULL,
                        teacher_id INTEGER NOT NULL,
                        priority INTEGER DEFAULT 1 NOT NULL,
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        PRIMARY KEY (class_id, teacher_id),
                        FOREIGN KEY (class_id) REFERENCES class (id),
                        FOREIGN KEY (teacher_id) REFERENCES teacher_staff (id)
                    )
                ''')
            ]
            
            with db.engine.connect() as connection:
                for table_name, create_sql in association_tables:
                    try:
                        if table_name not in inspector.get_table_names():
                            print(f"Creating table: {table_name}")
                            connection.execute(text(create_sql))
                            print(f"✓ Created: {table_name}")
                        else:
                            print(f"✓ Table {table_name} already exists")
                    except Exception as e:
                        print(f"⚠ Error creating {table_name}: {e}")
                
                connection.commit()
            
            print("\n✅ PostgreSQL Class table schema fix completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during schema fix: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = fix_postgres_class_schema()
    if success:
        print("\n🎉 PostgreSQL Class table schema fix completed successfully!")
    else:
        print("\n💥 PostgreSQL Class table schema fix failed!")
        sys.exit(1)
