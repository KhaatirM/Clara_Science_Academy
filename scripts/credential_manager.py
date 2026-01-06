#!/usr/bin/env python3
"""
Unified Credential Management System

This script consolidates all password and credential management functionality
into a single, comprehensive system. It replaces multiple individual scripts.
"""

import os
import sys
import csv
import json
import getpass
from datetime import datetime
from typing import List, Dict, Optional

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import db, User, Student, TeacherStaff
    from werkzeug.security import generate_password_hash
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

class CredentialManager:
    """Manages all credential operations for the application."""
    
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_context.pop()
    
    def list_all_users(self) -> List[Dict]:
        """List all users with their information."""
        users = User.query.all()
        user_list = []
        
        for user in users:
            user_data = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'has_password': bool(user.password_hash)
            }
            user_list.append(user_data)
        
        return user_list
    
    def reset_user_password(self, email: str, new_password: str) -> bool:
        """Reset a user's password."""
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                print(f"User with email '{email}' not found.")
                return False
            
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            print(f"✅ Password reset successfully for {email}")
            print(f"New password: {new_password}")
            return True
            
        except Exception as e:
            print(f"❌ Error resetting password for {email}: {e}")
            db.session.rollback()
            return False
    
    def reset_all_passwords(self, new_password: str) -> int:
        """Reset passwords for all users."""
        try:
            users = User.query.all()
            reset_count = 0
            
            for user in users:
                user.password_hash = generate_password_hash(new_password)
                reset_count += 1
            
            db.session.commit()
            
            print(f"✅ Reset passwords for {reset_count} users")
            print(f"New password for all users: {new_password}")
            return reset_count
            
        except Exception as e:
            print(f"❌ Error resetting all passwords: {e}")
            db.session.rollback()
            return 0
    
    def create_user(self, email: str, password: str, first_name: str, last_name: str, role: str) -> bool:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                print(f"User with email '{email}' already exists.")
                return False
            
            # Create new user
            new_user = User(
                email=email,
                password_hash=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
                created_at=datetime.now()
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            print(f"✅ User created successfully: {email}")
            print(f"Password: {password}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating user {email}: {e}")
            db.session.rollback()
            return False
    
    def export_credentials_csv(self, filename: str = None) -> str:
        """Export all user credentials to CSV file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_credentials_{timestamp}.csv"
        
        try:
            users = self.list_all_users()
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for user in users:
                    # Remove sensitive data for CSV
                    user_data = {k: v for k, v in user.items() if k != 'has_password'}
                    writer.writerow(user_data)
            
            print(f"✅ Credentials exported to {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting credentials: {e}")
            return ""
    
    def export_credentials_json(self, filename: str = None) -> str:
        """Export all user credentials to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_credentials_{timestamp}.json"
        
        try:
            users = self.list_all_users()
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(users, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"✅ Credentials exported to {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting credentials: {e}")
            return ""
    
    def display_user_table(self):
        """Display all users in a formatted table."""
        users = self.list_all_users()
        
        if not users:
            print("No users found in the database.")
            return
        
        print("=" * 120)
        print("USER CREDENTIALS OVERVIEW")
        print("=" * 120)
        print(f"{'ID':<5} {'Email':<30} {'Name':<25} {'Role':<20} {'Active':<8} {'Has Password':<12}")
        print("-" * 120)
        
        for user in users:
            name = f"{user['first_name']} {user['last_name']}"
            active = "Yes" if user['is_active'] else "No"
            has_password = "Yes" if user['has_password'] else "No"
            
            print(f"{user['id']:<5} {user['email']:<30} {name:<25} {user['role']:<20} {active:<8} {has_password:<12}")
        
        print("-" * 120)
        print(f"Total users: {len(users)}")
        print("=" * 120)
    
    def quick_reset_all(self, password: str = "password123"):
        """Quick reset all user passwords to a default value."""
        print(f"⚠️  WARNING: This will reset ALL user passwords to '{password}'")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        
        if confirm.lower() == 'yes':
            count = self.reset_all_passwords(password)
            if count > 0:
                print(f"✅ Successfully reset {count} user passwords")
            else:
                print("❌ Failed to reset passwords")
        else:
            print("Operation cancelled.")
    
    def interactive_menu(self):
        """Display interactive menu for credential management."""
        while True:
            print("\n" + "=" * 50)
            print("CREDENTIAL MANAGEMENT SYSTEM")
            print("=" * 50)
            print("1. List all users")
            print("2. Reset user password")
            print("3. Reset all passwords")
            print("4. Create new user")
            print("5. Export credentials (CSV)")
            print("6. Export credentials (JSON)")
            print("7. Quick reset all passwords")
            print("8. Exit")
            print("-" * 50)
            
            choice = input("Enter your choice (1-8): ").strip()
            
            if choice == '1':
                self.display_user_table()
            elif choice == '2':
                email = input("Enter user email: ").strip()
                password = getpass.getpass("Enter new password: ")
                self.reset_user_password(email, password)
            elif choice == '3':
                password = getpass.getpass("Enter new password for all users: ")
                self.reset_all_passwords(password)
            elif choice == '4':
                email = input("Enter email: ").strip()
                password = getpass.getpass("Enter password: ")
                first_name = input("Enter first name: ").strip()
                last_name = input("Enter last name: ").strip()
                role = input("Enter role (Student/Teacher/Director/School Administrator): ").strip()
                self.create_user(email, password, first_name, last_name, role)
            elif choice == '5':
                filename = input("Enter filename (or press Enter for auto-generated): ").strip()
                if not filename:
                    filename = None
                self.export_credentials_csv(filename)
            elif choice == '6':
                filename = input("Enter filename (or press Enter for auto-generated): ").strip()
                if not filename:
                    filename = None
                self.export_credentials_json(filename)
            elif choice == '7':
                self.quick_reset_all()
            elif choice == '8':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")

def main():
    """Main function with command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python credential_manager.py [command] [options]")
        print("Commands:")
        print("  list                    - List all users")
        print("  reset <email> <pass>    - Reset user password")
        print("  reset-all <pass>        - Reset all passwords")
        print("  create <email> <pass> <first> <last> <role> - Create user")
        print("  export-csv [filename]   - Export to CSV")
        print("  export-json [filename]  - Export to JSON")
        print("  quick-reset             - Quick reset all to 'password123'")
        print("  interactive             - Interactive menu")
        return
    
    command = sys.argv[1].lower()
    
    with CredentialManager() as manager:
        if command == 'list':
            manager.display_user_table()
        elif command == 'reset':
            if len(sys.argv) < 4:
                print("Usage: reset <email> <password>")
                return
            manager.reset_user_password(sys.argv[2], sys.argv[3])
        elif command == 'reset-all':
            if len(sys.argv) < 3:
                print("Usage: reset-all <password>")
                return
            manager.reset_all_passwords(sys.argv[2])
        elif command == 'create':
            if len(sys.argv) < 7:
                print("Usage: create <email> <password> <first_name> <last_name> <role>")
                return
            manager.create_user(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
        elif command == 'export-csv':
            filename = sys.argv[2] if len(sys.argv) > 2 else None
            manager.export_credentials_csv(filename)
        elif command == 'export-json':
            filename = sys.argv[2] if len(sys.argv) > 2 else None
            manager.export_credentials_json(filename)
        elif command == 'quick-reset':
            manager.quick_reset_all()
        elif command == 'interactive':
            manager.interactive_menu()
        else:
            print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()


