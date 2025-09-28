#!/usr/bin/env python3
"""
Script to add sample class schedules and enrollments for testing the student dashboard.
"""

from app import create_app, db
from models import Class, ClassSchedule, Student, Enrollment, SchoolYear
from datetime import time

def add_sample_schedules():
    """Add sample class schedules and enrollments."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the active school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("No active school year found. Please create one first.")
                return
            
            # Get existing classes
            classes = Class.query.filter_by(school_year_id=school_year.id).all()
            if not classes:
                print("No classes found. Please create classes first.")
                return
            
            # Get existing students
            students = Student.query.all()
            if not students:
                print("No students found. Please create students first.")
                return
            
            print(f"Found {len(classes)} classes and {len(students)} students")
            
            # Add sample schedules for each class
            schedules_added = 0
            for i, class_obj in enumerate(classes):
                # Create a schedule for Monday (0) and Wednesday (2)
                for day in [0, 2]:  # Monday and Wednesday
                    # Different times for different classes
                    start_hour = 8 + (i * 2) % 6  # Spread classes throughout the day
                    start_time = time(start_hour, 0)  # 8:00 AM, 10:00 AM, etc.
                    end_time = time(start_hour + 1, 0)  # 1 hour classes
                    
                    # Check if schedule already exists
                    existing = ClassSchedule.query.filter_by(
                        class_id=class_obj.id,
                        day_of_week=day
                    ).first()
                    
                    if not existing:
                        schedule = ClassSchedule(
                            class_id=class_obj.id,
                            day_of_week=day,
                            start_time=start_time,
                            end_time=end_time,
                            room=f"Room {100 + i}",
                            is_active=True
                        )
                        db.session.add(schedule)
                        schedules_added += 1
                        print(f"Added schedule for {class_obj.name} on day {day}: {start_time}-{end_time}")
            
            # Add sample enrollments for students
            enrollments_added = 0
            for i, student in enumerate(students):
                # Enroll each student in 2-3 classes
                classes_to_enroll = classes[i % len(classes):(i % len(classes)) + 2]
                if len(classes_to_enroll) < 2:
                    classes_to_enroll.extend(classes[:2 - len(classes_to_enroll)])
                
                for class_obj in classes_to_enroll:
                    # Check if enrollment already exists
                    existing = Enrollment.query.filter_by(
                        student_id=student.id,
                        class_id=class_obj.id
                    ).first()
                    
                    if not existing:
                        enrollment = Enrollment(
                            student_id=student.id,
                            class_id=class_obj.id,
                            is_active=True
                        )
                        db.session.add(enrollment)
                        enrollments_added += 1
                        print(f"Enrolled {student.first_name} {student.last_name} in {class_obj.name}")
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully added {schedules_added} schedules and {enrollments_added} enrollments")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    add_sample_schedules()

