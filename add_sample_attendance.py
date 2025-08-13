#!/usr/bin/env python3
"""
Script to add sample attendance records for testing.
"""

from app import create_app, db
from models import Attendance, Student, Class, SchoolYear
from datetime import date, timedelta
import random

def add_sample_attendance():
    """Add sample attendance records for testing."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the active school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("No active school year found.")
                return
            
            # Get existing students
            students = Student.query.all()
            if not students:
                print("No students found.")
                return
            
            # Get existing classes
            classes = Class.query.filter_by(school_year_id=school_year.id).all()
            if not classes:
                print("No classes found.")
                return
            
            print(f"Found {len(students)} students and {len(classes)} classes")
            
            # Generate attendance for the last 30 days
            attendance_added = 0
            start_date = date.today() - timedelta(days=30)
            end_date = date.today()
            
            current_date = start_date
            while current_date <= end_date:
                # Skip weekends (Saturday=5, Sunday=6)
                if current_date.weekday() < 5:
                    for student in students:
                        # Check if student is enrolled in any classes
                        from models import Enrollment
                        enrollments = Enrollment.query.filter_by(
                            student_id=student.id,
                            is_active=True
                        ).all()
                        
                        if enrollments:
                            # For each enrolled class, create attendance record
                            for enrollment in enrollments:
                                # Get a random teacher for this class
                                class_obj = enrollment.class_info
                                if class_obj.teacher:
                                    # Generate realistic attendance (mostly present)
                                    status_choices = ['Present', 'Present', 'Present', 'Tardy', 'Absent']
                                    status = random.choice(status_choices)
                                    
                                    # Create attendance record
                                    attendance = Attendance(
                                        student_id=student.id,
                                        class_id=class_obj.id,
                                        date=current_date,
                                        status=status,
                                        teacher_id=class_obj.teacher.id,
                                        notes=f"Generated for testing on {current_date}"
                                    )
                                    db.session.add(attendance)
                                    attendance_added += 1
                
                current_date += timedelta(days=1)
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully added {attendance_added} attendance records")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    add_sample_attendance()

