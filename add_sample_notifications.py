#!/usr/bin/env python3
"""
Script to add sample notifications for testing the notification system.
"""

from app import create_app, db
from models import User, Student, TeacherStaff, Notification
from datetime import datetime, timedelta

def add_sample_notifications():
    """Add sample notifications for testing"""
    
    # Create the app instance
    app = create_app()
    
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        if not users:
            print("No users found. Please add users first.")
            return
        
        # Sample notifications for students
        student_users = [u for u in users if u.role == 'Student']
        for user in student_users:
            # Sample assignment notification
            notification1 = Notification()
            notification1.user_id = user.id
            notification1.type = 'assignment'
            notification1.title = 'New Assignment: Math Quiz'
            notification1.message = 'A new math quiz has been assigned. Due date: Tomorrow'
            notification1.link = '/student/assignments'
            notification1.timestamp = datetime.now() - timedelta(hours=2)
            db.session.add(notification1)
            
            # Sample grade notification
            notification2 = Notification()
            notification2.user_id = user.id
            notification2.type = 'grade'
            notification2.title = 'Grade posted for Science Project'
            notification2.message = 'Your science project has been graded. Score: 95%'
            notification2.link = '/student/grades'
            notification2.timestamp = datetime.now() - timedelta(hours=4)
            db.session.add(notification2)
            
            # Sample announcement notification
            notification3 = Notification()
            notification3.user_id = user.id
            notification3.type = 'announcement'
            notification3.title = 'School Assembly Tomorrow'
            notification3.message = 'There will be a school assembly tomorrow at 9 AM in the gym.'
            notification3.timestamp = datetime.now() - timedelta(hours=6)
            db.session.add(notification3)
        
        # Sample notifications for teachers
        teacher_users = [u for u in users if u.role == 'Teacher']
        for user in teacher_users:
            # Sample submission notification
            notification1 = Notification()
            notification1.user_id = user.id
            notification1.type = 'submission'
            notification1.title = 'New submission received'
            notification1.message = 'John Smith submitted work for Math Assignment #3'
            notification1.link = '/teacher/assignments'
            notification1.timestamp = datetime.now() - timedelta(hours=1)
            db.session.add(notification1)
            
            # Sample system notification
            notification2 = Notification()
            notification2.user_id = user.id
            notification2.type = 'system'
            notification2.title = 'System Maintenance'
            notification2.message = 'System will be under maintenance tonight from 10 PM to 2 AM.'
            notification2.timestamp = datetime.now() - timedelta(hours=3)
            db.session.add(notification2)
        
        # Commit all notifications
        db.session.commit()
        
        print(f"Successfully added sample notifications:")
        print(f"- {len(student_users)} students received 3 notifications each")
        print(f"- {len(teacher_users)} teachers received 2 notifications each")
        print(f"Total notifications created: {len(student_users) * 3 + len(teacher_users) * 2}")

if __name__ == '__main__':
    add_sample_notifications() 