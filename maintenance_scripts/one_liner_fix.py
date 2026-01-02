"""
ONE-LINER FIX for Render Shell

Copy and paste this single command into the Render shell:

python3 -c "
import os, json
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE group_assignment ADD COLUMN selected_group_ids TEXT'))
        print('Column added (or already exists)')
    except: pass
    
    result = conn.execute(text('SELECT id, title, class_id FROM group_assignment WHERE selected_group_ids IS NULL'))
    assignments = result.fetchall()
    print(f'Fixing {len(assignments)} assignments...')
    
    for aid, title, cid in assignments:
        result = conn.execute(text('SELECT id FROM student_group WHERE class_id = :cid AND is_active = true'), {'cid': cid})
        groups = result.fetchall()
        if groups:
            gids = json.dumps([str(g[0]) for g in groups])
            conn.execute(text('UPDATE group_assignment SET selected_group_ids = :gids WHERE id = :aid'), {'gids': gids, 'aid': aid})
            print(f'Fixed: {title} -> {gids}')
    
    conn.commit()
    print('✅ All assignments fixed!')
"
"""

print("Copy this ONE command into Render shell:")
print("=" * 80)
exec(open(__file__).read().split('"""')[1])
print("=" * 80)
