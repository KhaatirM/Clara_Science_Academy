#!/usr/bin/env python3
"""
Test script to verify automatic date linking functionality.
"""

from app import create_app, db
from models import SchoolYear, AcademicPeriod
from datetime import date, timedelta

def test_date_linking():
    """Test the automatic date linking functionality."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== TESTING AUTOMATIC DATE LINKING ===\n")
            
            # Get the active school year
            active_year = SchoolYear.query.filter_by(is_active=True).first()
            if not active_year:
                print("❌ No active school year found. Please create one first.")
                return
            
            print(f"Active School Year: {active_year.name}")
            print(f"Current Start Date: {active_year.start_date}")
            print(f"Current End Date: {active_year.end_date}\n")
            
            # Get academic periods
            academic_periods = AcademicPeriod.query.filter_by(school_year_id=active_year.id).all()
            if not academic_periods:
                print("❌ No academic periods found. Please generate them first.")
                return
            
            print("Current Academic Periods:")
            for period in academic_periods:
                print(f"  {period.name}: {period.start_date} to {period.end_date}")
            
            print("\n" + "="*50)
            print("TESTING DATE LINKING LOGIC:")
            print("="*50)
            
            # Test 1: Verify Q1 start = S1 start = School Year start
            q1 = next((p for p in academic_periods if p.name == 'Quarter 1'), None)
            s1 = next((p for p in academic_periods if p.name == 'Semester 1'), None)
            
            if q1 and s1:
                if q1.start_date == s1.start_date == active_year.start_date:
                    print("✅ Q1 start = S1 start = School Year start")
                else:
                    print("❌ Q1 start ≠ S1 start ≠ School Year start")
                    print(f"   Q1 start: {q1.start_date}")
                    print(f"   S1 start: {s1.start_date}")
                    print(f"   School Year start: {active_year.start_date}")
            else:
                print("❌ Missing Quarter 1 or Semester 1")
            
            # Test 2: Verify Q2 end = S1 end
            q2 = next((p for p in academic_periods if p.name == 'Quarter 2'), None)
            if q2 and s1:
                if q2.end_date == s1.end_date:
                    print("✅ Q2 end = S1 end")
                else:
                    print("❌ Q2 end ≠ S1 end")
                    print(f"   Q2 end: {q2.end_date}")
                    print(f"   S1 end: {s1.end_date}")
            else:
                print("❌ Missing Quarter 2 or Semester 1")
            
            # Test 3: Verify Q3 start = S2 start
            q3 = next((p for p in academic_periods if p.name == 'Quarter 3'), None)
            s2 = next((p for p in academic_periods if p.name == 'Semester 2'), None)
            
            if q3 and s2:
                if q3.start_date == s2.start_date:
                    print("✅ Q3 start = S2 start")
                else:
                    print("❌ Q3 start ≠ S2 start")
                    print(f"   Q3 start: {q3.start_date}")
                    print(f"   S2 start: {s2.start_date}")
            else:
                print("❌ Missing Quarter 3 or Semester 2")
            
            # Test 4: Verify Q4 end = S2 end = School Year end
            q4 = next((p for p in academic_periods if p.name == 'Quarter 4'), None)
            if q4 and s2:
                if q4.end_date == s2.end_date == active_year.end_date:
                    print("✅ Q4 end = S2 end = School Year end")
                else:
                    print("❌ Q4 end ≠ S2 end ≠ School Year end")
                    print(f"   Q4 end: {q4.end_date}")
                    print(f"   S2 end: {s2.end_date}")
                    print(f"   School Year end: {active_year.end_date}")
            else:
                print("❌ Missing Quarter 4 or Semester 2")
            
            # Test 5: Verify quarter durations are approximately equal
            if q1 and q2 and q3 and q4:
                q1_duration = (q1.end_date - q1.start_date).days
                q2_duration = (q2.end_date - q2.start_date).days
                q3_duration = (q3.end_date - q3.start_date).days
                q4_duration = (q4.end_date - q4.start_date).days
                
                avg_duration = (q1_duration + q2_duration + q3_duration + q4_duration) / 4
                max_deviation = max(abs(q1_duration - avg_duration), 
                                  abs(q2_duration - avg_duration),
                                  abs(q3_duration - avg_duration),
                                  abs(q4_duration - avg_duration))
                
                if max_deviation <= 2:  # Allow 2 days deviation
                    print("✅ Quarter durations are approximately equal")
                else:
                    print("❌ Quarter durations vary significantly")
                    print(f"   Q1: {q1_duration} days")
                    print(f"   Q2: {q2_duration} days")
                    print(f"   Q3: {q3_duration} days")
                    print(f"   Q4: {q4_duration} days")
                    print(f"   Average: {avg_duration:.1f} days")
                    print(f"   Max deviation: {max_deviation} days")
            else:
                print("❌ Cannot test quarter durations - missing quarters")
            
            print("\n" + "="*50)
            print("SUMMARY:")
            print("="*50)
            
            # Count successful tests
            success_count = 0
            total_tests = 5
            
            # Re-run tests to count successes
            if q1 and s1 and q1.start_date == s1.start_date == active_year.start_date:
                success_count += 1
            if q2 and s1 and q2.end_date == s1.end_date:
                success_count += 1
            if q3 and s2 and q3.start_date == s2.start_date:
                success_count += 1
            if q4 and s2 and q4.end_date == s2.end_date == active_year.end_date:
                success_count += 1
            if q1 and q2 and q3 and q4:
                q1_duration = (q1.end_date - q1.start_date).days
                q2_duration = (q2.end_date - q2.start_date).days
                q3_duration = (q3.end_date - q3.start_date).days
                q4_duration = (q4.end_date - q4.start_date).days
                avg_duration = (q1_duration + q2_duration + q3_duration + q4_duration) / 4
                max_deviation = max(abs(q1_duration - avg_duration), 
                                  abs(q2_duration - avg_duration),
                                  abs(q3_duration - avg_duration),
                                  abs(q4_duration - avg_duration))
                if max_deviation <= 2:
                    success_count += 1
            
            print(f"Tests Passed: {success_count}/{total_tests}")
            
            if success_count == total_tests:
                print("🎉 All date linking tests passed! The system is working correctly.")
            else:
                print("⚠️  Some tests failed. You may need to regenerate academic periods.")
                print("   Use the 'Regenerate Academic Periods' button in the Academic Calendar Management page.")
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_date_linking()
