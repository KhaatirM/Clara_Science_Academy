from app import create_app
from models import db, Student

def test_student_id_generation():
    """Test the Student ID generation functionality"""
    app = create_app()
    
    with app.app_context():
        print("Testing Student ID generation...")
        
        # Get the test student
        student = Student.query.filter_by(first_name='Alex').first()
        
        if student:
            print(f"Student: {student.first_name} {student.last_name}")
            print(f"DOB: {student.dob}")
            print(f"State: {student.state}")
            print(f"Generated Student ID: {student.student_id}")
            
            # Test the generation method
            generated_id = student.generate_student_id()
            print(f"Generated ID from method: {generated_id}")
            
            # Expected: TX051510 (Texas + 05/15/10)
            expected = "TX051510"
            print(f"Expected ID: {expected}")
            print(f"Match: {generated_id == expected}")
        else:
            print("No test student found!")

if __name__ == '__main__':
    test_student_id_generation() 