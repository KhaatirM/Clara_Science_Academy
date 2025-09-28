#!/usr/bin/env python3
"""
Script to add sample assignments and grades for testing.
"""

from app import create_app, db
from models import Assignment, Submission, Grade, Class, Student, SchoolYear
from datetime import datetime, timedelta
import json

def add_sample_assignments():
    """Add sample assignments and grades for testing."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the active school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("No active school year found.")
                return
            
            # Get existing classes
            classes = Class.query.filter_by(school_year_id=school_year.id).all()
            if not classes:
                print("No classes found.")
                return
            
            # Get existing students
            students = Student.query.all()
            if not students:
                print("No students found.")
                return
            
            print(f"Found {len(classes)} classes and {len(students)} students")
            
            # Sample assignments for each class
            assignments_added = 0
            submissions_added = 0
            grades_added = 0
            
            for class_obj in classes:
                # Create 3-4 assignments per class
                for i in range(3):
                    # Different due dates (past, recent, future)
                    if i == 0:
                        due_date = datetime.now() - timedelta(days=30)  # Past due
                    elif i == 1:
                        due_date = datetime.now() - timedelta(days=7)   # Recent
                    else:
                        due_date = datetime.now() + timedelta(days=7)   # Future
                    
                    assignment = Assignment(
                        title=f"{class_obj.name} Assignment {i+1}",
                        description=f"This is assignment {i+1} for {class_obj.name}",
                        class_id=class_obj.id,
                        due_date=due_date,
                        quarter="Q1",
                        school_year_id=school_year.id,
                        is_locked=False
                    )
                    db.session.add(assignment)
                    db.session.flush()  # Get the ID
                    assignments_added += 1
                    
                    # Create submissions and grades for each student
                    for student in students:
                        # Check if student is enrolled in this class
                        from models import Enrollment
                        enrollment = Enrollment.query.filter_by(
                            student_id=student.id,
                            class_id=class_obj.id,
                            is_active=True
                        ).first()
                        
                        if enrollment:
                            # Create submission
                            submission = Submission(
                                student_id=student.id,
                                assignment_id=assignment.id,
                                submitted_at=due_date - timedelta(days=1),
                                comments=f"Submitted by {student.first_name}"
                            )
                            db.session.add(submission)
                            db.session.flush()
                            submissions_added += 1
                            
                            # Create grade (only for past assignments)
                            if due_date < datetime.now():
                                # Generate a realistic grade (70-100)
                                import random
                                score = random.randint(70, 100)
                                
                                grade_data = {
                                    'score': score,
                                    'comments': f'Good work on {assignment.title}',
                                    'graded_by': 'teacher'
                                }
                                
                                grade = Grade(
                                    student_id=student.id,
                                    assignment_id=assignment.id,
                                    grade_data=json.dumps(grade_data),
                                    graded_at=due_date
                                )
                                db.session.add(grade)
                                grades_added += 1
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully added:")
            print(f"- {assignments_added} assignments")
            print(f"- {submissions_added} submissions")
            print(f"- {grades_added} grades")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    add_sample_assignments()

