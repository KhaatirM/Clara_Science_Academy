"""
Migration script to add is_edited and parent_message_id columns to message table.
"""

from app import create_app, db
from sqlalchemy import text, inspect

def add_message_columns():
    """Add missing columns to message table."""
    app = create_app()
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            # Check if message table exists
            if 'message' not in inspector.get_table_names():
                print("Message table doesn't exist. Creating all tables...")
                db.create_all()
                print("✅ All tables created successfully!")
                return True
            
            # Get existing columns
            columns = [col['name'] for col in inspector.get_columns('message')]
            print(f"Existing message table columns: {columns}")
            
            # Add is_edited column if it doesn't exist
            if 'is_edited' not in columns:
                print("Adding is_edited column to message table...")
                db.session.execute(text("ALTER TABLE message ADD COLUMN is_edited BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("✅ Added is_edited column")
            else:
                print("✅ is_edited column already exists")
            
            # Add parent_message_id column if it doesn't exist
            if 'parent_message_id' not in columns:
                print("Adding parent_message_id column to message table...")
                db.session.execute(text("ALTER TABLE message ADD COLUMN parent_message_id INTEGER"))
                db.session.commit()
                print("✅ Added parent_message_id column")
            else:
                print("✅ parent_message_id column already exists")
            
            # Check if message_reaction table exists, create if not
            if 'message_reaction' not in inspector.get_table_names():
                print("Creating message_reaction table...")
                db.create_all()
                print("✅ message_reaction table created")
            else:
                print("✅ message_reaction table already exists")
            
            print("\n✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    add_message_columns()

