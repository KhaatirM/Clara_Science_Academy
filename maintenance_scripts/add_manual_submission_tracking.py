"""
Migration script to add manual submission tracking fields to the Submission table.
This allows tracking physical/paper submissions without requiring file uploads.

Fields added:
- submission_type: 'online', 'in_person', or 'not_submitted'
- submission_notes: Notes like "Turned in late", "Resubmitted"
- marked_by: Teacher who manually marked the submission
- marked_at: Timestamp when manually marked

Run this script once:
    python add_manual_submission_tracking.py
"""

from app import create_app, db
from sqlalchemy import text

def add_manual_submission_tracking():
    """Add manual submission tracking fields to the Submission table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('submission')]
            
            columns_to_add = []
            
            if 'submission_type' not in existing_columns:
                columns_to_add.append("submission_type VARCHAR(20) DEFAULT 'online' NOT NULL")
            
            if 'submission_notes' not in existing_columns:
                columns_to_add.append("submission_notes TEXT")
            
            if 'marked_by' not in existing_columns:
                columns_to_add.append("marked_by INTEGER")
            
            if 'marked_at' not in existing_columns:
                # Use TIMESTAMP for PostgreSQL compatibility
                columns_to_add.append("marked_at TIMESTAMP")
            
            if not columns_to_add:
                print("✅ All columns already exist! No migration needed.")
                return
            
            # Add columns one by one with proper error handling
            for column_def in columns_to_add:
                column_name = column_def.split()[0]
                try:
                    db.session.execute(text(f"ALTER TABLE submission ADD COLUMN {column_def}"))
                    db.session.commit()  # Commit each column separately
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    db.session.rollback()  # Rollback the failed column
                    print(f"⚠️  Column {column_name} may already exist or error: {e}")
            
            # Update existing submissions to have submission_type = 'online' if they have a file_path
            try:
                db.session.execute(text("""
                    UPDATE submission 
                    SET submission_type = CASE 
                        WHEN file_path IS NOT NULL AND file_path != '' THEN 'online'
                        ELSE 'not_submitted'
                    END
                    WHERE submission_type IS NULL OR submission_type = ''
                """))
                db.session.commit()
                print("✅ Updated existing submissions with default types")
            except Exception as e:
                db.session.rollback()
                print(f"⚠️  Error updating existing submissions: {e}")
            
            print("\n✨ Manual Submission Tracking is ready!")
            print("\nNew Features Available:")
            print("  ✅ Mark submissions as 'online', 'in_person', or 'not_submitted'")
            print("  ✅ Add submission notes (e.g., 'Turned in late')")
            print("  ✅ Track who manually marked submissions")
            print("  ✅ Grade physical papers without file uploads")
            print("  ✅ Bulk submission marking")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_manual_submission_tracking()

