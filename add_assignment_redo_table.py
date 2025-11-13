"""
Migration script to add the assignment_redo table to the database.
This table tracks redo permissions granted to students for assignments.

Run this script once to create the table:
    python add_assignment_redo_table.py
"""

from app import create_app, db
from models import AssignmentRedo

def add_assignment_redo_table():
    """Create the assignment_redo table if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the table
            db.create_all()
            print("✅ Successfully created assignment_redo table!")
            print("\nTable structure:")
            print("  - id: Primary key")
            print("  - assignment_id: Foreign key to assignment")
            print("  - student_id: Foreign key to student")
            print("  - granted_by: Teacher/admin who granted redo")
            print("  - granted_at: When redo was granted")
            print("  - redo_deadline: New deadline for redo")
            print("  - reason: Optional reason for granting redo")
            print("  - is_used: Has student used the redo?")
            print("  - redo_submission_id: Links to redo submission")
            print("  - redo_submitted_at: When redo was submitted")
            print("  - original_grade: Grade before redo")
            print("  - redo_grade: Grade from redo attempt")
            print("  - final_grade: Final calculated grade")
            print("  - was_redo_late: Was redo submitted late?")
            print("\n✨ Assignment Redo System is ready to use!")
            
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_assignment_redo_table()

