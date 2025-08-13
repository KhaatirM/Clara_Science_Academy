#!/usr/bin/env python3
"""
Script to add academic periods (quarters and semesters) to the database.
"""

from app import create_app, db
from models import SchoolYear, AcademicPeriod
from datetime import date

def add_academic_periods_for_year(school_year_id):
    """Add academic periods for a specific school year by ID."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the school year by ID
            school_year = SchoolYear.query.get(school_year_id)
            if not school_year:
                raise ValueError(f"School year with ID {school_year_id} not found")
            
            # Check if academic periods already exist
            existing_periods = AcademicPeriod.query.filter_by(school_year_id=school_year.id).all()
            if existing_periods:
                # Remove existing periods
                for period in existing_periods:
                    db.session.delete(period)
                db.session.commit()
            
            # Calculate quarter and semester dates based on school year
            year_start = school_year.start_date
            year_end = school_year.end_date
            
            # Calculate quarter dates (approximately 9 weeks each)
            quarter_length = (year_end - year_start).days // 4
            
            # Create quarters with proper linking
            quarters = []
            for i in range(4):
                quarter_start = date.fromordinal(year_start.toordinal() + (i * quarter_length))
                quarter_end = date.fromordinal(year_start.toordinal() + ((i + 1) * quarter_length) - 1)
                if i == 3:  # Last quarter goes to year end
                    quarter_end = year_end
                
                quarter = AcademicPeriod(
                    school_year_id=school_year.id,
                    name=f"Quarter {i+1}",
                    period_type="quarter",
                    start_date=quarter_start,
                    end_date=quarter_end,
                    is_active=True
                )
                quarters.append(quarter)
            
            # Create semesters with proper linking to quarters
            semester1_start = year_start  # Same as Q1 start
            semester1_end = quarters[1].end_date  # Same as Q2 end
            
            semester2_start = quarters[2].start_date  # Same as Q3 start
            semester2_end = year_end  # Same as Q4 end
            
            semesters = [
                AcademicPeriod(
                    school_year_id=school_year.id,
                    name="Semester 1",
                    period_type="semester",
                    start_date=semester1_start,
                    end_date=semester1_end,
                    is_active=True
                ),
                AcademicPeriod(
                    school_year_id=school_year.id,
                    name="Semester 2",
                    period_type="semester",
                    start_date=semester2_start,
                    end_date=semester2_end,
                    is_active=True
                )
            ]
            
            # Add all periods to database
            all_periods = quarters + semesters
            for period in all_periods:
                db.session.add(period)
            
            db.session.commit()
            
            return len(all_periods)
            
        except Exception as e:
            db.session.rollback()
            raise e

def add_academic_periods():
    """Add academic periods for the current school year."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== ADDING ACADEMIC PERIODS ===\n")
            
            # Get the active school year
            school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not school_year:
                print("❌ No active school year found. Please create a school year first.")
                return
            
            print(f"✅ Found active school year: {school_year.name}")
            print(f"   Start date: {school_year.start_date}")
            print(f"   End date: {school_year.end_date}")
            
            # Check if academic periods already exist
            existing_periods = AcademicPeriod.query.filter_by(school_year_id=school_year.id).all()
            if existing_periods:
                print(f"⚠️  Academic periods already exist for {school_year.name}:")
                for period in existing_periods:
                    print(f"   - {period.name} ({period.period_type}): {period.start_date} to {period.end_date}")
                return
            
            # Use the new function
            count = add_academic_periods_for_year(school_year.id)
            
            print(f"\n✅ Successfully added {count} academic periods:")
            print(f"   - 4 Quarters (Q1, Q2, Q3, Q4)")
            print(f"   - 2 Semesters (S1, S2)")
            
            # Verify the periods were added
            added_periods = AcademicPeriod.query.filter_by(school_year_id=school_year.id).all()
            print(f"\n📋 Verification - Found {len(added_periods)} periods in database:")
            for period in added_periods:
                print(f"   - {period.name} ({period.period_type}): {period.start_date} to {period.end_date}")
            
        except Exception as e:
            print(f"❌ Error adding academic periods: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    add_academic_periods()
