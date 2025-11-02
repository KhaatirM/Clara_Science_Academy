"""
Debug script to check why quarter grades aren't being created.
Run: python debug_quarter_grades.py
"""

from app import create_app
from models import Student, Enrollment, Class, SchoolYear, Grade, Assignment, AcademicPeriod
from datetime import date
import json

app = create_app()
with app.app_context():
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    print(f'\n=== SCHOOL YEAR INFO ===')
    print(f'School Year: {school_year.name}')
    print(f'School Year ID: {school_year.id}')
    
    # Check Q1 period
    q1 = AcademicPeriod.query.filter_by(
        school_year_id=school_year.id,
        name='Q1',
        period_type='quarter'
    ).first()
    
    print(f'\n=== Q1 PERIOD ===')
    if q1:
        print(f'Q1 Period: {q1.start_date} to {q1.end_date}')
        print(f'Q1 has ended: {q1.end_date < date.today()}')
    else:
        print('Q1 period not found!')
    
    # Check enrollments
    enrollments = Enrollment.query.join(Class).filter(
        Class.school_year_id == school_year.id
    ).all()
    print(f'\n=== ENROLLMENTS ===')
    print(f'Total enrollments: {len(enrollments)}')
    
    # Check Q1 assignments
    q1_assignments = Assignment.query.filter_by(
        school_year_id=school_year.id,
        quarter='Q1'
    ).all()
    print(f'\n=== Q1 ASSIGNMENTS ===')
    print(f'Total Q1 Assignments: {len(q1_assignments)}')
    
    if q1_assignments:
        print('Sample Q1 assignments:')
        for a in q1_assignments[:5]:
            print(f'  - {a.title} (Class: {a.class_info.name if a.class_info else "Unknown"})')
    
    # Check Q1 grades
    q1_grades = Grade.query.join(Assignment).filter(
        Assignment.school_year_id == school_year.id,
        Assignment.quarter == 'Q1',
        Grade.is_voided == False
    ).all()
    print(f'\n=== Q1 GRADES ===')
    print(f'Total Q1 Grades (non-voided): {len(q1_grades)}')
    
    if q1_grades:
        print('Sample Q1 grades:')
        for g in q1_grades[:5]:
            student_name = g.student.name if g.student else 'Unknown'
            assignment_name = g.assignment.title if g.assignment else 'Unknown'
            print(f'  - {student_name}: {assignment_name}')
    
    # Check a specific student's Q1 data
    print(f'\n=== SAMPLE STUDENT ANALYSIS ===')
    if enrollments:
        sample_enrollment = enrollments[0]
        student = sample_enrollment.student
        class_obj = sample_enrollment.class_info
        
        print(f'Student: {student.name}')
        print(f'Class: {class_obj.name}')
        print(f'Enrollment Date: {sample_enrollment.enrolled_at}')
        
        if q1:
            enrolled_date = sample_enrollment.enrolled_at.date() if hasattr(sample_enrollment.enrolled_at, 'date') else sample_enrollment.enrolled_at
            print(f'Enrolled before Q1 ended: {enrolled_date <= q1.end_date if enrolled_date else "Unknown"}')
        
        # Check their Q1 grades
        student_q1_grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student.id,
            Assignment.class_id == class_obj.id,
            Assignment.quarter == 'Q1',
            Grade.is_voided == False
        ).all()
        
        print(f'Q1 grades for this student in this class: {len(student_q1_grades)}')
        
        if student_q1_grades:
            scores = []
            for g in student_q1_grades:
                try:
                    gd = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
                    if 'score' in gd and gd['score'] is not None:
                        scores.append(gd['score'])
                        print(f'  Assignment: {g.assignment.title} - Score: {gd["score"]}')
                except Exception as e:
                    print(f'  Error parsing grade: {e}')
            
            if scores:
                avg = sum(scores) / len(scores)
                print(f'  Average: {avg:.2f}')
            else:
                print('  No valid scores found in grade_data')
    else:
        print('No enrollments found!')
    
    print('\n=== DIAGNOSIS ===')
    if not q1:
        print('❌ Q1 period not configured in database')
    elif q1.end_date >= date.today():
        print('❌ Q1 has not ended yet')
    elif len(enrollments) == 0:
        print('❌ No students enrolled in any classes')
    elif len(q1_assignments) == 0:
        print('❌ No assignments marked for Q1')
    elif len(q1_grades) == 0:
        print('❌ No grades recorded for Q1 assignments')
    else:
        print('✓ Data looks good - quarter grades should be created')
        print('  Possible issue: Enrollment dates might be after Q1 ended')

