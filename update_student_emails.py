#!/usr/bin/env python3
"""
Script to update all existing students with generated email addresses.
This script generates emails in the format: firstname + lastinitial + month + year @clarascienceacademy.org

Example: Anna Amani, DOB: 2016-03-11 -> annaa0316@clarascienceacademy.org

Usage: python update_student_emails.py
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import Student, db

def update_student_emails():
    """Update all students with generated email addresses"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all students
            students = Student.query.all()
            
            if not students:
                print("No students found in the database.")
                return
            
            print(f"Found {len(students)} students to process...")
            
            updated_count = 0
            skipped_count = 0
            error_count = 0
            
            for student in students:
                try:
                    # Check if student already has an email
                    if student.email:
                        print(f"Skipping {student.first_name} {student.last_name} - already has email: {student.email}")
                        skipped_count += 1
                        continue
                    
                    # Generate email
                    generated_email = student.generate_email()
                    
                    if not generated_email:
                        print(f"Error generating email for {student.first_name} {student.last_name} - missing required data (first_name, last_name, or dob)")
                        error_count += 1
                        continue
                    
                    # Check for duplicate emails
                    existing_student = Student.query.filter_by(email=generated_email).first()
                    if existing_student and existing_student.id != student.id:
                        print(f"Warning: Email {generated_email} already exists for another student. Skipping {student.first_name} {student.last_name}")
                        error_count += 1
                        continue
                    
                    # Update student with generated email
                    student.email = generated_email
                    updated_count += 1
                    
                    print(f"Updated {student.first_name} {student.last_name} (DOB: {student.dob}) -> {generated_email}")
                    
                except Exception as e:
                    print(f"Error processing student {student.first_name} {student.last_name}: {str(e)}")
                    error_count += 1
                    continue
            
            # Commit all changes
            if updated_count > 0:
                db.session.commit()
                print(f"\n✅ Successfully updated {updated_count} students with generated emails!")
            else:
                print("\n⚠️  No students were updated.")
            
            print(f"\nSummary:")
            print(f"  - Updated: {updated_count}")
            print(f"  - Skipped (already had email): {skipped_count}")
            print(f"  - Errors: {error_count}")
            print(f"  - Total processed: {len(students)}")
            
        except Exception as e:
            print(f"❌ Fatal error: {str(e)}")
            db.session.rollback()
            sys.exit(1)

def preview_emails():
    """Preview what emails would be generated without making changes"""
    app = create_app()
    
    with app.app_context():
        try:
            students = Student.query.all()
            
            if not students:
                print("No students found in the database.")
                return
            
            print(f"Preview of emails that would be generated for {len(students)} students:\n")
            
            for student in students:
                generated_email = student.generate_email()
                status = "✅" if generated_email else "❌"
                email_display = generated_email if generated_email else "ERROR - Missing required data"
                
                print(f"{status} {student.first_name} {student.last_name} (DOB: {student.dob}) -> {email_display}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        print("🔍 PREVIEW MODE - No changes will be made\n")
        preview_emails()
    else:
        print("🚀 Updating student emails...\n")
        print("To preview changes first, run: python update_student_emails.py --preview\n")
        
        # Ask for confirmation
        response = input("Do you want to proceed with updating student emails? (y/N): ")
        if response.lower() in ['y', 'yes']:
            update_student_emails()
        else:
            print("Operation cancelled.")
