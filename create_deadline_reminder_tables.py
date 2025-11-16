"""
Migration script to create deadline_reminder and reminder_notification tables.
This script should be run on Render Shell if the tables don't exist yet.
"""

from app import create_app, db
from sqlalchemy import text, inspect

def create_deadline_reminder_tables():
    """Create deadline_reminder and reminder_notification tables if they don't exist."""
    app = create_app()
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Check if deadline_reminder table exists
            if 'deadline_reminder' not in existing_tables:
                print("Creating deadline_reminder table...")
                db.create_all()  # This will create all missing tables based on models
                print("✅ Successfully created deadline_reminder table!")
            else:
                print("✅ deadline_reminder table already exists!")
            
            # Check if reminder_notification table exists
            if 'reminder_notification' not in existing_tables:
                print("Creating reminder_notification table...")
                db.create_all()  # This will create all missing tables based on models
                print("✅ Successfully created reminder_notification table!")
            else:
                print("✅ reminder_notification table already exists!")
            
            # Refresh table list after potential creation
            existing_tables = inspector.get_table_names()
            
            # Now check if selected_student_ids column exists
            if 'deadline_reminder' in existing_tables:
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='deadline_reminder' 
                    AND column_name='selected_student_ids'
                """))
                
                if not result.fetchone():
                    print("\nAdding selected_student_ids column to deadline_reminder table...")
                    db.session.execute(text("""
                        ALTER TABLE deadline_reminder 
                        ADD COLUMN selected_student_ids TEXT
                    """))
                    db.session.commit()
                    print("✅ Successfully added 'selected_student_ids' column!")
                else:
                    print("✅ Column 'selected_student_ids' already exists!")
            
            print("\n" + "="*60)
            print("✅ Deadline reminder tables migration complete!")
            print("="*60)
            print("\nTables created/verified:")
            print("  - deadline_reminder")
            print("  - reminder_notification")
            print("  - selected_student_ids column added")
            print("\nYou can now use the deadline reminders feature!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during migration: {e}")
            print("\nTrying alternative method...")
            try:
                # Try using db.create_all() which should create tables from models
                from models import DeadlineReminder, ReminderNotification
                db.create_all()
                print("✅ Tables created using db.create_all()")
            except Exception as e2:
                print(f"❌ Alternative method also failed: {e2}")
                raise

if __name__ == '__main__':
    create_deadline_reminder_tables()

