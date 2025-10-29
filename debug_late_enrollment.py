#!/usr/bin/env python3
"""
Debug script to check why a specific student's assignments aren't being voided.
"""

from app import create_app
from models import Student, Enrollment, Grade, Assignment, AcademicPeriod
from datetime import datetime, timedelta
from management_routes.late_enrollment_utils import (
    is_late_enrollment, 
    get_academic_period_for_assignment,
    should_void_assignment_for_student
)

def debug_all_recent_enrollments():
    """Debug all enrollments from the last 2 weeks"""
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("DEBUGGING ALL RECENT ENROLLMENTS (Last 2 weeks)")
        print("=" * 70)
        print()
        
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        recent_enrollments = Enrollment.query.filter(
            Enrollment.enrolled_at >= two_weeks_ago,
            Enrollment.is_active == True
        ).all()
        
        if not recent_enrollments:
            print("No enrollments in the last 2 weeks found.")
            return
        
        print(f"Found {len(recent_enrollments)} enrollment(s) in the last 2 weeks:\n")
        
        for enrollment in recent_enrollments:
            student = Student.query.get(enrollment.student_id)
            class_obj = enrollment.class_info
            
            print("-" * 70)
            print(f"Student: {student.first_name} {student.last_name} (ID: {student.id})")
            print(f"Class: {class_obj.name if class_obj else 'Unknown'} (ID: {enrollment.class_id})")
            print(f"Enrolled: {enrollment.enrolled_at}")
            print()
            
            # Get assignments
            assignments = Assignment.query.filter_by(class_id=enrollment.class_id).all()
            print(f"Assignments in this class: {len(assignments)}")
            
            for assignment in assignments:
                academic_period = get_academic_period_for_assignment(assignment)
                print(f"\n  Assignment: {assignment.title}")
                print(f"    Quarter: {assignment.quarter}")
                print(f"    Due: {assignment.due_date}")
                
                if academic_period:
                    is_late = is_late_enrollment(enrollment.enrolled_at, academic_period)
                    should_void = should_void_assignment_for_student(
                        student.id, assignment, enrollment
                    )
                    
                    print(f"    Period: {academic_period.name} ({academic_period.start_date} to {academic_period.end_date})")
                    print(f"    Late enrollment? {is_late}")
                    print(f"    Should void? {should_void}")
                    
                    # Check grades
                    grades = Grade.query.filter_by(
                        student_id=student.id,
                        assignment_id=assignment.id
                    ).all()
                    
                    for grade in grades:
                        is_voided = getattr(grade, 'is_voided', False)
                        void_status = "✓ VOIDED" if is_voided else "❌ NOT VOIDED (SHOULD BE!)"
                        print(f"      Grade {grade.id}: {void_status}")
                        if not is_voided and should_void:
                            print(f"        ⚠️  NEEDS TO BE VOIDED!")
                else:
                    print(f"    ⚠️  Could not find academic period!")
                    print(f"       Quarter field: '{assignment.quarter}'")
                    print(f"       School year ID: {assignment.school_year_id}")
            print()

def debug_student(student_name=None, student_id=None):
    app = create_app()
    with app.app_context():
        if student_id:
            student = Student.query.get(student_id)
        elif student_name:
            # Find the student
            student = Student.query.filter(
                (Student.first_name + ' ' + Student.last_name).like(f'%{student_name}%')
            ).first()
            
            if not student:
                # Try just last name
                student = Student.query.filter(
                    Student.last_name.like(f'%{student_name.split()[-1]}%')
                ).first()
        else:
            print("No student name or ID provided!")
            return
        
        if not student:
            print(f"❌ Student not found!")
            return
        
        print(f"✓ Found student: {student.first_name} {student.last_name} (ID: {student.id})")
        print()
        
        # Get enrollments
        enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
        
        if not enrollments:
            print("❌ No active enrollments found for this student!")
            return
        
        for enrollment in enrollments:
            print("-" * 70)
            print(f"Enrollment in Class ID: {enrollment.class_id}")
            print(f"Enrolled at: {enrollment.enrolled_at}")
            print()
            
            # Get assignments for this class
            assignments = Assignment.query.filter_by(class_id=enrollment.class_id).all()
            
            if not assignments:
                print("  No assignments found for this class.")
                continue
            
            print(f"  Found {len(assignments)} assignments:")
            print()
            
            voidable_count = 0
            voided_count = 0
            
            for assignment in assignments:
                print(f"  Assignment: {assignment.title}")
                print(f"    Quarter: {assignment.quarter}")
                print(f"    Due date: {assignment.due_date}")
                
                # Get academic period
                academic_period = get_academic_period_for_assignment(assignment)
                if academic_period:
                    print(f"    Academic Period: {academic_period.name} ({academic_period.start_date} to {academic_period.end_date})")
                    
                    # Check if late enrollment
                    is_late = is_late_enrollment(enrollment.enrolled_at, academic_period)
                    print(f"    Late enrollment? {is_late}")
                    
                    if is_late:
                        two_weeks_before = academic_period.end_date - timedelta(days=14)
                        print(f"    Enrollment date: {enrollment.enrolled_at.date()}")
                        print(f"    2 weeks before end: {two_weeks_before}")
                        print(f"    Period end: {academic_period.end_date}")
                    
                    # Check if should void
                    should_void = should_void_assignment_for_student(
                        student.id, assignment, enrollment
                    )
                    print(f"    Should void? {should_void}")
                    
                    if should_void:
                        voidable_count += 1
                else:
                    print(f"    ⚠️  Could not determine academic period for this assignment!")
                    print(f"       Assignment quarter: '{assignment.quarter}'")
                    print(f"       School year ID: {assignment.school_year_id}")
                
                # Check existing grades
                grades = Grade.query.filter_by(
                    student_id=student.id,
                    assignment_id=assignment.id
                ).all()
                
                for grade in grades:
                    is_voided = getattr(grade, 'is_voided', False)
                    void_status = "✓ VOIDED" if is_voided else "❌ NOT VOIDED"
                    print(f"      Grade ID {grade.id}: {void_status}")
                    
                    if is_voided:
                        voided_count += 1
                    elif should_void:
                        print(f"        ⚠️  This grade should be voided but isn't!")
                
                print()
            
            print(f"\n  Summary for this class:")
            print(f"    Assignments that should be voided: {voidable_count}")
            print(f"    Grades already voided: {voided_count}")
            print(f"    Grades that need voiding: {voidable_count - voided_count}")
        
        print()
        print("=" * 70)

if __name__ == "__main__":
    # Debug all recent enrollments first
    debug_all_recent_enrollments()

