#!/usr/bin/env python3
"""
Script to recreate the database with all current models.
This will delete the existing database and create a fresh one with all tables.
"""

import os
from app import create_app
from extensions import db
from models import db, User, Student, TeacherStaff, SchoolYear, Class, Assignment, Submission, Grade, ReportCard, Announcement, Notification, MaintenanceMode, ActivityLog, StudentGoal, Message, MessageGroup, MessageGroupMember, MessageAttachment, AnnouncementReadReceipt, ScheduledAnnouncement, Enrollment, BugReport, Attendance
from werkzeug.security import generate_password_hash
from datetime import datetime, date

def recreate_database():
    """Recreate the database with all tables"""
    app = create_app()
    
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("Dropped all tables")
        
        # Create all tables
        db.create_all()
        print("Created all tables")
        
        # Create a default school year
        current_year = datetime.now().year
        school_year = SchoolYear(
            name=f"{current_year}-{current_year + 1}",
            start_date=date(current_year, 8, 1),
            end_date=date(current_year + 1, 6, 30),
            is_active=True
        )
        db.session.add(school_year)
        db.session.commit()
        print(f"Created school year: {school_year.name}")
        
        # Create a default director user
        director_user = User(
            username='director',
            password_hash=generate_password_hash('director123'),
            role='Director'
        )
        db.session.add(director_user)
        db.session.commit()
        print("Created director user")
        
        print("Database recreation completed successfully!")

if __name__ == '__main__':
    recreate_database() 