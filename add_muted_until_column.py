"""
Migration script to add muted_until column to message_group_member table.
"""
import sqlite3
import os
from datetime import datetime

def add_muted_until_column():
    # Try multiple possible database paths
    possible_paths = [
        'instance/app.db',
        'instance/school_management.db',
        os.path.join(os.path.dirname(__file__), 'instance', 'app.db'),
        os.path.join(os.path.dirname(__file__), 'instance', 'school_management.db')
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print(f"Database not found. Tried:")
        for path in possible_paths:
            print(f"  - {path}")
        return
    
    print(f"Using database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(message_group_member)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'muted_until' not in columns:
            # Add muted_until column
            cursor.execute("""
                ALTER TABLE message_group_member 
                ADD COLUMN muted_until DATETIME NULL
            """)
            conn.commit()
            print("[OK] Added muted_until column to message_group_member table")
        else:
            print("[OK] muted_until column already exists")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_muted_until_column()

