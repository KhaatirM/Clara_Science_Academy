#!/usr/bin/env python3
"""
Admin User Manager Script
=========================

Advanced script for managing user credentials on Render.
Includes export, password reset, and user management features.

Usage:
    python admin_user_manager.py export
    python admin_user_manager.py reset-password <username> <new_password>
    python admin_user_manager.py list
    python admin_user_manager.py create <username> <password> <role>
"""

import os
import sys
import getpass
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import db, User
    from werkzeug.security import generate_password_hash
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def export_credentials():
    """Export all user credentials."""
    app = create_app()
    
    with app.app_context():
        try:
            users = User.query.all()
            
            if not users:
                print("No users found in the database.")
                return
            
            print("=" * 100)
            print("USER CREDENTIALS EXPORT")
            print("=" * 100)
            print(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Total Users: {len(users)}")
            print("=" * 100)
            
            for i, user in enumerate(users, 1):
                print(f"\n{i}. USER ID: {user.id}")
                print(f"   Username: {user.username}")
                print(f"   Email: {getattr(user, 'email', 'N/A')}")
                print(f"   Role: {getattr(user, 'role', 'N/A')}")
                print(f"   First Name: {getattr(user, 'first_name', 'N/A')}")
                print(f"   Last Name: {getattr(user, 'last_name', 'N/A')}")
                print(f"   Active: {getattr(user, 'is_active', True)}")
                print(f"   Created: {getattr(user, 'created_at', 'N/A')}")
                print(f"   Last Login: {getattr(user, 'last_login', 'N/A')}")
                print(f"   Password Hash: {user.password_hash}")
                print("-" * 80)
            
            print(f"\nExport completed! Total users: {len(users)}")
            
        except Exception as e:
            print(f"Error exporting credentials: {e}")
            import traceback
            traceback.print_exc()

def list_users():
    """List all users with basic info."""
    app = create_app()
    
    with app.app_context():
        try:
            users = User.query.all()
            
            if not users:
                print("No users found in the database.")
                return
            
            print("=" * 80)
            print("USER LIST")
            print("=" * 80)
            print(f"Total Users: {len(users)}")
            print("=" * 80)
            
            for i, user in enumerate(users, 1):
                print(f"{i:2d}. ID: {user.id:3d} | Username: {user.username:20s} | Role: {getattr(user, 'role', 'N/A'):15s} | Active: {getattr(user, 'is_active', True)}")
            
            print(f"\nTotal users: {len(users)}")
            
        except Exception as e:
            print(f"Error listing users: {e}")
            import traceback
            traceback.print_exc()

def reset_password(username, new_password):
    """Reset a user's password."""
    app = create_app()
    
    with app.app_context():
        try:
            user = User.query.filter_by(username=username).first()
            
            if not user:
                print(f"User '{username}' not found.")
                return False
            
            # Generate new password hash
            password_hash = generate_password_hash(new_password)
            
            # Update password
            user.password_hash = password_hash
            db.session.commit()
            
            print(f"Password reset successfully for user '{username}'")
            print(f"New password hash: {password_hash}")
            return True
            
        except Exception as e:
            print(f"Error resetting password: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

def create_user(username, password, role):
    """Create a new user."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"User '{username}' already exists.")
                return False
            
            # Generate password hash
            password_hash = generate_password_hash(password)
            
            # Create new user
            new_user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                is_active=True
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            print(f"User '{username}' created successfully with role '{role}'")
            print(f"Password hash: {password_hash}")
            return True
            
        except Exception as e:
            print(f"Error creating user: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

def show_help():
    """Show help information."""
    print("""
Admin User Manager Script
========================

Usage:
    python admin_user_manager.py <command> [arguments]

Commands:
    export                    - Export all user credentials
    list                      - List all users with basic info
    reset-password <user> <pass> - Reset a user's password
    create <user> <pass> <role>  - Create a new user
    help                      - Show this help

Examples:
    python admin_user_manager.py export
    python admin_user_manager.py list
    python admin_user_manager.py reset-password john newpassword123
    python admin_user_manager.py create jane mypass123 Teacher

Security Note:
    This script handles sensitive information. Use responsibly.
""")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'help':
        show_help()
    elif command == 'export':
        export_credentials()
    elif command == 'list':
        list_users()
    elif command == 'reset-password':
        if len(sys.argv) < 4:
            print("Usage: python admin_user_manager.py reset-password <username> <new_password>")
        else:
            username = sys.argv[2]
            new_password = sys.argv[3]
            reset_password(username, new_password)
    elif command == 'create':
        if len(sys.argv) < 5:
            print("Usage: python admin_user_manager.py create <username> <password> <role>")
        else:
            username = sys.argv[2]
            password = sys.argv[3]
            role = sys.argv[4]
            create_user(username, password, role)
    else:
        print(f"Unknown command: {command}")
        show_help()

if __name__ == '__main__':
    main()
