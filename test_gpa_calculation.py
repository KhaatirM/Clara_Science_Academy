from app import create_app
from models import db, Student, Grade
import json

def test_gpa_calculation():
    """Test the GPA calculation functionality"""
    app = create_app()
    
    with app.app_context():
        print("Testing GPA calculation...")
        
        # Get all students
        students = Student.query.all()
        
        for student in students:
            print(f"\nStudent: {student.first_name} {student.last_name}")
            print(f"Current GPA in database: {student.gpa}")
            
            # Get all grades for the student
            grades = Grade.query.filter_by(student_id=student.id).all()
            
            if not grades:
                print("  No grades found - GPA should be 0.0")
                # Update the student's GPA to 0.0
                student.gpa = 0.0
            else:
                print(f"  Found {len(grades)} grades:")
                
                total_points = 0
                total_assignments = 0
                
                for grade in grades:
                    try:
                        grade_data = json.loads(grade.grade_data)
                        score = grade_data.get('score', 0)
                        print(f"    Assignment {grade.assignment_id}: {score}%")
                        
                        # Convert percentage to GPA
                        if score >= 90:
                            gpa_points = 4.0
                        elif score >= 80:
                            gpa_points = 3.0
                        elif score >= 70:
                            gpa_points = 2.0
                        elif score >= 60:
                            gpa_points = 1.0
                        else:
                            gpa_points = 0.0
                        
                        total_points += gpa_points
                        total_assignments += 1
                        
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"    Error parsing grade: {e}")
                        continue
                
                if total_assignments > 0:
                    calculated_gpa = round(total_points / total_assignments, 2)
                    print(f"  Calculated GPA: {calculated_gpa}")
                    student.gpa = calculated_gpa
                else:
                    print("  No valid grades found - GPA set to 0.0")
                    student.gpa = 0.0
        
        # Commit all changes
        db.session.commit()
        print("\nGPA calculation test completed!")

if __name__ == "__main__":
    test_gpa_calculation() 