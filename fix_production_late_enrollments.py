#!/usr/bin/env python3
"""
Production-safe script to void grades for late enrollments.
This can be run on the production PostgreSQL server.
"""

from app import create_app
from models import Enrollment, Grade, Assignment, Student
from management_routes.late_enrollment_utils import (
    should_void_assignment_for_student,
    void_assignments_for_late_enrollment
)
from datetime import datetime

def fix_production_grades():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("FIXING LATE ENROLLMENT GRADES (Production)")
        print("=" * 70)
        print()
        
        # First, fix all enrollments without enrolled_at dates
        null_enrollments = Enrollment.query.filter(
            Enrollment.enrolled_at.is_(None)
        ).all()
        
        if null_enrollments:
            print(f"⚠️  Found {len(null_enrollments)} enrollments with NULL enrolled_at.")
            print("   Setting to current date...")
            
            for enrollment in null_enrollments:
                enrollment.enrolled_at = datetime.now()
            
            from models import db
            db.session.commit()
            print(f"✓ Fixed {len(null_enrollments)} enrollment dates.\n")
        
        # Now check all non-voided grades
        print("Checking all non-voided grades for void eligibility...")
        print()
        
        grades_to_check = Grade.query.filter_by(is_voided=False).all()
        voided_count = 0
        fixed_students = set()
        
        for grade in grades_to_check:
            try:
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
                
                # Check if should void
                if should_void_assignment_for_student(
                    grade.student_id, 
                    assignment, 
                    enrollment
                ):
                    grade.is_voided = True
                    grade.voided_at = datetime.now()
                    grade.voided_reason = (
                        f"Student enrolled late ({enrollment.enrolled_at.strftime('%Y-%m-%d')}) "
                        f"within 2 weeks of {assignment.quarter} end. "
                        f"Assignment automatically voided per late enrollment policy."
                    )
                    voided_count += 1
                    fixed_students.add(grade.student_id)
                    
                    student = Student.query.get(grade.student_id)
                    print(f"  ✓ Voided Grade {grade.id} for {student.first_name} {student.last_name}")
                    print(f"    Assignment: {assignment.title} (Q{assignment.quarter})")
                    print(f"    Enrolled: {enrollment.enrolled_at.strftime('%Y-%m-%d')}")
                    print()
            
            except Exception as e:
                print(f"  ⚠️  Error processing grade {grade.id}: {e}")
                continue
        
        if voided_count > 0:
            from models import db
            db.session.commit()
            print("=" * 70)
            print(f"✓ Successfully voided {voided_count} grade(s)")
            print(f"  Affected {len(fixed_students)} student(s)")
            print("=" * 70)
        else:
            print("=" * 70)
            print("✓ No grades needed voiding.")
            print("=" * 70)

if __name__ == "__main__":
    fix_production_grades()

