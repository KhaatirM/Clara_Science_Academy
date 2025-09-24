#!/usr/bin/env python3
"""
Create test users for the application
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, Student, TeacherStaff, SchoolYear
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_test_users():
    """Create test users"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Creating test users...")
            
            # Clear existing users
            User.query.delete()
            db.session.commit()
            print("Cleared existing users")
            
            # Create Director
            director = User(
                username='director',
                password_hash=generate_password_hash('password123'),
                role='Director',
                is_active=True,
                login_count=0,
                is_temporary_password=False,
                password_changed_at=datetime.utcnow()
            )
            db.session.add(director)
            
            # Create Admin
            admin = User(
                username='admin',
                password_hash=generate_password_hash('password123'),
                role='School Administrator',
                is_active=True,
                login_count=0,
                is_temporary_password=False,
                password_changed_at=datetime.utcnow()
            )
            db.session.add(admin)
            
            # Create Teacher
            teacher = User(
                username='teacher',
                password_hash=generate_password_hash('password123'),
                role='Teacher',
                is_active=True,
                login_count=0,
                is_temporary_password=False,
                password_changed_at=datetime.utcnow()
            )
            db.session.add(teacher)
            
            # Create Student
            student = User(
                username='student',
                password_hash=generate_password_hash('password123'),
                role='Student',
                is_active=True,
                login_count=0,
                is_temporary_password=False,
                password_changed_at=datetime.utcnow()
            )
            db.session.add(student)
            
            # Create Tech
            tech = User(
                username='tech',
                password_hash=generate_password_hash('password123'),
                role='Tech',
                is_active=True,
                login_count=0,
                is_temporary_password=False,
                password_changed_at=datetime.utcnow()
            )
            db.session.add(tech)
            
            db.session.commit()
            print("Test users created successfully!")
            
            # Verify users were created
            users = User.query.all()
            print(f"Total users in database: {len(users)}")
            for user in users:
                print(f"  - {user.username} ({user.role})")
                
        except Exception as e:
            print(f"Error creating users: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_test_users()
