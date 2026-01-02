#!/usr/bin/env python3
"""
Unified Sample Data Manager

This script consolidates all sample data creation functionality into a single,
manageable system. It replaces multiple individual sample data scripts.
"""

from app import create_app, db
from models import (
    SchoolYear, TeacherStaff, Class, Student, Assignment, 
    Announcement, Notification, Attendance, CalendarEvent,
    AcademicPeriod, User, Enrollment
)
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random

class SampleDataManager:
    """Manages all sample data creation for the application."""
    
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_context.pop()
    
    def create_school_year(self):
        """Create a sample school year."""
        print("Creating sample school year...")
        
        # Check if school year already exists
        existing_year = SchoolYear.query.filter_by(is_active=True).first()
        if existing_year:
            print(f"Active school year already exists: {existing_year.name}")
            return existing_year
        
        # Create new school year
        school_year = SchoolYear(
            name="2024-2025",
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
            is_active=True
        )
        db.session.add(school_year)
        db.session.commit()
        
        print(f"Created school year: {school_year.name}")
        return school_year
    
    def create_academic_periods(self, school_year_id):
        """Create academic periods for a school year."""
        print("Creating academic periods...")
        
        # Create quarters
        quarters = [
            ('Q1', date(2024, 9, 1), date(2024, 11, 15)),
            ('Q2', date(2024, 11, 16), date(2025, 2, 14)),
            ('Q3', date(2025, 2, 15), date(2025, 4, 25)),
            ('Q4', date(2025, 4, 26), date(2025, 6, 30))
        ]
        
        for name, start_date, end_date in quarters:
            period = AcademicPeriod(
                school_year_id=school_year_id,
                name=name,
                period_type='quarter',
                start_date=start_date,
                end_date=end_date,
                is_active=True
            )
            db.session.add(period)
        
        db.session.commit()
        print("Created 4 academic quarters")
    
    def create_teachers(self):
        """Create sample teachers and staff."""
        print("Creating sample teachers...")
        
        # Check if teachers already exist
        existing_teachers = TeacherStaff.query.count()
        if existing_teachers > 0:
            print(f"Teachers already exist ({existing_teachers} found)")
            return TeacherStaff.query.all()
        
        teachers_data = [
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@school.edu',
                'phone': '555-0101',
                'subject': 'Mathematics',
                'role': 'Teacher'
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@school.edu',
                'phone': '555-0102',
                'subject': 'English',
                'role': 'Teacher'
            },
            {
                'first_name': 'Michael',
                'last_name': 'Brown',
                'email': 'michael.brown@school.edu',
                'phone': '555-0103',
                'subject': 'Science',
                'role': 'Teacher'
            },
            {
                'first_name': 'Emily',
                'last_name': 'Davis',
                'email': 'emily.davis@school.edu',
                'phone': '555-0104',
                'subject': 'History',
                'role': 'Teacher'
            }
        ]
        
        teachers = []
        for teacher_data in teachers_data:
            teacher = TeacherStaff(**teacher_data)
            db.session.add(teacher)
            teachers.append(teacher)
        
        db.session.commit()
        print(f"Created {len(teachers)} teachers")
        return teachers
    
    def create_classes(self, school_year, teachers):
        """Create sample classes."""
        print("Creating sample classes...")
        
        # Check if classes already exist
        existing_classes = Class.query.count()
        if existing_classes > 0:
            print(f"Classes already exist ({existing_classes} found)")
            return Class.query.all()
        
        classes_data = [
            {
                'name': 'Algebra I',
                'subject': 'Mathematics',
                'grade_level': '9',
                'room_number': '101',
                'schedule': 'Mon/Wed/Fri 9:00-9:50 AM',
                'max_students': 25,
                'description': 'Introduction to algebraic concepts and problem solving',
                'teacher_id': teachers[0].id if len(teachers) > 0 else None,
                'school_year_id': school_year.id
            },
            {
                'name': 'English Literature',
                'subject': 'English',
                'grade_level': '10',
                'room_number': '102',
                'schedule': 'Tue/Thu 10:00-10:50 AM',
                'max_students': 20,
                'description': 'Study of classic and contemporary literature',
                'teacher_id': teachers[1].id if len(teachers) > 1 else None,
                'school_year_id': school_year.id
            },
            {
                'name': 'Biology',
                'subject': 'Science',
                'grade_level': '11',
                'room_number': '103',
                'schedule': 'Mon/Wed 11:00-11:50 AM',
                'max_students': 22,
                'description': 'Introduction to biological sciences',
                'teacher_id': teachers[2].id if len(teachers) > 2 else None,
                'school_year_id': school_year.id
            },
            {
                'name': 'World History',
                'subject': 'History',
                'grade_level': '12',
                'room_number': '104',
                'schedule': 'Tue/Thu 1:00-1:50 PM',
                'max_students': 18,
                'description': 'Survey of world history from ancient to modern times',
                'teacher_id': teachers[3].id if len(teachers) > 3 else None,
                'school_year_id': school_year.id
            }
        ]
        
        classes = []
        for class_data in classes_data:
            class_obj = Class(**class_data)
            db.session.add(class_obj)
            classes.append(class_obj)
        
        db.session.commit()
        print(f"Created {len(classes)} classes")
        return classes
    
    def create_students(self, classes):
        """Create sample students and enroll them in classes."""
        print("Creating sample students...")
        
        # Check if students already exist
        existing_students = Student.query.count()
        if existing_students > 0:
            print(f"Students already exist ({existing_students} found)")
            return Student.query.all()
        
        students_data = [
            {'first_name': 'Alice', 'last_name': 'Johnson', 'email': 'alice.johnson@student.edu', 'grade_level': '9'},
            {'first_name': 'Bob', 'last_name': 'Smith', 'email': 'bob.smith@student.edu', 'grade_level': '9'},
            {'first_name': 'Carol', 'last_name': 'Brown', 'email': 'carol.brown@student.edu', 'grade_level': '10'},
            {'first_name': 'David', 'last_name': 'Davis', 'email': 'david.davis@student.edu', 'grade_level': '10'},
            {'first_name': 'Eve', 'last_name': 'Wilson', 'email': 'eve.wilson@student.edu', 'grade_level': '11'},
            {'first_name': 'Frank', 'last_name': 'Moore', 'email': 'frank.moore@student.edu', 'grade_level': '11'},
            {'first_name': 'Grace', 'last_name': 'Taylor', 'email': 'grace.taylor@student.edu', 'grade_level': '12'},
            {'first_name': 'Henry', 'last_name': 'Anderson', 'email': 'henry.anderson@student.edu', 'grade_level': '12'}
        ]
        
        students = []
        for student_data in students_data:
            student = Student(**student_data)
            db.session.add(student)
            students.append(student)
        
        db.session.commit()
        print(f"Created {len(students)} students")
        
        # Enroll students in appropriate classes
        print("Enrolling students in classes...")
        for student in students:
            for class_obj in classes:
                # Simple enrollment logic based on grade level
                if student.grade_level == class_obj.grade_level:
                    enrollment = Enrollment(
                        student_id=student.id,
                        class_id=class_obj.id,
                        enrollment_date=date.today(),
                        is_active=True
                    )
                    db.session.add(enrollment)
        
        db.session.commit()
        print("Enrolled students in classes")
        return students
    
    def create_assignments(self, classes):
        """Create sample assignments."""
        print("Creating sample assignments...")
        
        # Check if assignments already exist
        existing_assignments = Assignment.query.count()
        if existing_assignments > 0:
            print(f"Assignments already exist ({existing_assignments} found)")
            return Assignment.query.all()
        
        assignments = []
        for class_obj in classes:
            # Create 2-3 assignments per class
            for i in range(2):
                assignment = Assignment(
                    title=f"{class_obj.name} Assignment {i+1}",
                    description=f"Sample assignment for {class_obj.name}",
                    due_date=datetime.now() + timedelta(days=7*(i+1)),
                    points=100,
                    quarter="1",
                    class_id=class_obj.id,
                    school_year_id=class_obj.school_year_id,
                    assignment_type='pdf_paper',
                    status='Active',
                    created_by=class_obj.teacher_id
                )
                db.session.add(assignment)
                assignments.append(assignment)
        
        db.session.commit()
        print(f"Created {len(assignments)} assignments")
        return assignments
    
    def create_sample_data(self):
        """Create all sample data."""
        print("Starting sample data creation...")
        
        try:
            # Create school year
            school_year = self.create_school_year()
            
            # Create academic periods
            self.create_academic_periods(school_year.id)
            
            # Create teachers
            teachers = self.create_teachers()
            
            # Create classes
            classes = self.create_classes(school_year, teachers)
            
            # Create students
            students = self.create_students(classes)
            
            # Create assignments
            assignments = self.create_assignments(classes)
            
            print("✅ Sample data creation completed successfully!")
            print(f"Created: 1 school year, 4 quarters, {len(teachers)} teachers, {len(classes)} classes, {len(students)} students, {len(assignments)} assignments")
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            db.session.rollback()
            raise

def main():
    """Main function to run sample data creation."""
    with SampleDataManager() as manager:
        manager.create_sample_data()

if __name__ == '__main__':
    main()



