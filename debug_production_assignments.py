#!/usr/bin/env python3
"""
Production debug script for group assignments
Run this on Render shell to check assignment data
"""

import os
import json
from sqlalchemy import create_engine, text

def debug_production():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        print("🔍 Debugging Production Group Assignments")
        print("=" * 50)
        
        # Get all group assignments
        result = conn.execute(text("SELECT id, title, class_id, selected_group_ids FROM group_assignment"))
        assignments = result.fetchall()
        
        print(f"Found {len(assignments)} group assignments:")
        
        for assignment_id, title, class_id, selected_group_ids in assignments:
            print(f"\n📝 Assignment: {title} (ID: {assignment_id})")
            print(f"   Class ID: {class_id}")
            print(f"   selected_group_ids: {selected_group_ids}")
            
            # Get groups for this class
            result = conn.execute(text("""
                SELECT id, name, description 
                FROM student_group 
                WHERE class_id = :class_id AND is_active = true
            """), {"class_id": class_id})
            
            groups = result.fetchall()
            print(f"   Available groups in class {class_id}:")
            for group_id, group_name, group_desc in groups:
                print(f"     - Group {group_id}: {group_name}")
            
            # Parse selected groups
            if selected_group_ids:
                try:
                    selected_ids = json.loads(selected_group_ids)
                    print(f"   Selected group IDs: {selected_ids}")
                    
                    # Show which groups are actually selected
                    selected_groups = [g for g in groups if str(g[0]) in selected_ids]
                    print(f"   Selected groups:")
                    for group_id, group_name, group_desc in selected_groups:
                        print(f"     - Group {group_id}: {group_name}")
                        
                except Exception as e:
                    print(f"   Error parsing selected_group_ids: {e}")
            else:
                print("   No selected_group_ids set")

if __name__ == "__main__":
    debug_production()
