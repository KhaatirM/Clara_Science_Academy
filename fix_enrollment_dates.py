#!/usr/bin/env python3
"""
Fix enrollment dates that are NULL and void grades for late enrollments
"""

from app import create_app
from models import Enrollment, Grade, Assignment
from datetime import datetime
from management_routes.late_enrollment_utils import void_assignments_for_late_enrollment

def main():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("FIXING NULL ENROLLMENT DATES")
        print("=" * 70)
        print()
        
        # Find enrollments with NULL enrolled_at
        null_enrollments = Enrollment.query.filter(
            Enrollment.enrolled_at.is_(None)
        ).all()
        
        if null_enrollments:
            print(f"Found {len(null_enrollments)} enrollments with NULL enrolled_at dates.")
            print("Setting them to current date (this week)...\n")
            
            for enrollment in null_enrollments:
                # Set to current date (this week)
                enrollment.enrolled_at = datetime.now()
                print(f"  Fixed enrollment ID {enrollment.id} (Student {enrollment.student_id}, Class {enrollment.class_id})")
            
            from models import db
            db.session.commit()
            print(f"\n✓ Fixed {len(null_enrollments)} enrollment dates.\n")
        else:
            print("✓ No NULL enrollment dates found.\n")
        
        # Now check all enrollments and void assignments where needed
        print("=" * 70)
        print("VOIDING ASSIGNMENTS FOR LATE ENROLLMENTS")
        print("=" * 70)
        print()
        
        total_voided = 0
        
        # Get all active enrollments
        enrollments = Enrollment.query.filter_by(is_active=True).all()
        
        for enrollment in enrollments:
            if not enrollment.enrolled_at:
                # Skip if still null (shouldn't happen after above fix)
                continue
            
            voided = void_assignments_for_late_enrollment(
                enrollment.student_id,
                enrollment.class_id
            )
            
            if voided > 0:
                total_voided += voided
                print(f"  Student {enrollment.student_id}, Class {enrollment.class_id}: Voided {voided} grade(s)")
        
        if total_voided > 0:
            print(f"\n✓ Total grades voided: {total_voided}")
        else:
            print("\n✓ No grades needed voiding.")
        
        print("\n" + "=" * 70)
        print("DONE!")
        print("=" * 70)

if __name__ == "__main__":
    main()

