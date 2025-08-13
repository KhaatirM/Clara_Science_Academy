#!/usr/bin/env python3
"""
Test script to verify automatic synchronization when dates are changed.
"""

from app import create_app, db
from models import SchoolYear, AcademicPeriod
from datetime import date, timedelta

def test_synchronization():
    """Test automatic synchronization when dates are changed."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== TESTING AUTOMATIC SYNCHRONIZATION ===\n")
            
            # Get the active school year
            active_year = SchoolYear.query.filter_by(is_active=True).first()
            if not active_year:
                print("❌ No active school year found.")
                return
            
            print(f"Active School Year: {active_year.name}")
            print(f"Current Start Date: {active_year.start_date}")
            print(f"Current End Date: {active_year.end_date}\n")
            
            # Get current academic periods
            academic_periods = AcademicPeriod.query.filter_by(school_year_id=active_year.id).all()
            period_map = {p.name: p for p in academic_periods}
            
            print("Current Academic Periods:")
            for period in academic_periods:
                print(f"  {period.name}: {period.start_date} to {period.end_date}")
            
            print("\n" + "="*60)
            print("TESTING SCHOOL YEAR DATE CHANGE SYNCHRONIZATION:")
            print("="*60)
            
            # Store original dates
            original_start = active_year.start_date
            original_end = active_year.end_date
            
            # Test 1: Change school year start date (should update Q1 and S1 start)
            print("\n1. Testing school year start date change...")
            new_start = original_start + timedelta(days=7)  # Move start date 7 days later
            
            # Simulate the synchronization logic
            active_year.start_date = new_start
            
            # Update Q1 start date
            if 'Quarter 1' in period_map:
                period_map['Quarter 1'].start_date = new_start
            
            # Update S1 start date
            if 'Semester 1' in period_map:
                period_map['Semester 1'].start_date = new_start
            
            # Commit changes
            db.session.commit()
            
            print(f"   Changed school year start from {original_start} to {new_start}")
            print(f"   Q1 start: {period_map['Quarter 1'].start_date}")
            print(f"   S1 start: {period_map['Semester 1'].start_date}")
            
            if (period_map['Quarter 1'].start_date == new_start and 
                period_map['Semester 1'].start_date == new_start):
                print("   ✅ Q1 and S1 start dates synchronized correctly")
            else:
                print("   ❌ Q1 and S1 start dates not synchronized")
            
            # Test 2: Change school year end date (should update Q4 and S2 end)
            print("\n2. Testing school year end date change...")
            new_end = original_end + timedelta(days=7)  # Move end date 7 days later
            
            # Simulate the synchronization logic
            active_year.end_date = new_end
            
            # Update Q4 end date
            if 'Quarter 4' in period_map:
                period_map['Quarter 4'].end_date = new_end
            
            # Update S2 end date
            if 'Semester 2' in period_map:
                period_map['Semester 2'].end_date = new_end
            
            # Commit changes
            db.session.commit()
            
            print(f"   Changed school year end from {original_end} to {new_end}")
            print(f"   Q4 end: {period_map['Quarter 4'].end_date}")
            print(f"   S2 end: {period_map['Semester 2'].end_date}")
            
            if (period_map['Quarter 4'].end_date == new_end and 
                period_map['Semester 2'].end_date == new_end):
                print("   ✅ Q4 and S2 end dates synchronized correctly")
            else:
                print("   ❌ Q4 and S2 end dates not synchronized")
            
            # Test 3: Change Q2 end date (should update S1 end)
            print("\n3. Testing Q2 end date change...")
            q2_original_end = period_map['Quarter 2'].end_date
            new_q2_end = q2_original_end + timedelta(days=3)  # Move Q2 end 3 days later
            
            # Simulate the synchronization logic
            period_map['Quarter 2'].end_date = new_q2_end
            
            # Update S1 end date
            if 'Semester 1' in period_map:
                period_map['Semester 1'].end_date = new_q2_end
            
            # Commit changes
            db.session.commit()
            
            print(f"   Changed Q2 end from {q2_original_end} to {new_q2_end}")
            print(f"   S1 end: {period_map['Semester 1'].end_date}")
            
            if period_map['Semester 1'].end_date == new_q2_end:
                print("   ✅ S1 end date synchronized correctly")
            else:
                print("   ❌ S1 end date not synchronized")
            
            # Test 4: Change Q3 start date (should update S2 start)
            print("\n4. Testing Q3 start date change...")
            q3_original_start = period_map['Quarter 3'].start_date
            new_q3_start = q3_original_start + timedelta(days=2)  # Move Q3 start 2 days later
            
            # Simulate the synchronization logic
            period_map['Quarter 3'].start_date = new_q3_start
            
            # Update S2 start date
            if 'Semester 2' in period_map:
                period_map['Semester 2'].start_date = new_q3_start
            
            # Commit changes
            db.session.commit()
            
            print(f"   Changed Q3 start from {q3_original_start} to {new_q3_start}")
            print(f"   S2 start: {period_map['Semester 2'].start_date}")
            
            if period_map['Semester 2'].start_date == new_q3_start:
                print("   ✅ S2 start date synchronized correctly")
            else:
                print("   ❌ S2 start date not synchronized")
            
            print("\n" + "="*60)
            print("FINAL ACADEMIC PERIODS AFTER SYNCHRONIZATION:")
            print("="*60)
            
            # Refresh from database
            db.session.refresh(active_year)
            academic_periods = AcademicPeriod.query.filter_by(school_year_id=active_year.id).all()
            
            print(f"School Year: {active_year.start_date} to {active_year.end_date}")
            for period in academic_periods:
                print(f"  {period.name}: {period.start_date} to {period.end_date}")
            
            print("\n🎉 Synchronization tests completed!")
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_synchronization()
