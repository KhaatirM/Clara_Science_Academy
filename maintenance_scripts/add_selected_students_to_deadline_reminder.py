"""
Migration script to add selected_student_ids field to deadline_reminder table.
This allows reminders to be sent to specific students only.
"""

from app import create_app, db
from sqlalchemy import text

def add_selected_students_field():
    """Add selected_student_ids JSON field to deadline_reminder table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='deadline_reminder' 
                AND column_name='selected_student_ids'
            """))
            
            if result.fetchone():
                print("✅ Column 'selected_student_ids' already exists!")
                return
            
            # Add the column
            db.session.execute(text("""
                ALTER TABLE deadline_reminder 
                ADD COLUMN selected_student_ids TEXT
            """))
            
            db.session.commit()
            print("✅ Successfully added 'selected_student_ids' column to deadline_reminder table!")
            print("\nColumn Details:")
            print("  - Name: selected_student_ids")
            print("  - Type: TEXT (stores JSON array of student IDs)")
            print("  - Purpose: Allows reminders to be sent to specific students only")
            print("  - Format: JSON array like '[1, 2, 3]' or NULL for all students")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding column: {e}")
            raise

if __name__ == '__main__':
    add_selected_students_field()

