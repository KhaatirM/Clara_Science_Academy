#!/usr/bin/env python3
"""
Script to reorganize cleaning teams according to new requirements:
1. Switch Jayden and Nathan between teams
2. Add Bathroom duty to Team 1
3. Add Trash duty to Team 2
4. Set Mason Jackson to work Monday & Wednesday for both teams with separate score
5. Set Major as individual cleaner for Fridays with separate score
"""

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import Student, CleaningTeam, CleaningTeamMember

def reorganize_teams():
    """Reorganize cleaning teams according to new structure"""
    app = create_app()
    with app.app_context():
        try:
            print("Starting cleaning team reorganization...")
            
            # Get all students by name
            jayden = Student.query.filter_by(first_name='Jayden').first()
            nathan = Student.query.filter_by(first_name='Nathan').first()
            mason = Student.query.filter_by(first_name='Mason', last_name='Jackson').first()
            major = Student.query.filter_by(first_name='Major').first()
            
            if not jayden:
                print("Warning: Jayden not found")
            if not nathan:
                print("Warning: Nathan not found")
            if not mason:
                print("Warning: Mason Jackson not found")
            if not major:
                print("Warning: Major not found")
            
            # Get teams
            team1 = CleaningTeam.query.filter_by(team_name='Team 1').first()
            team2 = CleaningTeam.query.filter_by(team_name='Team 2').first()
            
            if not team1:
                print("Error: Team 1 not found")
                return
            if not team2:
                print("Error: Team 2 not found")
                return
            
            print(f"Found Team 1: {team1.team_description}")
            print(f"Found Team 2: {team2.team_description}")
            
            # Update team descriptions
            team1.team_description = "4 Classrooms, Hallway Trash & Bathroom"
            team2.team_description = "4 Classrooms, Trash & Bathrooms"
            
            # Clear all existing team members
            CleaningTeamMember.query.delete()
            db.session.commit()
            print("Cleared all existing team members")
            
            # Team 1 Members (Monday & Wednesday)
            # Sweeping Team
            team1_members = [
                {'student_name': 'Amari', 'role': 'Sweeping Team'},
                {'student_name': 'Nathan', 'role': 'Wipe Down Team'},  # Switched from Jayden
                {'student_name': 'Kai', 'role': 'Trash Team'},
                {'student_name': 'Elijah', 'role': 'Bathroom Team'},  # New role
            ]
            
            # Team 2 Members (Tuesday & Thursday)
            team2_members = [
                {'student_name': 'Zion', 'role': 'Sweeping Team'},
                {'student_name': 'Jayden', 'role': 'Wipe Down Team'},  # Switched from Nathan
                {'student_name': 'Isaiah', 'role': 'Trash Team'},  # New role
                {'student_name': 'Noah', 'role': 'Bathroom Team'},
            ]
            
            # Add Team 1 members
            print("\nAdding Team 1 members:")
            for member_info in team1_members:
                student = Student.query.filter_by(first_name=member_info['student_name']).first()
                if student:
                    member = CleaningTeamMember(
                        team_id=team1.id,
                        student_id=student.id,
                        role=member_info['role'],
                        is_active=True
                    )
                    db.session.add(member)
                    print(f"  Added {student.first_name} {student.last_name} - {member_info['role']}")
                else:
                    print(f"  Warning: Student {member_info['student_name']} not found")
            
            # Add Team 2 members
            print("\nAdding Team 2 members:")
            for member_info in team2_members:
                student = Student.query.filter_by(first_name=member_info['student_name']).first()
                if student:
                    member = CleaningTeamMember(
                        team_id=team2.id,
                        student_id=student.id,
                        role=member_info['role'],
                        is_active=True
                    )
                    db.session.add(member)
                    print(f"  Added {student.first_name} {student.last_name} - {member_info['role']}")
                else:
                    print(f"  Warning: Student {member_info['student_name']} not found")
            
            # Add Mason Jackson to both teams (Monday & Wednesday)
            if mason:
                print("\nAdding Mason Jackson to both teams:")
                # Mason on Team 1 - Sweeping
                mason_team1 = CleaningTeamMember(
                    team_id=team1.id,
                    student_id=mason.id,
                    role='Sweeping Team (Mon & Wed)',
                    is_active=True
                )
                db.session.add(mason_team1)
                print(f"  Added Mason Jackson to Team 1 - Sweeping Team (Mon & Wed)")
                
                # Mason on Team 2 - Bathroom
                mason_team2 = CleaningTeamMember(
                    team_id=team2.id,
                    student_id=mason.id,
                    role='Bathroom Team (Mon & Wed)',
                    is_active=True
                )
                db.session.add(mason_team2)
                print(f"  Added Mason Jackson to Team 2 - Bathroom Team (Mon & Wed)")
            
            # Create individual team for Major (Friday)
            print("\nCreating individual team for Major:")
            major_team = CleaningTeam.query.filter_by(team_name='Individual - Major').first()
            if not major_team:
                major_team = CleaningTeam(
                    team_name='Individual - Major',
                    team_description='Entire Floor Cleaning (Friday)',
                    is_active=True
                )
                db.session.add(major_team)
                db.session.flush()  # Get the ID
                print(f"  Created Individual team for Major")
            
            if major:
                major_member = CleaningTeamMember(
                    team_id=major_team.id,
                    student_id=major.id,
                    role='Full Floor Cleaning (Friday)',
                    is_active=True
                )
                db.session.add(major_member)
                print(f"  Added Major to Individual team - Full Floor Cleaning (Friday)")
            
            # Create individual team for Mason Jackson
            print("\nCreating individual tracking for Mason Jackson:")
            mason_individual = CleaningTeam.query.filter_by(team_name='Individual - Mason Jackson').first()
            if not mason_individual:
                mason_individual = CleaningTeam(
                    team_name='Individual - Mason Jackson',
                    team_description='Works with both teams (Mon & Wed) - Separate Score',
                    is_active=True
                )
                db.session.add(mason_individual)
                print(f"  Created Individual tracking for Mason Jackson")
            
            # Commit all changes
            db.session.commit()
            print("\n✓ Cleaning team reorganization completed successfully!")
            
            # Print summary
            print("\n=== SUMMARY ===")
            print(f"Team 1: {team1.team_description}")
            print(f"  Members: {len([m for m in team1.team_members if m.is_active])}")
            print(f"Team 2: {team2.team_description}")
            print(f"  Members: {len([m for m in team2.team_members if m.is_active])}")
            if major_team:
                print(f"Individual - Major: {major_team.team_description}")
                print(f"  Members: {len([m for m in major_team.team_members if m.is_active])}")
            if mason_individual:
                print(f"Individual - Mason Jackson: {mason_individual.team_description}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during reorganization: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    reorganize_teams()

