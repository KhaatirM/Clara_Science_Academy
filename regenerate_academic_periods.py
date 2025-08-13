#!/usr/bin/env python3
"""
Script to regenerate academic periods with new naming and linking.
"""

from app import create_app, db
from models import SchoolYear, AcademicPeriod
from add_academic_periods import add_academic_periods_for_year

def regenerate_academic_periods():
    """Regenerate academic periods for the active school year."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== REGENERATING ACADEMIC PERIODS ===\n")
            
            # Get the active school year
            active_year = SchoolYear.query.filter_by(is_active=True).first()
            if not active_year:
                print("❌ No active school year found.")
                return
            
            print(f"Active School Year: {active_year.name}")
            print(f"Start Date: {active_year.start_date}")
            print(f"End Date: {active_year.end_date}\n")
            
            # Remove existing academic periods
            existing_periods = AcademicPeriod.query.filter_by(school_year_id=active_year.id).all()
            if existing_periods:
                print(f"Removing {len(existing_periods)} existing academic periods...")
                for period in existing_periods:
                    print(f"  - {period.name}: {period.start_date} to {period.end_date}")
                    db.session.delete(period)
                db.session.commit()
                print("✅ Existing periods removed.\n")
            
            # Generate new academic periods
            print("Generating new academic periods with proper linking...")
            count = add_academic_periods_for_year(active_year.id)
            print(f"✅ Generated {count} new academic periods.\n")
            
            # Display new periods
            new_periods = AcademicPeriod.query.filter_by(school_year_id=active_year.id).all()
            print("New Academic Periods:")
            for period in new_periods:
                print(f"  {period.name}: {period.start_date} to {period.end_date}")
            
            print("\n🎉 Academic periods regenerated successfully!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    regenerate_academic_periods()
