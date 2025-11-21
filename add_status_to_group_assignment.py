"""
Migration script to add the 'status' column to the 'group_assignment' table.
This column already exists in the model but may be missing from the database.
"""
from app import create_app
from extensions import db
from sqlalchemy import text

def add_status_column():
    """Add status column to group_assignment table if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            
            if 'status' not in columns:
                print("[INFO] Adding 'status' column to 'group_assignment' table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN status VARCHAR(20) DEFAULT 'Active' NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'status' column to 'group_assignment' table")
            else:
                print("[OK] 'status' column already exists in 'group_assignment' table")
                
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to add 'status' column: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_status_column()

