#!/usr/bin/env python3
"""
Add a single test user to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, Student, TeacherStaff, SchoolYear
from werkzeug.security import generate_password_hash
from datetime import datetime

def add_single_user():
    """Add a single test user"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting to add test user...")
            
            # Check if user already exists
            existing_user = User.query.filter_by(username='director').first()
            if existing_user:
                print("Director user already exists")
                return
            
            # Create a new user
            new_user = User(
                username='director',
                password_hash=generate_password_hash('password123'),
                role='Director',
                is_active=True,
                login_count=0,
                is_temporary_password=False,
                password_changed_at=datetime.utcnow()
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            print("Director user added successfully!")
            
            # Check if user was added
            user = User.query.filter_by(username='director').first()
            if user:
                print(f"User found: {user.username}, Role: {user.role}")
            else:
                print("User not found after adding")
                
        except Exception as e:
            print(f"Error adding user: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_single_user()
