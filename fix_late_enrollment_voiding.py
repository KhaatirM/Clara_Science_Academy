"""
Fix late enrollment voiding for all existing enrollments.
Run this on Render to retroactively void assignments for late-enrolled students.

Usage: python fix_late_enrollment_voiding.py
"""

from app import create_app
from management_routes.late_enrollment_utils import void_assignments_for_late_enrollment
from models import Enrollment, Student, Class, Grade
from datetime import datetime

app = create_app()

with app.app_context():
    print("=" * 60)
    print("LATE ENROLLMENT VOIDING FIX")
    print("=" * 60)
    print()
    
    # Get all active enrollments
    enrollments = Enrollment.query.filter_by(is_active=True).all()
    
    print(f"Found {len(enrollments)} active enrollments to check\n")
    
    total_voided = 0
    students_affected = []
    
    for enrollment in enrollments:
        if enrollment.student and enrollment.class_info:
            student_name = f"{enrollment.student.first_name} {enrollment.student.last_name}"
            class_name = enrollment.class_info.name
            enrolled_date = enrollment.enrolled_at.strftime('%Y-%m-%d') if enrollment.enrolled_at else 'Unknown'
            
            # Run the voiding function
            voided_count = void_assignments_for_late_enrollment(
                enrollment.student_id,
                enrollment.class_id
            )
            
            if voided_count > 0:
                total_voided += voided_count
                students_affected.append({
                    'student': student_name,
                    'class': class_name,
                    'enrolled': enrolled_date,
                    'voided': voided_count
                })
                print(f"✓ {student_name} ({class_name})")
                print(f"  Enrolled: {enrolled_date}")
                print(f"  Voided: {voided_count} assignment(s)")
                print()
    
    print("=" * 60)
    print(f"SUMMARY")
    print("=" * 60)
    print(f"Total enrollments checked: {len(enrollments)}")
    print(f"Students affected: {len(students_affected)}")
    print(f"Total assignments voided: {total_voided}")
    print()
    
    if students_affected:
        print("Students with voided assignments:")
        for item in students_affected:
            print(f"  - {item['student']} in {item['class']}: {item['voided']} voided")
    else:
        print("No late enrollments found that needed voiding")
    
    print()
    print("✓ Complete!")


