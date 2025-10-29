#!/usr/bin/env python3
"""
Script to retroactively void grades for students who enrolled late.
Run this to fix existing grades that should be voided.
"""

from app import create_app
from management_routes.late_enrollment_utils import check_and_void_existing_enrollments, void_assignments_for_late_enrollment
from models import Enrollment, Grade
from datetime import datetime

def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Late Enrollment Grade Voiding Script")
        print("=" * 60)
        print()
        
        # Option 1: Process all enrollments
        print("Processing all existing enrollments...")
        results = check_and_void_existing_enrollments()
        
        if results:
            print(f"\n✓ Processed {len(results)} students with late enrollments:")
            for key, data in results.items():
                print(f"  - Student {data['student_id']}, Class {data['class_id']}: {data['voided_count']} grades voided")
        else:
            print("\n✓ No late enrollments found that require voiding.")
        
        # Option 2: Also check all existing grades and void if needed
        print("\nChecking all existing grades for void eligibility...")
        voided_count = 0
        grades = Grade.query.filter_by(is_voided=False).all()
        
        for grade in grades:
            from management_routes.late_enrollment_utils import check_and_void_grade
            if check_and_void_grade(grade):
                voided_count += 1
        
        if voided_count > 0:
            print(f"\n✓ Voided {voided_count} additional grades that should have been voided.")
        else:
            print("\n✓ No additional grades need to be voided.")
        
        print("\n" + "=" * 60)
        print("Script completed successfully!")
        print("=" * 60)

if __name__ == "__main__":
    main()

