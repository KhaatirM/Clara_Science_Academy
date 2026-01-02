#!/usr/bin/env python3
"""
Debug script to check group assignment creation
"""
import os
import sys
import json

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import GroupAssignment, StudentGroup

def debug_assignments():
    app = create_app()
    with app.app_context():
        print("🔍 Debugging Group Assignments")
        print("=" * 50)
        
        # Get all group assignments
        assignments = GroupAssignment.query.all()
        print(f"Found {len(assignments)} group assignments:")
        
        for assignment in assignments:
            print(f"\n📝 Assignment: {assignment.title} (ID: {assignment.id})")
            print(f"   Class ID: {assignment.class_id}")
            print(f"   selected_group_ids: {assignment.selected_group_ids}")
            
            # Get groups for this class
            groups = StudentGroup.query.filter_by(class_id=assignment.class_id, is_active=True).all()
            print(f"   Available groups in class {assignment.class_id}:")
            for group in groups:
                print(f"     - Group {group.id}: {group.name} ({len(group.members)} members)")
            
            # Parse selected groups
            if assignment.selected_group_ids:
                try:
                    selected_ids = json.loads(assignment.selected_group_ids)
                    print(f"   Selected group IDs: {selected_ids}")
                    
                    # Show which groups are actually selected
                    selected_groups = [g for g in groups if str(g.id) in selected_ids]
                    print(f"   Selected groups:")
                    for group in selected_groups:
                        print(f"     - Group {group.id}: {group.name}")
                        
                except Exception as e:
                    print(f"   Error parsing selected_group_ids: {e}")
            else:
                print("   No selected_group_ids set")

if __name__ == "__main__":
    debug_assignments()
