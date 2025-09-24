#!/usr/bin/env python3
"""
Add director user to test login
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User
from werkzeug.security import generate_password_hash
from datetime import datetime

def add_director():
    """Add director user"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Adding director user...")
            
            # Check if director already exists
            existing = User.query.filter_by(username='director').first()
            if existing:
                print("Director already exists")
                return
            
            # Create director user
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
            db.session.commit()
            
            print("Director user added successfully!")
            
            # Verify
            user = User.query.filter_by(username='director').first()
            if user:
                print(f"Verified: {user.username} ({user.role})")
            else:
                print("ERROR: User not found after adding")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_director()
