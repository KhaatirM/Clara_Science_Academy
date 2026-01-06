"""
Migration script to add the 'assignment_type' and 'assignment_context' columns to the 'group_assignment' table.
These columns already exist in the model but may be missing from the database.
"""
from app import create_app
from extensions import db
from sqlalchemy import text

def add_assignment_type_columns():
    """Add assignment_type and assignment_context columns to group_assignment table if they don't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            
            if 'assignment_type' not in columns:
                print("[INFO] Adding 'assignment_type' column to 'group_assignment' table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN assignment_type VARCHAR(20) DEFAULT 'pdf' NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'assignment_type' column to 'group_assignment' table")
            else:
                print("[OK] 'assignment_type' column already exists in 'group_assignment' table")
            
            if 'assignment_context' not in columns:
                print("[INFO] Adding 'assignment_context' column to 'group_assignment' table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN assignment_context VARCHAR(20) DEFAULT 'homework' NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'assignment_context' column to 'group_assignment' table")
            else:
                print("[OK] 'assignment_context' column already exists in 'group_assignment' table")
            
            # Add quiz-related columns if missing
            if 'allow_save_and_continue' not in columns:
                print("[INFO] Adding 'allow_save_and_continue' column to 'group_assignment' table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN allow_save_and_continue BOOLEAN DEFAULT 0 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'allow_save_and_continue' column to 'group_assignment' table")
            else:
                print("[OK] 'allow_save_and_continue' column already exists in 'group_assignment' table")
            
            if 'max_save_attempts' not in columns:
                print("[INFO] Adding 'max_save_attempts' column to 'group_assignment' table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN max_save_attempts INTEGER DEFAULT 10 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'max_save_attempts' column to 'group_assignment' table")
            else:
                print("[OK] 'max_save_attempts' column already exists in 'group_assignment' table")
            
            if 'save_timeout_minutes' not in columns:
                print("[INFO] Adding 'save_timeout_minutes' column to 'group_assignment' table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN save_timeout_minutes INTEGER DEFAULT 30 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'save_timeout_minutes' column to 'group_assignment' table")
            else:
                print("[OK] 'save_timeout_minutes' column already exists in 'group_assignment' table")
                
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to add columns: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_assignment_type_columns()

