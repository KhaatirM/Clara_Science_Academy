"""
Script to backfill created_by field for existing assignments.
For assignments without a creator, this script will set the creator to the class teacher.
This provides a reasonable default for historical assignments.
"""

from app import create_app, db
from models import Assignment, GroupAssignment, Class, TeacherStaff, User
from sqlalchemy import text, inspect

def check_and_add_created_by_column():
    """Check if created_by column exists and add it if missing."""
    inspector = inspect(db.engine)
    
    # Check assignment table
    assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
    if 'created_by' not in assignment_columns:
        print("Adding 'created_by' column to assignment table...")
        db.session.execute(text("ALTER TABLE assignment ADD COLUMN created_by INTEGER"))
        db.session.commit()
        print("✓ Added 'created_by' column to assignment table")
    
    # Check group_assignment table
    group_assignment_columns = [col['name'] for col in inspector.get_columns('group_assignment')]
    if 'created_by' not in group_assignment_columns:
        print("Adding 'created_by' column to group_assignment table...")
        db.session.execute(text("ALTER TABLE group_assignment ADD COLUMN created_by INTEGER"))
        db.session.commit()
        print("✓ Added 'created_by' column to group_assignment table")

def backfill_creators():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("BACKFILLING ASSIGNMENT CREATORS")
        print("=" * 70)
        
        # First, ensure the created_by column exists
        try:
            check_and_add_created_by_column()
        except Exception as e:
            print(f"Note: Could not check/add created_by column (may already exist): {e}")
        
        # Process regular assignments
        print("\n[1] Processing regular assignments...")
        assignments = Assignment.query.filter(Assignment.created_by.is_(None)).all()
        
        updated_count = 0
        skipped_count = 0
        
        for assignment in assignments:
            # Get the class and its teacher
            class_obj = assignment.class_info
            if class_obj and class_obj.teacher_id:
                # Get the teacher's user account
                teacher = db.session.get(TeacherStaff, class_obj.teacher_id)
                if teacher:
                    # Find the user account associated with this teacher
                    user = User.query.filter_by(teacher_staff_id=teacher.id).first()
                    if user:
                        assignment.created_by = user.id
                        updated_count += 1
                        print(f"  Updated assignment {assignment.id} ({assignment.title[:50]}): Set creator to {teacher.first_name} {teacher.last_name}")
                    else:
                        skipped_count += 1
                        print(f"  Skipped assignment {assignment.id}: Teacher {teacher.first_name} {teacher.last_name} has no user account")
                else:
                    skipped_count += 1
                    print(f"  Skipped assignment {assignment.id}: Class has no teacher")
            else:
                skipped_count += 1
                print(f"  Skipped assignment {assignment.id}: Class not found or has no teacher")
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✓ Updated {updated_count} regular assignments")
        else:
            print("  No regular assignments needed updating")
        
        if skipped_count > 0:
            print(f"  ⚠ Skipped {skipped_count} assignments (no teacher/user found)")
        
        # Process group assignments
        print("\n[2] Processing group assignments...")
        group_assignments = GroupAssignment.query.filter(GroupAssignment.created_by.is_(None)).all()
        
        group_updated_count = 0
        group_skipped_count = 0
        
        for assignment in group_assignments:
            # Get the class and its teacher
            class_obj = assignment.class_info
            if class_obj and class_obj.teacher_id:
                # Get the teacher's user account
                teacher = db.session.get(TeacherStaff, class_obj.teacher_id)
                if teacher:
                    # Find the user account associated with this teacher
                    user = User.query.filter_by(teacher_staff_id=teacher.id).first()
                    if user:
                        assignment.created_by = user.id
                        group_updated_count += 1
                        print(f"  Updated group assignment {assignment.id} ({assignment.title[:50]}): Set creator to {teacher.first_name} {teacher.last_name}")
                    else:
                        group_skipped_count += 1
                        print(f"  Skipped group assignment {assignment.id}: Teacher {teacher.first_name} {teacher.last_name} has no user account")
                else:
                    group_skipped_count += 1
                    print(f"  Skipped group assignment {assignment.id}: Class has no teacher")
            else:
                group_skipped_count += 1
                print(f"  Skipped group assignment {assignment.id}: Class not found or has no teacher")
        
        if group_updated_count > 0:
            db.session.commit()
            print(f"\n✓ Updated {group_updated_count} group assignments")
        else:
            print("  No group assignments needed updating")
        
        if group_skipped_count > 0:
            print(f"  ⚠ Skipped {group_skipped_count} group assignments (no teacher/user found)")
        
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✓ Updated {updated_count} regular assignments")
        print(f"✓ Updated {group_updated_count} group assignments")
        print(f"⚠ Skipped {skipped_count + group_skipped_count} assignments (no teacher/user found)")
        print("\nNote: Assignments that were skipped will continue to show the class teacher")
        print("name in the interface (via fallback logic in the template).")

if __name__ == '__main__':
    backfill_creators()

