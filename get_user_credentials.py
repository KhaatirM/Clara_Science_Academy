#!/usr/bin/env python3
"""
Simple User Credentials Script
==============================

Quick script to get all user credentials from the database.
Designed for Render shell usage.

Usage:
    python get_user_credentials.py
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import User
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def get_credentials():
    """Get all user credentials."""
    app = create_app()
    
    with app.app_context():
        try:
            users = User.query.all()
            
            if not users:
                print("No users found in the database.")
                return
            
            print("=" * 80)
            print("USER CREDENTIALS")
            print("=" * 80)
            print(f"Total Users: {len(users)}")
            print("=" * 80)
            
            for i, user in enumerate(users, 1):
                print(f"\n{i}. ID: {user.id}")
                print(f"   Username: {user.username}")
                print(f"   Email: {getattr(user, 'email', 'N/A')}")
                print(f"   Role: {getattr(user, 'role', 'N/A')}")
                print(f"   Name: {getattr(user, 'first_name', 'N/A')} {getattr(user, 'last_name', 'N/A')}")
                print(f"   Active: {getattr(user, 'is_active', True)}")
                print(f"   Password Hash: {user.password_hash}")
                print("-" * 60)
            
            print(f"\nExport completed! Total users: {len(users)}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    get_credentials()
