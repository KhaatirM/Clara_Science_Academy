from app import create_app, db
from models import GroupAssignment, StudentGroup
import json

def fix_existing_group_assignments():
    app = create_app()
    with app.app_context():
        print("Fixing existing group assignments with missing selected_group_ids...")
        
        # Find all group assignments with null selected_group_ids
        assignments_to_fix = GroupAssignment.query.filter(
            GroupAssignment.selected_group_ids.is_(None)
        ).all()
        
        print(f"Found {len(assignments_to_fix)} assignments to fix")
        
        for assignment in assignments_to_fix:
            print(f"Processing assignment: {assignment.title} (ID: {assignment.id})")
            
            # Get all active groups for this assignment's class
            groups = StudentGroup.query.filter_by(
                class_id=assignment.class_id, 
                is_active=True
            ).all()
            
            if groups:
                # Set selected_group_ids to include all groups
                group_ids = [str(group.id) for group in groups]
                assignment.selected_group_ids = json.dumps(group_ids)
                print(f"  - Set selected_group_ids to: {assignment.selected_group_ids}")
            else:
                print(f"  - No groups found for class {assignment.class_id}")
        
        # Commit changes
        try:
            db.session.commit()
            print("Successfully updated all assignments!")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating assignments: {e}")

if __name__ == "__main__":
    fix_existing_group_assignments()
