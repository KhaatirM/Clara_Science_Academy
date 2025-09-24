#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    print("Creating test users...")
    
    # Clear existing users
    User.query.delete()
    db.session.commit()
    print("Cleared existing users")
    
    # Create test users with only required fields
    users = [
        User(username='director', password_hash=generate_password_hash('password123'), role='Director'),
        User(username='admin', password_hash=generate_password_hash('password123'), role='School Administrator'),
        User(username='teacher', password_hash=generate_password_hash('password123'), role='Teacher'),
        User(username='student', password_hash=generate_password_hash('password123'), role='Student'),
        User(username='tech', password_hash=generate_password_hash('password123'), role='Tech')
    ]
    
    for user in users:
        db.session.add(user)
    
    db.session.commit()
    print("Test users created successfully!")
    
    # Verify
    all_users = User.query.all()
    print(f"Total users: {len(all_users)}")
    for user in all_users:
        print(f"  - {user.username} ({user.role})")



