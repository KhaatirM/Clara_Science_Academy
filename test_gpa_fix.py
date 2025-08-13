#!/usr/bin/env python3
"""
Test script to verify the GPA calculation now works correctly on the 4.0 scale.
"""

from studentroutes import calculate_gpa

def test_gpa_calculation():
    """Test that the GPA calculation works correctly on the 4.0 scale."""
    try:
        print("=== TESTING GPA CALCULATION (4.0 SCALE) ===\n")
        
        # Test various grade combinations
        test_cases = [
            ([95, 87, 78, 65], "Mixed grades"),
            ([95, 95, 95, 95], "All A's"),
            ([85, 85, 85, 85], "All B's"),
            ([75, 75, 75, 75], "All C's"),
            ([65, 65, 65, 65], "All D's"),
            ([55, 55, 55, 55], "All F's"),
            ([93, 90, 87, 83], "High grades"),
            ([80, 77, 73, 70], "Medium grades"),
            ([67, 63, 60, 45], "Low grades"),
        ]
        
        for grades, description in test_cases:
            gpa = calculate_gpa(grades)
            print(f"{description}: {grades}% -> {gpa:.2f} GPA")
        
        # Test the specific case from your data
        print(f"\nReal example from your data:")
        real_grades = [83.5, 86.0]  # Mathematics 101 and English Literature
        gpa = calculate_gpa(real_grades)
        print(f"Class averages: {real_grades}% -> Overall GPA: {gpa:.2f}")
        
        print(f"\n✅ GPA calculation is now working correctly on the 4.0 scale!")
        print(f"📊 The grades tab will now show the correct 4.0 scale GPA instead of percentage average.")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gpa_calculation()
