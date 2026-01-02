#!/usr/bin/env python3
"""
Production Fix Script for Cleaning Teams - SHORT ROLES VERSION
Run this on Render shell to fix the team assignments with shorter role names
"""

from app import create_app
from extensions import db
from models import Student, CleaningTeam, CleaningTeamMember

app = create_app()

def main():
    with app.app_context():
        print("="*70)
        print("PRODUCTION CLEANING TEAM FIX - SHORT ROLES")
        print("="*70)
        
        # Step 1: Find and remove Mason Jackson from Team 2
        print("\n[1] Removing Mason Jackson from Team 2...")
        mason = Student.query.filter_by(first_name="Mason", last_name="Jackson").first()
        team_2 = CleaningTeam.query.filter(
            CleaningTeam.team_name.like("%Team 2%")
        ).first()
        
        if mason and team_2:
            print(f"    Found Mason: {mason.first_name} {mason.last_name} (ID: {mason.id})")
            print(f"    Found Team: {team_2.team_name}")
            
            # Remove Mason from Team 2
            mason_team_2 = CleaningTeamMember.query.filter_by(
                student_id=mason.id,
                team_id=team_2.id,
                is_active=True
            ).first()
            
            if mason_team_2:
                print(f"    Removing Mason from {team_2.team_name}...")
                db.session.delete(mason_team_2)
                db.session.commit()
                print(f"    ✓ Mason removed from {team_2.team_name}")
            else:
                print(f"    Mason not found in {team_2.team_name}")
        else:
            print(f"    ✗ Could not find Mason or Team 2")
        
        # Step 2: Add Major Sharif to Team 2 with short role
        print("\n[2] Adding Major Sharif to Team 2...")
        major = Student.query.filter_by(first_name="Major", last_name="Sharif").first()
        
        if major and team_2:
            print(f"    Found Major: {major.first_name} {major.last_name} (ID: {major.id})")
            
            # Check if Major is already in Team 2
            existing = CleaningTeamMember.query.filter_by(
                student_id=major.id,
                team_id=team_2.id,
                is_active=True
            ).first()
            
            if existing:
                print(f"    Major already in {team_2.team_name}")
            else:
                # Add Major to Team 2 with short role name
                new_member = CleaningTeamMember()
                new_member.team_id = team_2.id
                new_member.student_id = major.id
                new_member.role = "Wipe Down Team"  # Short role name
                new_member.is_active = True
                
                db.session.add(new_member)
                db.session.commit()
                print(f"    ✓ Major Sharif added to {team_2.team_name}")
        else:
            print(f"    ✗ Could not find Major or Team 2")
        
        # Step 3: Assign specific duties to all team members (short roles)
        print("\n[3] Assigning specific duties to all team members...")
        
        # Team 1 assignments (short roles)
        team_1 = CleaningTeam.query.filter(
            CleaningTeam.team_name.like("%Team 1%")
        ).first()
        
        if team_1:
            print(f"\n    {team_1.team_name}:")
            team_1_assignments = {
                "Julien John": "Sweeping Team",
                "Jayden Hope": "Wipe Down Team", 
                "Brendan Tinsley": "Trash Team",
                "Mason Jackson": "General Cleaning"
            }
            
            for student_name, role in team_1_assignments.items():
                first, last = student_name.split()
                student = Student.query.filter_by(first_name=first, last_name=last).first()
                if student:
                    member = CleaningTeamMember.query.filter_by(
                        team_id=team_1.id,
                        student_id=student.id,
                        is_active=True
                    ).first()
                    if member:
                        member.role = role
                        print(f"      ✓ {student_name}: {role}")
        
        # Team 2 assignments (short roles)
        if team_2:
            print(f"\n    {team_2.team_name}:")
            team_2_assignments = {
                "Julien Amani": "Bathroom Team",
                "Josue Perez": "Sweeping Team",
                "Major Sharif": "Wipe Down Team"
            }
            
            for student_name, role in team_2_assignments.items():
                first, last = student_name.split()
                student = Student.query.filter_by(first_name=first, last_name=last).first()
                if student:
                    member = CleaningTeamMember.query.filter_by(
                        team_id=team_2.id,
                        student_id=student.id,
                        is_active=True
                    ).first()
                    if member:
                        member.role = role
                        print(f"      ✓ {student_name}: {role}")
        
        db.session.commit()
        print(f"\n    ✓ All duties assigned!")
        
        # Step 4: Verify the changes
        print("\n[4] Verifying changes...")
        
        if team_2:
            print(f"\n    {team_2.team_name} members:")
            members = CleaningTeamMember.query.filter_by(
                team_id=team_2.id,
                is_active=True
            ).all()
            
            for member in members:
                student = Student.query.get(member.student_id)
                if student:
                    print(f"      • {student.first_name} {student.last_name}")
                    print(f"        Role: {member.role}")
        
        print("\n" + "="*70)
        print("PRODUCTION FIX COMPLETE")
        print("="*70)

if __name__ == "__main__":
    main()
