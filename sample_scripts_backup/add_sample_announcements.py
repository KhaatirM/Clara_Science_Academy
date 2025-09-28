#!/usr/bin/env python3
"""
Script to add sample announcements for testing.
"""

from app import create_app, db
from models import Announcement, User, Class, SchoolYear
from datetime import datetime, timedelta

def add_sample_announcements():
    """Add sample announcements for testing."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the active school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("No active school year found.")
                return
            
            # Get existing users (for sender)
            users = User.query.all()
            if not users:
                print("No users found.")
                return
            
            # Get existing classes
            classes = Class.query.filter_by(school_year_id=school_year.id).all()
            if not classes:
                print("No classes found.")
                return
            
            print(f"Found {len(users)} users and {len(classes)} classes")
            
            # Sample announcements
            announcements = [
                {
                    "title": "Welcome Back to School!",
                    "message": "We're excited to start the new school year. Please check your schedules and be ready for an amazing year ahead.",
                    "target_group": "all_students",
                    "is_important": True
                },
                {
                    "title": "Parent-Teacher Conference Sign-up",
                    "message": "Parent-teacher conferences will be held next week. Please sign up for a time slot through the parent portal.",
                    "target_group": "all_students",
                    "is_important": False
                },
                {
                    "title": "Science Fair Registration",
                    "message": "The annual science fair is coming up! Students in grades 6-8 can register their projects starting next Monday.",
                    "target_group": "all_students",
                    "is_important": False
                },
                {
                    "title": "Library Hours Extended",
                    "message": "The school library will now be open until 4:30 PM on weekdays for students who need extra study time.",
                    "target_group": "all_students",
                    "is_important": False
                },
                {
                    "title": "Math Club Meeting",
                    "message": "Math Club will meet every Tuesday after school in Room 205. All students interested in mathematics are welcome!",
                    "target_group": "all_students",
                    "is_important": False
                }
            ]
            
            # Add class-specific announcements
            for class_obj in classes:
                announcements.append({
                    "title": f"{class_obj.name} - Important Update",
                    "message": f"Please note that {class_obj.name} will have a special guest speaker next week. More details to follow.",
                    "target_group": "class",
                    "class_id": class_obj.id,
                    "is_important": False
                })
            
            announcements_added = 0
            for i, announcement_data in enumerate(announcements):
                # Check if announcement already exists
                existing = Announcement.query.filter_by(
                    title=announcement_data["title"]
                ).first()
                
                if not existing:
                    # Assign sender (round-robin)
                    sender = users[i % len(users)]
                    
                    # Set timestamp (recent announcements)
                    timestamp = datetime.now() - timedelta(days=i)
                    
                    announcement = Announcement(
                        title=announcement_data["title"],
                        message=announcement_data["message"],
                        sender_id=sender.id,
                        timestamp=timestamp,
                        target_group=announcement_data["target_group"],
                        class_id=announcement_data.get("class_id"),
                        is_important=announcement_data.get("is_important", False),
                        requires_confirmation=False,
                        expires_at=timestamp + timedelta(days=30)
                    )
                    db.session.add(announcement)
                    announcements_added += 1
                    print(f"Added announcement: {announcement_data['title']}")
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully added {announcements_added} announcements")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    add_sample_announcements()
