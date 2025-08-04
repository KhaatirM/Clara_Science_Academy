from app import create_app
from models import db, TeacherStaff

def test_staff_id_generation():
    """Test the Staff ID generation functionality"""
    app = create_app()
    
    with app.app_context():
        print("Testing Staff ID generation...")
        
        # Create a test teacher/staff member
        test_staff = TeacherStaff(
            first_name='John',
            last_name='Smith',
            email='john.smith@school.com',
            department='Mathematics',
            hire_date='2023-08-15',
            position='Lead Teacher'
        )
        
        # Generate staff ID
        generated_id = test_staff.generate_staff_id()
        print(f"Staff: {test_staff.first_name} {test_staff.last_name}")
        print(f"Department: {test_staff.department}")
        print(f"Hire Date: {test_staff.hire_date}")
        print(f"Generated Staff ID: {generated_id}")
        
        # Expected: MATH081523 (Mathematics + 08/15/23)
        expected = "MATH081523"
        print(f"Expected ID: {expected}")
        print(f"Match: {generated_id == expected}")
        
        # Test with different department
        test_staff2 = TeacherStaff(
            first_name='Jane',
            last_name='Doe',
            email='jane.doe@school.com',
            department='Science',
            hire_date='2022-09-01',
            position='Teacher'
        )
        
        generated_id2 = test_staff2.generate_staff_id()
        print(f"\nStaff: {test_staff2.first_name} {test_staff2.last_name}")
        print(f"Department: {test_staff2.department}")
        print(f"Hire Date: {test_staff2.hire_date}")
        print(f"Generated Staff ID: {generated_id2}")
        
        # Expected: SCI090122 (Science + 09/01/22)
        expected2 = "SCI090122"
        print(f"Expected ID: {expected2}")
        print(f"Match: {generated_id2 == expected2}")

if __name__ == '__main__':
    test_staff_id_generation() 