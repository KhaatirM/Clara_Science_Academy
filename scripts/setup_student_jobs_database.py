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
        print("\nSetting up default cleaning teams...")
        
        # Team 1: 4 Classrooms & Hallway Trash
        team1 = CleaningTeam.query.filter_by(team_name="Team 1").first()
        if not team1:
            team1 = CleaningTeam(
                team_name="Team 1",
                team_description="4 Classrooms & Hallway Trash",
                is_active=True
            )
            db.session.add(team1)
            print("✓ Created Team 1")
        else:
            print("✓ Team 1 already exists")
        
        # Team 2: 4 Classrooms & Bathrooms
        team2 = CleaningTeam.query.filter_by(team_name="Team 2").first()
        if not team2:
            team2 = CleaningTeam(
                team_name="Team 2",
                team_description="4 Classrooms & Bathrooms",
                is_active=True
            )
            db.session.add(team2)
            print("✓ Created Team 2")
        else:
            print("✓ Team 2 already exists")
        
        db.session.commit()
        
        # Create default tasks for each team
        print("\nSetting up default cleaning tasks...")
        
        # Team 1 Tasks
        team1_tasks = [
            {
                'task_name': 'Sweeping Team',
                'task_description': 'Sweep all four classrooms.',
                'area_covered': 'all four classrooms'
            },
            {
                'task_name': 'Wipe Down Team', 
                'task_description': 'Wipe down all tables and desks in the four classrooms.',
                'area_covered': 'all four classrooms'
            },
            {
                'task_name': 'Trash Team',
                'task_description': 'Replace liners in all four classroom trash cans and all hallway trash cans.',
                'area_covered': 'all four classrooms and hallway trash cans'
            }
        ]
        
        for task_data in team1_tasks:
            existing_task = CleaningTask.query.filter_by(
                team_id=team1.id, 
                task_name=task_data['task_name']
            ).first()
            if not existing_task:
                task = CleaningTask(
                    team_id=team1.id,
                    task_name=task_data['task_name'],
                    task_description=task_data['task_description'],
                    area_covered=task_data['area_covered'],
                    is_active=True
                )
                db.session.add(task)
                print(f"✓ Created Team 1 task: {task_data['task_name']}")
        
        # Team 2 Tasks
        team2_tasks = [
            {
                'task_name': 'Sweeping Team',
                'task_description': 'Sweep all four classrooms.',
                'area_covered': 'all four classrooms'
            },
            {
                'task_name': 'Wipe Down Team',
                'task_description': 'Wipe down all tables and desks in the four classrooms.',
                'area_covered': 'all four classrooms'
            },
            {
                'task_name': 'Bathroom Team',
                'task_description': 'Sweep both Male and Female restrooms, replace trash cans, and restock all paper products and soap.',
                'area_covered': 'both Male and Female restrooms'
            }
        ]
        
        for task_data in team2_tasks:
            existing_task = CleaningTask.query.filter_by(
                team_id=team2.id,
                task_name=task_data['task_name']
            ).first()
            if not existing_task:
                task = CleaningTask(
                    team_id=team2.id,
                    task_name=task_data['task_name'],
                    task_description=task_data['task_description'],
                    area_covered=task_data['area_covered'],
                    is_active=True
                )
                db.session.add(task)
                print(f"✓ Created Team 2 task: {task_data['task_name']}")
        
        db.session.commit()
        
        # Create sample team members (if students exist)
        print("\nSetting up sample team members...")
        students = Student.query.limit(16).all()
        
        if students:
            # Team 1 Members (first 8 students)
            team1_members_data = [
                {'name': 'Mason Jackson', 'role': 'Sweeping Team'},
                {'name': 'Julien John', 'role': 'Sweeping Team'},
                {'name': 'Ester Hope', 'role': 'Sweeping Team'},
                {'name': 'Nathan Cassidy', 'role': 'Wipe Down Team'},
                {'name': 'Brendan Tinsley', 'role': 'Wipe Down Team'},
                {'name': 'Ty\'mier Crandell', 'role': 'Trash Team'},
                {'name': 'Miracle Heuston', 'role': 'Trash Team'},
                {'name': 'Emack Akili', 'role': 'Trash Team'}
            ]
            
            for i, member_data in enumerate(team1_members_data):
                if i < len(students):
                    existing_member = CleaningTeamMember.query.filter_by(
                        team_id=team1.id,
                        student_id=students[i].id
                    ).first()
                    if not existing_member:
                        member = CleaningTeamMember(
                            team_id=team1.id,
                            student_id=students[i].id,
                            role=member_data['role'],
                            is_active=True
                        )
                        db.session.add(member)
                        print(f"✓ Added {students[i].first_name} {students[i].last_name} to Team 1 ({member_data['role']})")
            
            # Team 2 Members (next 8 students)
            team2_members_data = [
                {'name': 'Mason Jackson', 'role': 'Bathroom Team'},
                {'name': 'Julien Amani', 'role': 'Sweeping Team'},
                {'name': 'Kya Patterson', 'role': 'Wipe Down Team'},
                {'name': 'Jayden Hope', 'role': 'Wipe Down Team'},
                {'name': 'Elimine', 'role': 'Sweeping Team'},
                {'name': 'Josue Perez', 'role': 'Bathroom Team'},
                {'name': 'Zatianna Bennett', 'role': 'Bathroom Team'},
                {'name': 'Mwajuma Abubakari', 'role': 'Bathroom Team'}
            ]
            
            for i, member_data in enumerate(team2_members_data):
                if i + 8 < len(students):
                    existing_member = CleaningTeamMember.query.filter_by(
                        team_id=team2.id,
                        student_id=students[i + 8].id
                    ).first()
                    if not existing_member:
                        member = CleaningTeamMember(
                            team_id=team2.id,
                            student_id=students[i + 8].id,
                            role=member_data['role'],
                            is_active=True
                        )
                        db.session.add(member)
                        print(f"✓ Added {students[i + 8].first_name} {students[i + 8].last_name} to Team 2 ({member_data['role']})")
        else:
            print("⚠ No students found in database. Team members will need to be added manually.")
        
        db.session.commit()
        
        # Create sample inspection (optional)
        print("\nCreating sample inspection...")
        existing_inspection = CleaningInspection.query.filter_by(
            team_id=team1.id,
            inspector_name="System Setup"
        ).first()
        
        if not existing_inspection:
            sample_inspection = CleaningInspection(
                team_id=team1.id,
                inspection_date=date.today(),
                inspector_name="System Setup",
                inspector_notes="Initial system setup - perfect score for demonstration",
                starting_score=100,
                major_deductions=0,
                moderate_deductions=0,
                minor_deductions=0,
                bonus_points=5,
                final_score=105,
                exceptional_finish=True
            )
            db.session.add(sample_inspection)
            print("✓ Created sample inspection for Team 1")
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("STUDENT JOBS DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print()
        print("✓ Database tables created")
        print("✓ Default teams configured")
        print("✓ Cleaning tasks set up")
        print("✓ Sample team members assigned")
        print("✓ Sample inspection created")
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
