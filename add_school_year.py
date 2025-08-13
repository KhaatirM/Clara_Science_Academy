#!/usr/bin/env python3
"""
Script to add a school year for testing.
"""

from app import create_app, db
from models import SchoolYear
from datetime import date

def add_school_year():
    """Add a school year for testing."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if school year already exists
            existing = SchoolYear.query.filter_by(is_active=True).first()
            if existing:
                print(f"School year already exists: {existing.name}")
                return existing
            
            # Create a new school year
            current_year = date.today().year
            school_year = SchoolYear(
                name=f"{current_year}-{current_year + 1}",
                start_date=date(current_year, 8, 1),
                end_date=date(current_year + 1, 6, 30),
                is_active=True
            )
            db.session.add(school_year)
            db.session.commit()
            
            print(f"Created school year: {school_year.name}")
            return school_year
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    add_school_year()

