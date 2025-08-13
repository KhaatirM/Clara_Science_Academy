#!/usr/bin/env python3
"""
Test script to verify the quarters and semesters functionality works correctly.
"""

from app import create_app, db
from models import Student, User, SchoolYear, Enrollment, Class, Assignment, Grade, AcademicPeriod
from datetime import datetime, timedelta
import json

def test_quarters_semesters():
    """Test that the quarters and semesters functionality works correctly."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== TESTING QUARTERS AND SEMESTERS FUNCTIONALITY ===\n")
            
            # 1. Check academic periods
            academic_periods = AcademicPeriod.query.filter_by(is_active=True).all()
            print(f"✅ Found {len(academic_periods)} academic periods:")
            
            quarters = [p for p in academic_periods if p.period_type == 'quarter']
            semesters = [p for p in academic_periods if p.period_type == 'semester']
            
            print(f"   📅 Quarters: {len(quarters)}")
            for quarter in quarters:
                print(f"      - {quarter.name}: {quarter.start_date} to {quarter.end_date}")
            
            print(f"   📅 Semesters: {len(semesters)}")
            for semester in semesters:
                print(f"      - {semester.name}: {semester.start_date} to {semester.end_date}")
            
            # 2. Check if we have a student
            student = Student.query.first()
            if not student:
                print("❌ No students found")
                return
            
            print(f"\n✅ Found student: {student.first_name} {student.last_name}")
            
            # 3. Check if we have a school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("❌ No active school year found")
                return
            
            print(f"✅ Found school year: {school_year.name}")
            
            # 4. Check enrollments
            enrollments = Enrollment.query.filter_by(
                student_id=student.id,
                is_active=True
            ).join(Class).filter(
                Class.school_year_id == school_year.id
            ).all()
            
            if not enrollments:
                print("❌ No enrollments found")
                return
            
            print(f"✅ Found {len(enrollments)} enrollments")
            
            # 5. Test the enhanced grades calculation logic
            grades_by_class = {}
            all_class_averages = []
            
            for enrollment in enrollments:
                class_info = enrollment.class_info
                print(f"\n📚 Processing class: {class_info.name}")
                
                # Get all assignments for this class
                assignments = Assignment.query.filter(
                    Assignment.class_id == class_info.id,
                    Assignment.school_year_id == school_year.id
                ).all()
                
                if not assignments:
                    print(f"   ⚠️  No assignments found for {class_info.name}")
                    continue
                
                print(f"   ✅ Found {len(assignments)} assignments")
                
                # Get all grades for this student in this class
                grades = Grade.query.join(Assignment).filter(
                    Grade.student_id == student.id,
                    Assignment.class_id == class_info.id,
                    Assignment.school_year_id == school_year.id
                ).order_by(Grade.graded_at.desc()).all()
                
                if not grades:
                    print(f"   ⚠️  No grades found for {class_info.name}")
                    continue
                
                print(f"   ✅ Found {len(grades)} grades")
                
                # Calculate individual assignment grades
                assignment_grades = {}
                total_score = 0
                valid_grades = 0
                
                for grade in grades:
                    grade_data = json.loads(grade.grade_data)
                    if 'score' in grade_data:
                        score = grade_data['score']
                        assignment_grades[grade.assignment.title] = f"{score}%"
                        total_score += score
                        valid_grades += 1
                
                if valid_grades > 0:
                    class_average = round(total_score / valid_grades, 2)
                    all_class_averages.append(class_average)
                    
                    # Test quarter grades calculation
                    quarter_grades = {}
                    for quarter in quarters:
                        quarter_assignments = [a for a in assignments if a.quarter == quarter.name]
                        quarter_grades_list = []
                        
                        for assignment in quarter_assignments:
                            grade = next((g for g in grades if g.assignment_id == assignment.id), None)
                            if grade:
                                grade_data = json.loads(grade.grade_data)
                                if 'score' in grade_data:
                                    quarter_grades_list.append(grade_data['score'])
                        
                        if quarter_grades_list:
                            quarter_avg = round(sum(quarter_grades_list) / len(quarter_grades_list), 2)
                            quarter_grades[quarter.name] = {
                                'average': quarter_avg,
                                'letter': 'A' if quarter_avg >= 90 else 'B' if quarter_avg >= 80 else 'C' if quarter_avg >= 70 else 'D' if quarter_avg >= 60 else 'F',
                                'assignments': len(quarter_grades_list)
                            }
                            print(f"      📊 {quarter.name}: {quarter_avg}% ({len(quarter_grades_list)} assignments)")
                    
                    # Test semester grades calculation
                    semester_grades = {}
                    for semester in semesters:
                        semester_assignments = []
                        for assignment in assignments:
                            if semester.name == 'S1' and assignment.due_date.date() <= semester.end_date:
                                semester_assignments.append(assignment)
                            elif semester.name == 'S2' and assignment.due_date.date() > semester.start_date:
                                semester_assignments.append(assignment)
                        
                        semester_grades_list = []
                        for assignment in semester_assignments:
                            grade = next((g for g in grades if g.assignment_id == assignment.id), None)
                            if grade:
                                grade_data = json.loads(grade.grade_data)
                                if 'score' in grade_data:
                                    semester_grades_list.append(grade_data['score'])
                        
                        if semester_grades_list:
                            semester_avg = round(sum(semester_grades_list) / len(semester_grades_list), 2)
                            semester_grades[semester.name] = {
                                'average': semester_avg,
                                'letter': 'A' if semester_avg >= 90 else 'B' if semester_avg >= 80 else 'C' if semester_avg >= 70 else 'D' if semester_avg >= 60 else 'F',
                                'assignments': len(semester_grades_list)
                            }
                            print(f"      📊 {semester.name}: {semester_avg}% ({len(semester_grades_list)} assignments)")
                    
                    grades_by_class[class_info.name] = {
                        'final_grade': {
                            'letter': 'A' if class_average >= 90 else 'B' if class_average >= 80 else 'C' if class_average >= 70 else 'D' if class_average >= 60 else 'F',
                            'percentage': class_average
                        },
                        'quarter_grades': quarter_grades,
                        'semester_grades': semester_grades
                    }
                    
                    print(f"   📊 Class average: {class_average}%")
            
            print(f"\n✅ Quarters and semesters test completed successfully!")
            print(f"📊 Processed {len(grades_by_class)} classes with academic period organization")
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_quarters_semesters()
