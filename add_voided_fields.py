"""
Migration script to add voided fields to Grade and GroupGrade models.
This allows for voiding individual grades while keeping the records.
"""

import sqlite3
import os

def add_voided_fields():
    """Add voided fields to Grade and GroupGrade tables."""
    db_path = os.path.join('instance', 'app.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"Connected to database at {db_path}")
        
        # Check and add voided fields to grade table
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN is_voided BOOLEAN DEFAULT 0")
            print("✓ Added 'is_voided' field to Grade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'is_voided' field already exists in Grade table")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN voided_by INTEGER")
            print("✓ Added 'voided_by' field to Grade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'voided_by' field already exists in Grade table")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN voided_at TIMESTAMP")
            print("✓ Added 'voided_at' field to Grade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'voided_at' field already exists in Grade table")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE grade ADD COLUMN voided_reason TEXT")
            print("✓ Added 'voided_reason' field to Grade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'voided_reason' field already exists in Grade table")
            else:
                raise
        
        # Check and add voided fields to group_grade table
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN is_voided BOOLEAN DEFAULT 0")
            print("✓ Added 'is_voided' field to GroupGrade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'is_voided' field already exists in GroupGrade table")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN voided_by INTEGER")
            print("✓ Added 'voided_by' field to GroupGrade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'voided_by' field already exists in GroupGrade table")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN voided_at TIMESTAMP")
            print("✓ Added 'voided_at' field to GroupGrade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'voided_at' field already exists in GroupGrade table")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE group_grade ADD COLUMN voided_reason TEXT")
            print("✓ Added 'voided_reason' field to GroupGrade table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓ 'voided_reason' field already exists in GroupGrade table")
            else:
                raise
        
        conn.commit()
        print("\n✅ Successfully added all voided fields!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    add_voided_fields()
