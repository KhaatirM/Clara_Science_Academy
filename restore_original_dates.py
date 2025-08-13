#!/usr/bin/env python3
"""
Script to restore original academic period dates.
"""

from app import create_app, db
from models import SchoolYear, AcademicPeriod
from datetime import date

def restore_original_dates():
    """Restore original academic period dates for 2025-2026."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== RESTORING ORIGINAL DATES ===\n")
            
            # Get the active school year
            active_year = SchoolYear.query.filter_by(is_active=True).first()
            if not active_year:
                print("❌ No active school year found.")
                return
            
            print(f"Active School Year: {active_year.name}")
            
            # Restore original school year dates
            active_year.start_date = date(2025, 8, 5)
            active_year.end_date = date(2026, 5, 29)
            
            # Get academic periods
            academic_periods = AcademicPeriod.query.filter_by(school_year_id=active_year.id).all()
            period_map = {p.name: p for p in academic_periods}
            
            # Restore original quarter dates
            if 'Quarter 1' in period_map:
                period_map['Quarter 1'].start_date = date(2025, 8, 5)
                period_map['Quarter 1'].end_date = date(2025, 10, 17)
            
            if 'Quarter 2' in period_map:
                period_map['Quarter 2'].start_date = date(2025, 10, 18)
                period_map['Quarter 2'].end_date = date(2025, 12, 30)
            
            if 'Quarter 3' in period_map:
                period_map['Quarter 3'].start_date = date(2025, 12, 31)
                period_map['Quarter 3'].end_date = date(2026, 3, 14)
            
            if 'Quarter 4' in period_map:
                period_map['Quarter 4'].start_date = date(2026, 3, 15)
                period_map['Quarter 4'].end_date = date(2026, 5, 29)
            
            # Restore original semester dates
            if 'Semester 1' in period_map:
                period_map['Semester 1'].start_date = date(2025, 8, 5)
                period_map['Semester 1'].end_date = date(2025, 12, 30)
            
            if 'Semester 2' in period_map:
                period_map['Semester 2'].start_date = date(2025, 12, 31)
                period_map['Semester 2'].end_date = date(2026, 5, 29)
            
            # Commit changes
            db.session.commit()
            
            print("✅ Original dates restored successfully!")
            print("\nRestored Academic Periods:")
            for period in academic_periods:
                print(f"  {period.name}: {period.start_date} to {period.end_date}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    restore_original_dates()
