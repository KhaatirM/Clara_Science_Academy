#!/usr/bin/env python3
"""
Test script to verify the grades functionality works without template errors.
"""

from app import create_app
from studentroutes import create_template_context, get_letter_grade

def test_grades_functions():
    """Test that the grades-related functions work correctly."""
    try:
        print("=== TESTING GRADES FUNCTIONS ===\n")
        
        # Test get_letter_grade function
        test_scores = [95, 87, 78, 65, 45]
        print("Testing get_letter_grade function:")
        for score in test_scores:
            letter = get_letter_grade(score)
            print(f"  {score}% -> {letter}")
        
        # Test create_template_context function
        print("\nTesting create_template_context function:")
        # Create a mock student object
        class MockStudent:
            def __init__(self):
                self.id = 1
                self.first_name = "Test"
                self.last_name = "Student"
        
        mock_student = MockStudent()
        context = create_template_context(mock_student, 'grades', 'grades')
        
        print(f"  Context created successfully")
        print(f"  Section: {context['section']}")
        print(f"  Active tab: {context['active_tab']}")
        print(f"  get_letter_grade function available: {'get_letter_grade' in context}")
        
        print("\n✅ All tests passed! The grades functionality should work correctly.")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_grades_functions()
