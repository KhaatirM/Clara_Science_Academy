#!/usr/bin/env python3
"""
Migration script to create the new group-related tables.
Run this script to add the new tables to your database.
"""

from app import create_app, db
from models import StudentGroup, StudentGroupMember, GroupAssignment, GroupSubmission, GroupGrade

def create_group_tables():
    """Create the new group-related tables."""
    app = create_app()
    with app.app_context():
        try:
            # Create all the new tables
            db.create_all()
            print("✅ Successfully created group-related tables:")
            print("   - student_group")
            print("   - student_group_member") 
            print("   - group_assignment")
            print("   - group_submission")
            print("   - group_grade")
            print("\n🎉 Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting group tables migration...")
    print("This will create the following new tables:")
    print("   - student_group (for managing student groups)")
    print("   - student_group_member (for group membership)")
    print("   - group_assignment (for group assignments)")
    print("   - group_submission (for group submissions)")
    print("   - group_grade (for group assignment grades)")
    print()
    
    confirm = input("Do you want to proceed? (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        create_group_tables()
    else:
        print("❌ Migration cancelled.")
