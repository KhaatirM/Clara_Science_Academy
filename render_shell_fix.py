#!/usr/bin/env python3
"""
Simple script to run in Render shell to fix the Class table schema
"""

from sqlalchemy import text

# Connect to the database
from app import create_app, db

app = create_app()
with app.app_context():
    print("🔧 Fixing PostgreSQL Class table schema...")
    
    try:
        with db.engine.connect() as connection:
            # Check what columns exist
            result = connection.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'class'"))
            existing_columns = [row[0] for row in result]
            print(f"Existing columns: {existing_columns}")
            
            # Add missing columns one by one
            columns_to_add = [
                ('room_number', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS room_number VARCHAR(20)'),
                ('schedule', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS schedule VARCHAR(200)'),
                ('max_students', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS max_students INTEGER DEFAULT 30'),
                ('description', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS description TEXT'),
                ('is_active', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE'),
                ('created_at', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'ALTER TABLE class ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            for col_name, sql in columns_to_add:
                if col_name not in existing_columns:
                    try:
                        print(f"Adding column: {col_name}")
                        connection.execute(text(sql))
                        print(f"✓ Added: {col_name}")
                    except Exception as e:
                        print(f"⚠ Error adding {col_name}: {e}")
                else:
                    print(f"✓ Column {col_name} already exists")
            
            connection.commit()
            
            # Create association tables
            print("\n🔧 Creating association tables...")
            
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS class_additional_teachers (
                    class_id INTEGER NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    role VARCHAR(50) DEFAULT 'co-teacher' NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (class_id, teacher_id),
                    FOREIGN KEY (class_id) REFERENCES class (id),
                    FOREIGN KEY (teacher_id) REFERENCES teacher_staff (id)
                )
            """))
            
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS class_substitute_teachers (
                    class_id INTEGER NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    priority INTEGER DEFAULT 1 NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (class_id, teacher_id),
                    FOREIGN KEY (class_id) REFERENCES class (id),
                    FOREIGN KEY (teacher_id) REFERENCES teacher_staff (id)
                )
            """))
            
            connection.commit()
            
            print("✅ PostgreSQL Class table schema fix completed successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
