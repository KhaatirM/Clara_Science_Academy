#!/usr/bin/env python3
"""
Debug all enrollments to find the issue
"""

from app import create_app
from models import Student, Enrollment, Grade, Assignment, AcademicPeriod
from datetime import datetime, timedelta
from management_routes.late_enrollment_utils import (
    is_late_enrollment, 
    get_academic_period_for_assignment,
    should_void_assignment_for_student,
    void_assignments_for_late_enrollment
)

def main():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("CHECKING ALL ENROLLMENTS FOR VOIDING ISSUES")
        print("=" * 70)
        print()
        
        # Get all active enrollments
        enrollments = Enrollment.query.filter_by(is_active=True).all()
        print(f"Total active enrollments: {len(enrollments)}\n")
        
        # Check enrollments with missing enrolled_at
        missing_dates = [e for e in enrollments if not e.enrolled_at]
        if missing_dates:
            print(f"⚠️  Found {len(missing_dates)} enrollments with NULL enrolled_at dates!")
            print("   These need to have enrolled_at set manually.\n")
        
        # Check recent enrollments (last month)
        month_ago = datetime.now() - timedelta(days=30)
        recent = [e for e in enrollments if e.enrolled_at and e.enrolled_at >= month_ago]
        print(f"Enrollments in last 30 days: {len(recent)}\n")
        
        for enrollment in recent[:10]:  # Show first 10
            student = Student.query.get(enrollment.student_id)
            print(f"Student ID {enrollment.student_id}: {student.first_name} {student.last_name if student else 'Unknown'}")
            print(f"  Class ID: {enrollment.class_id}")
            print(f"  Enrolled: {enrollment.enrolled_at}")
            
            # Check if assignments should be voided
            voided = void_assignments_for_late_enrollment(
                enrollment.student_id,
                enrollment.class_id
            )
            print(f"  Voided grades: {voided}")
            print()
        
        # Also check for grades that should be voided but aren't
        print("\n" + "=" * 70)
        print("CHECKING GRADES THAT SHOULD BE VOIDED")
        print("=" * 70)
        print()
        
        all_grades = Grade.query.filter_by(is_voided=False).limit(100).all()
        should_void_count = 0
        
        for grade in all_grades:
            assignment = Assignment.query.get(grade.assignment_id)
            if not assignment:
                continue
            
            enrollment = Enrollment.query.filter_by(
                student_id=grade.student_id,
                class_id=assignment.class_id,
                is_active=True
            ).first()
            
            if not enrollment or not enrollment.enrolled_at:
                continue
            
            if should_void_assignment_for_student(grade.student_id, assignment, enrollment):
                should_void_count += 1
                student = Student.query.get(grade.student_id)
                print(f"⚠️  Grade {grade.id} for {student.first_name} {student.last_name}")
                print(f"    Assignment: {assignment.title} (Q{assignment.quarter})")
                print(f"    Enrolled: {enrollment.enrolled_at}")
                print(f"    Should be voided but isn't!")
                print()
        
        print(f"\nTotal grades that should be voided: {should_void_count}")
        
        if should_void_count > 0:
            print("\nRun void_late_enrollment_grades.py to fix these!")

if __name__ == "__main__":
    main()

