"""
Debug why late enrollment voiding isn't working.
"""

from app import create_app
from models import Enrollment, Grade, Assignment, AcademicPeriod, Student, Class
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("LATE ENROLLMENT DEBUG")
    print("="*60 + "\n")
    
    # Get Q1 period
    q1 = AcademicPeriod.query.filter_by(
        name='Q1',
        period_type='quarter'
    ).first()
    
    if q1:
        print(f"Q1 Period: {q1.start_date} to {q1.end_date}")
        two_weeks_before = q1.end_date - timedelta(days=14)
        print(f"Late enrollment window: {two_weeks_before} to {q1.end_date}")
        print()
    
    # Check for late enrollments
    enrollments = Enrollment.query.filter_by(is_active=True).all()
    
    print(f"Total enrollments: {len(enrollments)}\n")
    
    late_enrollments = []
    
    for enrollment in enrollments:
        if enrollment.enrolled_at and q1:
            enrolled_date = enrollment.enrolled_at.date() if hasattr(enrollment.enrolled_at, 'date') else enrollment.enrolled_at
            
            # Check if late
            if two_weeks_before <= enrolled_date <= q1.end_date or enrolled_date > q1.end_date:
                student = enrollment.student
                class_obj = enrollment.class_info
                
                if not student or not class_obj:
                    continue
                
                student_name = f"{student.first_name} {student.last_name}"
                
                # Check if they have Q1 grades
                q1_grades = Grade.query.join(Assignment).filter(
                    Grade.student_id == student.id,
                    Assignment.class_id == class_obj.id,
                    Assignment.quarter == '1'  # or 'Q1'
                ).all()
                
                voided = [g for g in q1_grades if g.is_voided]
                not_voided = [g for g in q1_grades if not g.is_voided]
                
                late_enrollments.append({
                    'student': student_name,
                    'class': class_obj.name,
                    'enrolled': enrolled_date,
                    'total_q1_grades': len(q1_grades),
                    'voided': len(voided),
                    'not_voided': len(not_voided)
                })
    
    print(f"Late enrollments found: {len(late_enrollments)}\n")
    
    if late_enrollments:
        print("Details:")
        for item in late_enrollments[:10]:  # Show first 10
            print(f"\n  Student: {item['student']}")
            print(f"  Class: {item['class']}")
            print(f"  Enrolled: {item['enrolled']}")
            print(f"  Q1 Grades: {item['total_q1_grades']} total, {item['voided']} voided, {item['not_voided']} NOT voided")
            
            if item['not_voided'] > 0:
                print(f"  ⚠️  HAS {item['not_voided']} GRADES THAT SHOULD BE VOIDED!")
    else:
        print("No late enrollments detected.")
        print("\nPossible reasons:")
        print("1. All students enrolled before the 2-week window")
        print("2. Students don't have grades in Q1 assignments yet")
        print("3. Quarter value mismatch (checking '1' vs 'Q1')")
    
    # Check assignment quarter values
    print("\n" + "="*60)
    print("ASSIGNMENT QUARTER VALUES")
    print("="*60 + "\n")
    
    sample_assignments = Assignment.query.limit(10).all()
    print("Sample assignments and their quarter values:")
    for a in sample_assignments:
        print(f"  - {a.title[:40]}: quarter='{a.quarter}'")
