"""
Retroactively create placeholder voided grades for all late-enrolled students.
This ensures the UI properly shows "Voided" instead of "Not Graded" for late enrollments.
"""

from app import create_app
from management_routes.late_enrollment_utils import void_assignments_for_late_enrollment
from models import db, Enrollment

app = create_app()

with app.app_context():
    print("=" * 60)
    print("RETROACTIVELY VOIDING LATE ENROLLMENT ASSIGNMENTS")
    print("=" * 60)
    
    # Get all active enrollments
    enrollments = Enrollment.query.filter_by(is_active=True).all()
    
    total_voided = 0
    students_affected = 0
    
    for enrollment in enrollments:
        print(f"\nProcessing: Student {enrollment.student_id} in Class {enrollment.class_id}")
        
        voided_count = void_assignments_for_late_enrollment(
            enrollment.student_id,
            enrollment.class_id
        )
        
        if voided_count > 0:
            students_affected += 1
            total_voided += voided_count
            print(f"  ✓ Created/updated {voided_count} voided grade records")
        else:
            print(f"  - No late enrollments to process")
    
    print("\n" + "=" * 60)
    print(f"COMPLETE!")
    print(f"  Students affected: {students_affected}")
    print(f"  Total voided grades created/updated: {total_voided}")
    print("=" * 60)

