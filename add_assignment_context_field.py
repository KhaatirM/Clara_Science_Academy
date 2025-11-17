"""
Migration script to add assignment_context field to Assignment and GroupAssignment tables.
This field will store whether an assignment is 'in-class' or 'homework'.
"""

from app import create_app, db
from sqlalchemy import text

def add_assignment_context_field():
    """Add assignment_context column to assignment and group_assignment tables."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists in assignment table
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='assignment' AND column_name='assignment_context'
            """))
            
            if result.fetchone() is None:
                print("Adding assignment_context column to assignment table...")
                db.session.execute(text("""
                    ALTER TABLE assignment 
                    ADD COLUMN assignment_context VARCHAR(20) DEFAULT 'homework'
                """))
                db.session.commit()
                print("✅ Added assignment_context column to assignment table")
            else:
                print("ℹ️ assignment_context column already exists in assignment table")
            
            # Check if column already exists in group_assignment table
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='group_assignment' AND column_name='assignment_context'
            """))
            
            if result.fetchone() is None:
                print("Adding assignment_context column to group_assignment table...")
                db.session.execute(text("""
                    ALTER TABLE group_assignment 
                    ADD COLUMN assignment_context VARCHAR(20) DEFAULT 'homework'
                """))
                db.session.commit()
                print("✅ Added assignment_context column to group_assignment table")
            else:
                print("ℹ️ assignment_context column already exists in group_assignment table")
            
            print("\n✨ Assignment context field migration completed!")
            print("   - Default value: 'homework'")
            print("   - Valid values: 'homework', 'in-class'")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {e}")
            raise

if __name__ == '__main__':
    add_assignment_context_field()

