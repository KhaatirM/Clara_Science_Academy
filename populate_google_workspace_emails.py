"""
Helper script to populate google_workspace_email for existing users.
This script helps you set up Google Workspace emails for your staff and students.
"""

from app import app, db
from models import User, Student, TeacherStaff

def populate_google_workspace_emails():
    """
    Populate google_workspace_email for all users based on their role.
    
    Format:
    - Students: firstname.lastname@clarascienceacademy.org
    - Teachers/Staff: firstname.lastname@clarascienceacademy.org
    - Directors: firstname.lastname@clarascienceacademy.org
    """
    
    with app.app_context():
        print("=" * 60)
        print("Google Workspace Email Population Script")
        print("=" * 60)
        print()
        
        # Get all users
        users = User.query.all()
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for user in users:
            try:
                # Skip if already has Google Workspace email
                if user.google_workspace_email:
                    print(f"⏭️  Skipping {user.username} - already has Google Workspace email: {user.google_workspace_email}")
                    skipped_count += 1
                    continue
                
                # Determine the email based on role
                workspace_email = None
                
                if user.role == 'Student' and user.student_id:
                    # Get student details
                    student = Student.query.get(user.student_id)
                    if student and student.first_name and student.last_name:
                        # Format: firstname.lastname@clarascienceacademy.org
                        first = student.first_name.lower().replace(' ', '')
                        last = student.last_name.lower().replace(' ', '')
                        workspace_email = f"{first}.{last}@clarascienceacademy.org"
                
                elif user.role in ['Teacher', 'Director', 'School Administrator', 'Tech', 'IT Support'] and user.teacher_staff_id:
                    # Get teacher/staff details
                    staff = TeacherStaff.query.get(user.teacher_staff_id)
                    if staff and staff.first_name and staff.last_name:
                        # Format: firstname.lastname@clarascienceacademy.org
                        first = staff.first_name.lower().replace(' ', '')
                        last = staff.last_name.lower().replace(' ', '')
                        workspace_email = f"{first}.{last}@clarascienceacademy.org"
                
                if workspace_email:
                    # Check if this email is already used by another user
                    existing = User.query.filter_by(google_workspace_email=workspace_email).first()
                    if existing:
                        print(f"⚠️  Warning: {workspace_email} already assigned to {existing.username}")
                        print(f"   Skipping {user.username} - please set manually")
                        error_count += 1
                        continue
                    
                    # Update the user
                    user.google_workspace_email = workspace_email
                    print(f"✅ {user.username} ({user.role}): {workspace_email}")
                    updated_count += 1
                else:
                    print(f"⚠️  Could not generate email for {user.username} ({user.role}) - missing name information")
                    error_count += 1
                
            except Exception as e:
                print(f"❌ Error processing {user.username}: {str(e)}")
                error_count += 1
        
        # Commit all changes
        try:
            db.session.commit()
            print()
            print("=" * 60)
            print("Summary:")
            print(f"  ✅ Updated: {updated_count} users")
            print(f"  ⏭️  Skipped: {skipped_count} users (already had email)")
            print(f"  ⚠️  Errors: {error_count} users (need manual setup)")
            print("=" * 60)
            print()
            print("Next steps:")
            print("1. Review the emails above")
            print("2. Manually update any users with errors via management dashboard")
            print("3. Test Google Sign-In with updated accounts")
            
        except Exception as e:
            db.session.rollback()
            print()
            print(f"❌ Error committing changes: {str(e)}")
            print("No changes were saved to the database.")

def show_current_emails():
    """Display all users and their current email settings."""
    
    with app.app_context():
        print("=" * 80)
        print("Current User Email Settings")
        print("=" * 80)
        print(f"{'Username':<20} {'Role':<20} {'Personal Email':<30} {'Workspace Email':<30}")
        print("-" * 80)
        
        users = User.query.all()
        for user in users:
            personal = user.email or "(not set)"
            workspace = user.google_workspace_email or "(not set)"
            print(f"{user.username:<20} {user.role:<20} {personal:<30} {workspace:<30}")
        
        print("=" * 80)

def set_single_user_email(username, workspace_email):
    """Set Google Workspace email for a single user."""
    
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ User '{username}' not found.")
            return
        
        # Check if email is already used
        existing = User.query.filter_by(google_workspace_email=workspace_email).first()
        if existing and existing.id != user.id:
            print(f"❌ Email '{workspace_email}' is already assigned to user '{existing.username}'")
            return
        
        user.google_workspace_email = workspace_email
        db.session.commit()
        
        print(f"✅ Successfully set Google Workspace email for {username}")
        print(f"   Email: {workspace_email}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'show':
            show_current_emails()
        elif command == 'set' and len(sys.argv) == 4:
            username = sys.argv[2]
            email = sys.argv[3]
            set_single_user_email(username, email)
        else:
            print("Usage:")
            print("  python populate_google_workspace_emails.py          - Auto-populate all emails")
            print("  python populate_google_workspace_emails.py show     - Show current email settings")
            print("  python populate_google_workspace_emails.py set <username> <email>  - Set single user email")
            print()
            print("Examples:")
            print("  python populate_google_workspace_emails.py")
            print("  python populate_google_workspace_emails.py show")
            print("  python populate_google_workspace_emails.py set john.doe john.doe@clarascienceacademy.org")
    else:
        populate_google_workspace_emails()

