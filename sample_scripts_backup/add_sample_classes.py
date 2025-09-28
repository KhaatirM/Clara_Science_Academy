#!/usr/bin/env python3
"""
Script to add sample classes for testing.
"""

from app import create_app, db
from models import Class, SchoolYear, TeacherStaff

def add_sample_classes():
    """Add sample classes for testing."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the active school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("No active school year found. Please create one first.")
                return
            
            # Get existing teachers
            teachers = TeacherStaff.query.all()
            if not teachers:
                print("No teachers found. Please create teachers first.")
                return
            
            print(f"Found school year: {school_year.name}")
            print(f"Found {len(teachers)} teachers")
            
            # Sample classes to create
            sample_classes = [
                {"name": "Mathematics 101", "subject": "Mathematics"},
                {"name": "English Literature", "subject": "English"},
                {"name": "Science Lab", "subject": "Science"},
                {"name": "History", "subject": "Social Studies"},
                {"name": "Physical Education", "subject": "Physical Education"},
                {"name": "Art & Design", "subject": "Arts"},
                {"name": "Computer Science", "subject": "Technology"},
                {"name": "Spanish", "subject": "Foreign Language"}
            ]
            
            classes_added = 0
            for i, class_data in enumerate(sample_classes):
                # Check if class already exists
                existing = Class.query.filter_by(
                    name=class_data["name"],
                    school_year_id=school_year.id
                ).first()
                
                if not existing:
                    # Assign teacher (round-robin)
                    teacher = teachers[i % len(teachers)]
                    
                    new_class = Class(
                        name=class_data["name"],
                        subject=class_data["subject"],
                        teacher_id=teacher.id,
                        school_year_id=school_year.id
                    )
                    db.session.add(new_class)
                    classes_added += 1
                    print(f"Added class: {class_data['name']} with teacher {teacher.first_name} {teacher.last_name}")
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully added {classes_added} classes")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    add_sample_classes()

