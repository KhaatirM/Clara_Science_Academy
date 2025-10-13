"""
Commands to run directly in Render shell to fix group assignments

Copy and paste these commands one by one into the Render shell:

1. First, check current assignments:
"""

# Command 1: Check current assignments
check_assignments = """
python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, title, selected_group_ids FROM group_assignment'))
    assignments = result.fetchall()
    print('Current assignments:')
    for a in assignments:
        print(f'  ID: {a[0]}, Title: {a[1]}, selected_group_ids: {a[2]}')
"
"""

# Command 2: Add column if missing
add_column = """
python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE group_assignment ADD COLUMN selected_group_ids TEXT'))
        conn.commit()
        print('Column added successfully')
    except Exception as e:
        print(f'Column may already exist: {e}')
"
"""

# Command 3: Fix assignments
fix_assignments = """
python3 -c "
import os
import json
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    # Get assignments with null selected_group_ids
    result = conn.execute(text('SELECT id, title, class_id FROM group_assignment WHERE selected_group_ids IS NULL'))
    assignments = result.fetchall()
    print(f'Found {len(assignments)} assignments to fix')
    
    for assignment_id, title, class_id in assignments:
        print(f'Fixing assignment: {title} (ID: {assignment_id})')
        
        # Get groups for this class
        result = conn.execute(text('SELECT id FROM student_group WHERE class_id = :class_id AND is_active = true'), {'class_id': class_id})
        groups = result.fetchall()
        
        if groups:
            group_ids = [str(group[0]) for group in groups]
            selected_group_ids_json = json.dumps(group_ids)
            
            conn.execute(text('UPDATE group_assignment SET selected_group_ids = :selected_group_ids WHERE id = :assignment_id'), {
                'selected_group_ids': selected_group_ids_json,
                'assignment_id': assignment_id
            })
            print(f'  Set selected_group_ids to: {selected_group_ids_json}')
    
    conn.commit()
    print('All assignments fixed!')
"
"""

# Command 4: Verify the fix
verify_fix = """
python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, title, selected_group_ids FROM group_assignment'))
    assignments = result.fetchall()
    print('Updated assignments:')
    for a in assignments:
        print(f'  ID: {a[0]}, Title: {a[1]}, selected_group_ids: {a[2]}')
"
"""

print("Copy and paste these commands into Render shell:")
print("\n1. Check current assignments:")
print(check_assignments)
print("\n2. Add column if missing:")
print(add_column)
print("\n3. Fix assignments:")
print(fix_assignments)
print("\n4. Verify the fix:")
print(verify_fix)
