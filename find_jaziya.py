"""
Find Jaziya/Ja'ziya Richardson/Johnson student and check their enrollment status.
"""

from app import create_app
from models import db, Student, Enrollment, Grade, Assignment, AcademicPeriod
from datetime import timedelta

app = create_app()

with app.app_context():
    print("\nSearching for student with name containing 'jaziya', 'richardson', or 'johnson'...\n")
    
    # Search for student
    students = Student.query.filter(
        db.or_(
            Student.first_name.ilike('%jaziya%'),
            Student.first_name.ilike('%ja%ziya%'),
            Student.last_name.ilike('%richardson%'),
            Student.last_name.ilike('%johnson%')
        )
    ).all()
    
    if not students:
        print("❌ Student not found. Showing all students instead:\n")
        all_students = Student.query.all()
        for s in all_students:
            print(f"  - {s.first_name} {s.last_name} (Grade {s.grade_level})")
    else:
        for student in students:
            print(f"✓ Found: {student.first_name} {student.last_name}")
            print(f"  Grade Level: {student.grade_level}")
            print(f"  Student ID: {student.student_id}")
            print()
            
            # Get their enrollments
            enrollments = Enrollment.query.filter_by(
                student_id=student.id,
                is_active=True
            ).all()
            
            print(f"  Enrolled in {len(enrollments)} classes:\n")
            
            q1 = AcademicPeriod.query.filter_by(name='Q1', period_type='quarter').first()
            
            for enrollment in enrollments:
                class_obj = enrollment.class_info
                enrolled_date = enrollment.enrolled_at.strftime('%Y-%m-%d') if enrollment.enrolled_at else 'Unknown'
                
                print(f"  📚 {class_obj.name}")
                print(f"     Enrolled: {enrolled_date}")
                
                if q1 and enrollment.enrolled_at:
                    enrolled_date_obj = enrollment.enrolled_at.date() if hasattr(enrollment.enrolled_at, 'date') else enrollment.enrolled_at
                    two_weeks_before = q1.end_date - timedelta(days=14)
                    
                    is_late = (two_weeks_before <= enrolled_date_obj <= q1.end_date) or (enrolled_date_obj > q1.end_date)
                    print(f"     Late enrollment: {'YES ⚠️' if is_late else 'No'}")
                
                # Check Q1 grades for this class
                q1_grades = Grade.query.join(Assignment).filter(
                    Grade.student_id == student.id,
                    Assignment.class_id == class_obj.id,
                    Assignment.quarter == '1'
                ).all()
                
                print(f"     Q1 Grades: {len(q1_grades)} total")
                
                if q1_grades:
                    voided = sum(1 for g in q1_grades if g.is_voided)
                    not_voided = sum(1 for g in q1_grades if not g.is_voided)
                    print(f"     - Voided: {voided}")
                    print(f"     - Not Voided: {not_voided}")
                    
                    if not_voided > 0 and is_late:
                        print(f"     ⚠️  SHOULD BE VOIDED!")
                print()

