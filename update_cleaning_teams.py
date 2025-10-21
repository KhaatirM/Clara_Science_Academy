#!/usr/bin/env python3
"""
Script to update cleaning team assignments:
1. Remove Mason Jackson from team 2
2. Add Major Sharif to team 2
3. Assign specific duties/areas to teams
"""

from app import create_app
from extensions import db
from models import Student, CleaningTeam, CleaningTeamMember

app = create_app()

def main():
    with app.app_context():
        print("="*70)
        print("CLEANING TEAM UPDATE SCRIPT")
        print("="*70)
        
        # Step 1: Find Mason Jackson and remove from Cleanup Team 2
        print("\n[1] Finding Mason Jackson...")
        mason = Student.query.filter_by(first_name="Mason", last_name="Jackson").first()
        mason_in_team_2 = None
        
        if mason:
            print(f"    Found: {mason.first_name} {mason.last_name} (ID: {mason.id})")
            
            # Find team 2
            team_2 = CleaningTeam.query.filter(
                CleaningTeam.team_name.like("%Team 2%")
            ).first()
            
            if team_2:
                print(f"    Found: {team_2.team_name}")
                mason_in_team_2 = CleaningTeamMember.query.filter_by(
                    student_id=mason.id, 
                    team_id=team_2.id,
                    is_active=True
                ).first()
                
                if mason_in_team_2:
                    print(f"    Found Mason in {team_2.team_name} (Role: {mason_in_team_2.role})")
                    print(f"    Removing Mason from {team_2.team_name}...")
                    db.session.delete(mason_in_team_2)
                    db.session.commit()
                    print(f"    ✓ Mason removed from {team_2.team_name}")
                else:
                    print(f"    Mason is not currently in {team_2.team_name}")
            else:
                print(f"    ✗ Cleanup Team 2 not found!")
        else:
            print(f"    ✗ Mason Jackson not found!")
        
        # Step 2: Find Major Sharif and add to Cleanup Team 2
        print("\n[2] Finding Major Sharif...")
        major = Student.query.filter_by(first_name="Major", last_name="Sharif").first()
        if major:
            print(f"    Found: {major.first_name} {major.last_name} (ID: {major.id})")
            
            # Add him to team 2
            if team_2:
                # Check if he's already in team 2
                existing = CleaningTeamMember.query.filter_by(
                    student_id=major.id,
                    team_id=team_2.id,
                    is_active=True
                ).first()
                
                if existing:
                    print(f"    Major is already in {team_2.team_name} (Role: {existing.role})")
                else:
                    # Use the same role Mason had, or default to "Member"
                    role = mason_in_team_2.role if mason_in_team_2 else "Member"
                    new_member = CleaningTeamMember()
                    new_member.team_id = team_2.id
                    new_member.student_id = major.id
                    new_member.role = role
                    new_member.is_active = True
                    
                    db.session.add(new_member)
                    db.session.commit()
                    print(f"    ✓ Major Sharif added to {team_2.team_name} (Role: {role})")
            else:
                print(f"    ✗ Cannot add to {team_2.team_name} - team not found!")
        else:
            print(f"    ✗ Major Sharif not found!")
        
        # Step 3: Assign specific duties to each team member
        print("\n[3] Assigning specific duties and areas...")
        
        # Get Team 1
        team_1 = CleaningTeam.query.filter(
            CleaningTeam.team_name.like("%Team 1%")
        ).first()
        
        if team_1:
            print(f"\n    {team_1.team_name}:")
            # Assign roles for team 1 members
            team_1_assignments = {
                "Julien John": ("Sweeping Team", "Sweep all four classrooms and hallways"),
                "Jayden Hope": ("Wipe Down Team", "Wipe down tables and surfaces in all classrooms"),
                "Brendan Tinsley": ("Trash Team", "Empty trash in all classrooms and hallways")
            }
            
            for student_name, (role, area) in team_1_assignments.items():
                first, last = student_name.split()
                student = Student.query.filter_by(first_name=first, last_name=last).first()
                if student:
                    member = CleaningTeamMember.query.filter_by(
                        team_id=team_1.id,
                        student_id=student.id,
                        is_active=True
                    ).first()
                    if member:
                        member.role = f"{role} - {area}"
                        print(f"      ✓ {student_name}: {role} - {area}")
        
        if team_2:
            print(f"\n    {team_2.team_name}:")
            # Assign roles for team 2 members
            team_2_assignments = {
                "Julien Amani": ("Bathroom Team", "Clean and restock both bathrooms"),
                "Josue Perez": ("Sweeping Team", "Sweep all four classrooms and hallways"),
                "Major Sharif": ("Wipe Down Team", "Wipe down tables and surfaces in all classrooms")
            }
            
            for student_name, (role, area) in team_2_assignments.items():
                first, last = student_name.split()
                student = Student.query.filter_by(first_name=first, last_name=last).first()
                if student:
                    member = CleaningTeamMember.query.filter_by(
                        team_id=team_2.id,
                        student_id=student.id,
                        is_active=True
                    ).first()
                    if member:
                        member.role = f"{role} - {area}"
                        print(f"      ✓ {student_name}: {role} - {area}")
        
        db.session.commit()
        print(f"\n    ✓ All duties assigned!")
        
        # Step 4: Show current team compositions
        print("\n[4] Final Team Compositions:")
        teams = CleaningTeam.query.filter_by(is_active=True).all()
        
        for team in teams:
            print(f"\n    {team.team_name}")
            print(f"    Description: {team.team_description}")
            members = CleaningTeamMember.query.filter_by(
                team_id=team.id, 
                is_active=True
            ).all()
            
            if members:
                for member in members:
                    student = Student.query.get(member.student_id)
                    if student:
                        print(f"      • {student.first_name} {student.last_name}")
                        print(f"        Role: {member.role}")
            else:
                print(f"      (No active members)")
        
        print("\n" + "="*70)
        print("UPDATE COMPLETE")
        print("="*70)

if __name__ == "__main__":
    main()

