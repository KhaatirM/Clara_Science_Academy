#!/usr/bin/env python3
"""
Test script to verify that template functions are available.
"""

from studentroutes import create_template_context, get_letter_grade, calculate_gpa

def test_template_functions():
    """Test that template functions are available in the context."""
    try:
        print("=== TESTING TEMPLATE FUNCTIONS ===\n")
        
        # Test the functions directly
        print("Testing get_letter_grade function:")
        test_scores = [95, 87, 78, 65, 45]
        for score in test_scores:
            letter = get_letter_grade(score)
            print(f"  {score}% -> {letter}")
        
        print("\nTesting calculate_gpa function:")
        test_grades = [95, 87, 78, 65]
        gpa = calculate_gpa(test_grades)
        print(f"  Grades {test_grades}% -> GPA: {gpa:.2f}")
        
        # Test the template context
        print("\nTesting create_template_context function:")
        # Create a mock student object
        class MockStudent:
            def __init__(self):
                self.id = 1
                self.first_name = "Test"
                self.last_name = "Student"
        
        mock_student = MockStudent()
        context = create_template_context(mock_student, 'grades', 'grades')
        
        # Check if functions are in context
        if 'get_letter_grade' in context:
            print("✅ get_letter_grade function is in template context")
        else:
            print("❌ get_letter_grade function is missing from template context")
        
        if 'calculate_gpa' in context:
            print("✅ calculate_gpa function is in template context")
        else:
            print("❌ calculate_gpa function is missing from template context")
        
        # Test calling the functions from context
        if 'get_letter_grade' in context and 'calculate_gpa' in context:
            test_letter = context['get_letter_grade'](92)
            test_gpa = context['calculate_gpa']([92, 88, 85])
            print(f"✅ Functions work from context: 92% -> {test_letter}, GPA: {test_gpa:.2f}")
        
        print(f"\n✅ Template functions test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_template_functions()
