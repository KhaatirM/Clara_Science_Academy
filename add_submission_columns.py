"""
Migration script to add missing columns to the submission table.
These columns are used for manual submission tracking.
"""

from app import create_app, db
from config import DevelopmentConfig
from sqlalchemy import text

def add_submission_columns():
    """Add missing columns to submission table."""
    app = create_app(config_class=DevelopmentConfig)
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('submission')]
            
            print("[INFO] Checking submission table columns...")
            print(f"[INFO] Existing columns: {columns}")
            
            # Add missing columns one by one
            if 'submission_type' not in columns:
                print("[INFO] Adding submission_type column...")
                db.session.execute(text("""
                    ALTER TABLE submission 
                    ADD COLUMN submission_type VARCHAR(20) DEFAULT 'online' NOT NULL
                """))
                print("[OK] submission_type column added")
            else:
                print("[INFO] submission_type column already exists")
            
            if 'submission_notes' not in columns:
                print("[INFO] Adding submission_notes column...")
                db.session.execute(text("""
                    ALTER TABLE submission 
                    ADD COLUMN submission_notes TEXT
                """))
                print("[OK] submission_notes column added")
            else:
                print("[INFO] submission_notes column already exists")
            
            if 'marked_by' not in columns:
                print("[INFO] Adding marked_by column...")
                db.session.execute(text("""
                    ALTER TABLE submission 
                    ADD COLUMN marked_by INTEGER
                """))
                # Add foreign key constraint if teacher_staff table exists
                try:
                    db.session.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_submission_marked_by 
                        ON submission(marked_by)
                    """))
                except Exception as e:
                    print(f"[WARNING] Could not add index: {e}")
                print("[OK] marked_by column added")
            else:
                print("[INFO] marked_by column already exists")
            
            if 'marked_at' not in columns:
                print("[INFO] Adding marked_at column...")
                db.session.execute(text("""
                    ALTER TABLE submission 
                    ADD COLUMN marked_at DATETIME
                """))
                print("[OK] marked_at column added")
            else:
                print("[INFO] marked_at column already exists")
            
            db.session.commit()
            print("[OK] Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    print("[INFO] Starting submission table migration...")
    add_submission_columns()
    print("[OK] Migration finished!")

