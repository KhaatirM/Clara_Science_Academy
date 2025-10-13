#!/usr/bin/env python3
"""
Production fix script for group assignments with missing selected_group_ids
Run this on Render shell to fix the group assignment filtering issue
"""

import os
import sys
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def fix_production_assignments():
    """Fix group assignments in production database"""
    
    # Get database URL from environment (Render sets this automatically)
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    print(f"🔧 Connecting to production database...")
    
    try:
        # Create engine and session
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if the selected_group_ids column exists
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'group_assignment' 
            AND column_name = 'selected_group_ids'
        """))
        
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            print("❌ selected_group_ids column doesn't exist in group_assignment table")
            print("🔄 Adding the column...")
            
            # Add the column
            session.execute(text("ALTER TABLE group_assignment ADD COLUMN selected_group_ids TEXT"))
            session.commit()
            print("✅ Column added successfully")
        
        # Find assignments with null selected_group_ids
        result = session.execute(text("""
            SELECT id, title, class_id 
            FROM group_assignment 
            WHERE selected_group_ids IS NULL
        """))
        
        assignments = result.fetchall()
        print(f"📝 Found {len(assignments)} assignments to fix:")
        
        fixed_count = 0
        
        for assignment_id, title, class_id in assignments:
            print(f"  📝 Assignment: {title} (ID: {assignment_id}, Class: {class_id})")
            
            # Get all active groups for this class
            result = session.execute(text("""
                SELECT id FROM student_group 
                WHERE class_id = :class_id AND is_active = true
            """), {"class_id": class_id})
            
            groups = result.fetchall()
            
            if groups:
                # Set selected_group_ids to include all groups
                group_ids = [str(group[0]) for group in groups]
                selected_group_ids_json = json.dumps(group_ids)
                
                session.execute(text("""
                    UPDATE group_assignment 
                    SET selected_group_ids = :selected_group_ids 
                    WHERE id = :assignment_id
                """), {
                    "selected_group_ids": selected_group_ids_json,
                    "assignment_id": assignment_id
                })
                
                print(f"    ✅ Set selected_group_ids to: {selected_group_ids_json}")
                fixed_count += 1
            else:
                print(f"    ⚠️  No groups found for class {class_id}")
        
        # Commit all changes
        session.commit()
        print(f"\n🎉 Successfully updated {fixed_count} assignments!")
        
        # Verify the fix
        print("\n🔍 Verifying the fix...")
        result = session.execute(text("""
            SELECT id, title, selected_group_ids 
            FROM group_assignment 
            WHERE selected_group_ids IS NOT NULL
        """))
        
        verified_assignments = result.fetchall()
        print(f"✅ {len(verified_assignments)} assignments now have selected_group_ids set")
        
        for assignment_id, title, selected_group_ids in verified_assignments:
            print(f"  📝 Assignment {assignment_id}: {title} -> {selected_group_ids}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def main():
    print("🚀 Production Group Assignment Fix Script")
    print("=" * 50)
    
    success = fix_production_assignments()
    
    if success:
        print("\n✅ Fix completed successfully!")
        print("🎯 The group assignment filtering should now work correctly.")
        print("\n📋 Next steps:")
        print("1. Test grading assignment ID 6 again")
        print("2. Check that only selected groups appear")
        print("3. The debug logs should show proper group filtering")
    else:
        print("\n❌ Fix failed!")
        print("Please check the error messages above and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
