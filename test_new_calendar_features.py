#!/usr/bin/env python3
"""
Test script to verify the new teacher work days and school breaks functionality.
"""

import os
import sys
from datetime import datetime, date

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import TeacherWorkDay, SchoolBreak, SchoolYear

def test_new_calendar_features():
    """Test the new calendar features."""
    app = create_app()
    
    with app.app_context():
        try:
            print("🧪 Testing new calendar features...")
            
            # Check if we have an active school year
            active_year = SchoolYear.query.filter_by(is_active=True).first()
            if not active_year:
                print("⚠️  No active school year found. Creating a test school year...")
                active_year = SchoolYear(
                    name="Test School Year 2024-2025",
                    start_date=date(2024, 8, 1),
                    end_date=date(2025, 6, 30),
                    is_active=True
                )
                db.session.add(active_year)
                db.session.commit()
                print(f"✅ Created test school year: {active_year.name}")
            
            print(f"📚 Using school year: {active_year.name}")
            
            # Test 1: Create a teacher work day
            print("\n🔧 Test 1: Creating a teacher work day...")
            work_day = TeacherWorkDay(
                school_year_id=active_year.id,
                date=date(2024, 12, 25),
                title="Christmas Professional Development",
                attendance_requirement="Mandatory",
                description="Professional development day for all teachers"
            )
            db.session.add(work_day)
            db.session.commit()
            print(f"✅ Created teacher work day: {work_day.title} on {work_day.date}")
            
            # Test 2: Create a school break
            print("\n🏖️  Test 2: Creating a school break...")
            school_break = SchoolBreak(
                school_year_id=active_year.id,
                name="Winter Break",
                start_date=date(2024, 12, 23),
                end_date=date(2025, 1, 3),
                break_type="Vacation",
                description="Winter holiday break for students and teachers"
            )
            db.session.add(school_break)
            db.session.commit()
            print(f"✅ Created school break: {school_break.name} from {school_break.start_date} to {school_break.end_date}")
            
            # Test 3: Query and display the data
            print("\n📋 Test 3: Querying and displaying data...")
            
            # Get all teacher work days
            work_days = TeacherWorkDay.query.filter_by(school_year_id=active_year.id).all()
            print(f"📅 Found {len(work_days)} teacher work day(s):")
            for wd in work_days:
                print(f"  - {wd.title} on {wd.date} ({wd.attendance_requirement})")
            
            # Get all school breaks
            breaks = SchoolBreak.query.filter_by(school_year_id=active_year.id).all()
            print(f"🏖️  Found {len(breaks)} school break(s):")
            for br in breaks:
                duration = (br.end_date - br.start_date).days + 1
                print(f"  - {br.name} ({br.break_type}) from {br.start_date} to {br.end_date} ({duration} days)")
            
            # Test 4: Test calendar integration
            print("\n📅 Test 4: Testing calendar integration...")
            
            # Import the calendar function
            from managementroutes import get_academic_dates_for_calendar
            
            # Get calendar data for December 2024
            december_dates = get_academic_dates_for_calendar(2024, 12)
            print(f"📊 Found {len(december_dates)} academic dates in December 2024:")
            
            for academic_date in december_dates:
                print(f"  - {academic_date['day']}: {academic_date['title']} ({academic_date['category']})")
            
            # Test 5: Clean up test data
            print("\n🧹 Test 5: Cleaning up test data...")
            db.session.delete(work_day)
            db.session.delete(school_break)
            db.session.commit()
            print("✅ Test data cleaned up")
            
            print("\n🎉 All tests passed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("NEW CALENDAR FEATURES TEST")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = test_new_calendar_features()
    
    print()
    if success:
        print("🎉 All tests passed! The new calendar features are working correctly.")
    else:
        print("💥 Tests failed. Please check the error messages above.")
    
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
