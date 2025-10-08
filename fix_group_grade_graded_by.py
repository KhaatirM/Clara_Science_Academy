#!/usr/bin/env python3
"""
Fix group_grade table to allow NULL values in graded_by column
This allows administrators to grade group assignments without having a teacher_staff record
"""

from app import create_app
from models import db
from sqlalchemy import text

def fix_group_grade_table():
    """Make graded_by column nullable in group_grade table"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Checking group_grade table structure...")
            
            # Check if the table exists
            check_table = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'group_grade'
                );
            """)
            
            result = db.session.execute(check_table).scalar()
            
            if not result:
                print("❌ group_grade table does not exist. Skipping migration.")
                return
            
            print("✓ group_grade table exists")
            
            # Check current constraint on graded_by
            check_constraint = text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'group_grade' 
                AND column_name = 'graded_by';
            """)
            
            is_nullable = db.session.execute(check_constraint).scalar()
            
            if is_nullable == 'YES':
                print("✓ graded_by column is already nullable. No changes needed.")
                return
            
            print(f"Current graded_by nullable status: {is_nullable}")
            print("Making graded_by column nullable...")
            
            # Make graded_by nullable
            alter_column = text("""
                ALTER TABLE group_grade 
                ALTER COLUMN graded_by DROP NOT NULL;
            """)
            
            db.session.execute(alter_column)
            db.session.commit()
            
            print("✓ Successfully made graded_by column nullable")
            print("\nVerifying change...")
            
            # Verify the change
            is_nullable_after = db.session.execute(check_constraint).scalar()
            print(f"✓ graded_by nullable status after change: {is_nullable_after}")
            
            if is_nullable_after == 'YES':
                print("\n✅ Migration completed successfully!")
                print("Administrators can now grade group assignments without errors.")
            else:
                print("\n⚠️ Warning: Column may not have been updated correctly.")
                
        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    fix_group_grade_table()
