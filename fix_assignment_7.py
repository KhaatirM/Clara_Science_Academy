#!/usr/bin/env python3
"""
Fix Assignment 7 to only have group 1 selected
Run this in Render shell
"""

import os
import json
from sqlalchemy import create_engine, text

def fix_assignment_7():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        print("🔧 Fixing Assignment 7 to only select group 1")
        
        # Update assignment 7 to only have group 1 selected
        conn.execute(text("""
            UPDATE group_assignment 
            SET selected_group_ids = :sids 
            WHERE id = 7
        """), {"sids": '["1"]'})
        
        conn.commit()
        
        # Verify the fix
        result = conn.execute(text("""
            SELECT id, title, selected_group_ids 
            FROM group_assignment 
            WHERE id = 7
        """))
        
        assignment = result.fetchone()
        if assignment:
            print(f"✅ Updated Assignment {assignment[0]}: {assignment[1]} -> {assignment[2]}")
            
            # Show which groups are available for this class
            result = conn.execute(text("""
                SELECT id, name 
                FROM student_group 
                WHERE class_id = (SELECT class_id FROM group_assignment WHERE id = 7) 
                AND is_active = true
            """))
            
            groups = result.fetchall()
            print(f"\n📋 Available groups in this class:")
            for group_id, group_name in groups:
                print(f"  - Group {group_id}: {group_name}")
            
            return True
        else:
            print("❌ Assignment 7 not found")
            return False

if __name__ == "__main__":
    success = fix_assignment_7()
    if success:
        print("\n🎉 Assignment 7 fixed! Now test grading it.")
    else:
        print("\n❌ Fix failed!")

