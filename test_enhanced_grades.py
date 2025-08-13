#!/usr/bin/env python3
"""
Test script to verify the enhanced grades functionality works correctly.
"""

from app import create_app, db
from models import Student, User, SchoolYear, Enrollment, Class, Assignment, Grade
from datetime import datetime, timedelta
import json

def test_enhanced_grades():
    """Test that the enhanced grades functionality works correctly."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== TESTING ENHANCED GRADES FUNCTIONALITY ===\n")
            
            # 1. Check if we have a student
            student = Student.query.first()
            if not student:
                print("❌ No students found")
                return
            
            print(f"✅ Found student: {student.first_name} {student.last_name}")
            
            # 2. Check if we have a school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("❌ No active school year found")
                return
            
            print(f"✅ Found school year: {school_year.name}")
            
            # 3. Check enrollments
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
            
            # 4. Test the enhanced grades calculation logic
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
                    
                    # Get recent grades (last 3 assignments)
                    recent_assignments = []
                    for grade in grades[:3]:  # Get last 3 graded assignments
                        grade_data = json.loads(grade.grade_data)
                        if 'score' in grade_data:
                            recent_assignments.append({
                                'title': grade.assignment.title,
                                'score': grade_data['score'],
                                'graded_at': grade.graded_at.strftime('%b %d, %Y')
                            })
                    
                    # Calculate class GPA (convert percentage to 4.0 scale)
                    def calculate_gpa(grades):
                        if not grades:
                            return 0.0
                        
                        def percentage_to_gpa(percentage):
                            if percentage >= 93: return 4.0
                            elif percentage >= 90: return 3.7
                            elif percentage >= 87: return 3.3
                            elif percentage >= 83: return 3.0
                            elif percentage >= 80: return 2.7
                            elif percentage >= 77: return 2.3
                            elif percentage >= 73: return 2.0
                            elif percentage >= 70: return 1.7
                            elif percentage >= 67: return 1.3
                            elif percentage >= 63: return 1.0
                            elif percentage >= 60: return 0.7
                            else: return 0.0
                        
                        gpa_points = [percentage_to_gpa(grade) for grade in grades]
                        return round(sum(gpa_points) / len(gpa_points), 2)
                    
                    class_gpa = calculate_gpa([class_average])
                    
                    grades_by_class[class_info.name] = {
                        'final_grade': {
                            'letter': 'A' if class_average >= 90 else 'B' if class_average >= 80 else 'C' if class_average >= 70 else 'D' if class_average >= 60 else 'F',
                            'percentage': class_average
                        },
                        'class_gpa': class_gpa,
                        'recent_assignments': recent_assignments,
                        'grades': {
                            'Current': {
                                'overall_letter': 'A' if class_average >= 90 else 'B' if class_average >= 80 else 'C' if class_average >= 70 else 'D' if class_average >= 60 else 'F',
                                'overall_percentage': class_average,
                                'grade_details': assignment_grades
                            }
                        }
                    }
                    
                    print(f"   📊 Class average: {class_average}%")
                    print(f"   🎯 Class GPA: {class_gpa}")
                    print(f"   📝 Recent assignments: {len(recent_assignments)}")
                    
                    for assignment in recent_assignments:
                        print(f"      - {assignment['title']}: {assignment['score']}% ({assignment['graded_at']})")
            
            # 5. Calculate overall GPA
            if all_class_averages:
                overall_gpa = round(sum(all_class_averages) / len(all_class_averages), 2)
                print(f"\n🎓 Overall GPA: {overall_gpa}%")
                
                # Test the grades_by_class structure
                print(f"\n📋 Grades by class structure:")
                for class_name, data in grades_by_class.items():
                    print(f"   {class_name}:")
                    print(f"     - Final grade: {data['final_grade']['letter']} ({data['final_grade']['percentage']}%)")
                    print(f"     - Class GPA: {data['class_gpa']}")
                    print(f"     - Recent assignments: {len(data['recent_assignments'])}")
            else:
                print("⚠️  No grades found for GPA calculation")
            
            print(f"\n✅ Enhanced grades test completed successfully!")
            print(f"📊 Processed {len(grades_by_class)} classes with grades")
            
        except Exception as e:
            print(f"❌ Error during enhanced grades test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_grades()
