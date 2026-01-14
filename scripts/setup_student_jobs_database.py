#!/usr/bin/env python3
"""
Student Jobs Database Setup Script for Render Shell
Run this script on Render's shell to create the Student Jobs database tables.

Usage on Render:
1. Go to your Render dashboard
2. Navigate to your web service
3. Click on "Shell" tab
4. Run: python setup_student_jobs_database.py
"""

import os
import sys
from datetime import datetime, date, time

# Add the current directory to Python path
sys.path.append(os.getcwd())

try:
    from app import create_app
    from config import ProductionConfig
    from models import (
        db, CleaningTeam, CleaningTeamMember, CleaningInspection, 
        CleaningTask, CleaningSchedule, Student
    )
    
    print("=" * 60)
    print("STUDENT JOBS DATABASE SETUP")
    print("=" * 60)
    print()
    
    # Create Flask app with production config
    app = create_app(config_class=ProductionConfig)
    
    with app.app_context():
        print("✓ Flask app created successfully")
        
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✓ All database tables created successfully")
        
        # Create default teams if they don't exist
        print("\nSetting up default teams...")
        
        # Cleaning Team 1
        team1 = CleaningTeam.query.filter_by(team_name="Cleaning Team 1").first()
        if not team1:
            team1 = CleaningTeam(
                team_name="Cleaning Team 1",
                team_description="Cleaning duties for 3rd-5th, 6th-8th, and K classrooms plus common areas",
                team_type="cleaning",
                is_active=True
            )
            db.session.add(team1)
            print("✓ Created Cleaning Team 1")
        else:
            print("✓ Cleaning Team 1 already exists")
        
        # Cleaning Team 2
        team2 = CleaningTeam.query.filter_by(team_name="Cleaning Team 2").first()
        if not team2:
            team2 = CleaningTeam(
                team_name="Cleaning Team 2",
                team_description="Cleaning duties for 3rd-5th, 6th-8th, and K classrooms plus common areas",
                team_type="cleaning",
                is_active=True
            )
            db.session.add(team2)
            print("✓ Created Cleaning Team 2")
        else:
            print("✓ Cleaning Team 2 already exists")
        
        # Computer Team
        computer_team = CleaningTeam.query.filter_by(team_name="Computer Team").first()
        if not computer_team:
            computer_team = CleaningTeam(
                team_name="Computer Team",
                team_description="Manage and organize all computers, cords, and chromebooks in the office cabinet",
                team_type="computer",
                is_active=True
            )
            db.session.add(computer_team)
            print("✓ Created Computer Team")
        else:
            print("✓ Computer Team already exists")
        
        # Backup Computer Team
        backup_computer_team = CleaningTeam.query.filter_by(team_name="Backup Computer Team").first()
        if not backup_computer_team:
            backup_computer_team = CleaningTeam(
                team_name="Backup Computer Team",
                team_description="Backup team for managing and organizing all computers, cords, and chromebooks",
                team_type="computer",
                is_active=True
            )
            db.session.add(backup_computer_team)
            print("✓ Created Backup Computer Team")
        else:
            print("✓ Backup Computer Team already exists")
        
        db.session.commit()
        
        # Note: Tasks are no longer used - teams now have detailed descriptions instead
        # The detailed descriptions are handled in the route's get_team_detailed_description function
        print("\nNote: Teams now use detailed descriptions instead of individual tasks.")
        print("Detailed descriptions are automatically generated based on team name and type.")
        
        db.session.commit()
        
        # Note: Team members should be added manually through the web interface
        # This allows teachers and administrators to assign students to teams as needed
        print("\nNote: Team members should be added through the Student Jobs interface.")
        print("Teachers and administrators can add members to teams using the 'Add Members' button.")
        
        db.session.commit()
        
        # Note: Inspections should be created through the web interface
        print("\nNote: Inspections should be conducted through the Student Jobs interface.")
        print("Use the 'Conduct Inspection' button to record team inspections.")
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("STUDENT JOBS DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print()
        print("✓ Database tables created")
        print("✓ Default teams configured:")
        print("  - Cleaning Team 1")
        print("  - Cleaning Team 2")
        print("  - Computer Team")
        print("  - Backup Computer Team")
        print("✓ Teams are ready for member assignment and inspections")
        print()
        print("The Student Jobs system is now ready to use!")
        print("You can access it through the 'Student Jobs' tab in the management interface.")
        
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)
except Exception as e:
    print(f"Error setting up database: {e}")
    print("Please check your database connection and try again.")
    sys.exit(1)
