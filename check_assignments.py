"""
Check what assignments exist and their quarter values
"""

from app import create_app
from models import Assignment, SchoolYear

app = create_app()
with app.app_context():
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    print(f'School Year: {school_year.name}\n')
    
    # Get all assignments for this school year
    all_assignments = Assignment.query.filter_by(
        school_year_id=school_year.id
    ).all()
    
    print(f'Total Assignments: {len(all_assignments)}\n')
    
    # Group by quarter value
    quarter_counts = {}
    for a in all_assignments:
        quarter = a.quarter if a.quarter else 'None/NULL'
        quarter_counts[quarter] = quarter_counts.get(quarter, 0) + 1
    
    print('Assignments by Quarter:')
    for quarter, count in sorted(quarter_counts.items()):
        print(f'  {quarter}: {count}')
    
    print('\nSample assignments:')
    for a in all_assignments[:10]:
        quarter_val = a.quarter if a.quarter else 'None'
        class_name = a.class_info.name if a.class_info else 'Unknown'
        print(f'  - {a.title} | Quarter: {quarter_val} | Class: {class_name}')

