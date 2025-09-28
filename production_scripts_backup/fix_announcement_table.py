import sqlite3
import os

def fix_announcement_table():
    """Fix the announcement table to match the SQLAlchemy model structure."""
    
    db_path = 'instance/app.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Fixing announcement table to match SQLAlchemy model...")
        print("=" * 50)
        
        # Check current structure
        cursor.execute("PRAGMA table_info(announcement)")
        current_cols = cursor.fetchall()
        current_col_names = [col[1] for col in current_cols]
        
        print("Current announcement table columns:")
        for col in current_cols:
            print(f"  - {col[1]} ({col[2]})")
        
        # Expected columns from the model
        expected_columns = [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('title', 'VARCHAR(200) NOT NULL'),
            ('message', 'TEXT NOT NULL'),
            ('sender_id', 'INTEGER NOT NULL'),
            ('timestamp', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('target_group', 'VARCHAR(32) NOT NULL'),
            ('class_id', 'INTEGER'),
            ('is_important', 'BOOLEAN DEFAULT FALSE'),
            ('requires_confirmation', 'BOOLEAN DEFAULT FALSE'),
            ('rich_content', 'TEXT'),
            ('expires_at', 'DATETIME')
        ]
        
        print(f"\nExpected columns from model: {[col[0] for col in expected_columns]}")
        
        # Check what needs to be added
        columns_to_add = []
        
        for col_name, col_def in expected_columns:
            if col_name not in current_col_names:
                columns_to_add.append((col_name, col_def))
        
        if columns_to_add:
            print(f"\nAdding missing columns: {[col[0] for col in columns_to_add]}")
            
            for col_name, col_def in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE announcement ADD COLUMN {col_name} {col_def}")
                    print(f"  ✓ Added column: {col_name}")
                except Exception as e:
                    print(f"  ✗ Error adding {col_name}: {e}")
        else:
            print("\nAll expected columns are present!")
        
        # Add foreign key constraints if they don't exist
        try:
            # Check if foreign key constraints exist
            cursor.execute("PRAGMA foreign_key_list(announcement)")
            fk_list = cursor.fetchall()
            
            if not any(fk[3] == 'sender_id' for fk in fk_list):
                print("  ⚠ Note: sender_id foreign key constraint not found")
            
            if not any(fk[3] == 'class_id' for fk in fk_list):
                print("  ⚠ Note: class_id foreign key constraint not found")
                
        except Exception as e:
            print(f"  ⚠ Note: Could not check foreign key constraints: {e}")
        
        conn.commit()
        print("\n" + "=" * 50)
        print("Announcement table updated successfully!")
        
        # Verify final structure
        print("\nFinal announcement table structure:")
        cursor.execute("PRAGMA table_info(announcement)")
        for col in cursor.fetchall():
            print(f"  - {col[1]} ({col[2]})")
        
        # Show record count
        cursor.execute("SELECT COUNT(*) FROM announcement")
        count = cursor.fetchone()[0]
        print(f"\nTotal announcement records: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error updating announcement table: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_announcement_table()
