#!/usr/bin/env python3
"""
Script to clean up test data from the database.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import TeacherWorkDay, SchoolBreak

def cleanup_test_data():
    """Clean up test data from the database."""
    app = create_app()
    
    with app.app_context():
        try:
            print("🧹 Cleaning up test data...")
            
            # Delete all teacher work days
            work_days = TeacherWorkDay.query.all()
            for wd in work_days:
                db.session.delete(wd)
            print(f"🗑️  Deleted {len(work_days)} teacher work days")
            
            # Delete all school breaks
            breaks = SchoolBreak.query.all()
            for br in breaks:
                db.session.delete(br)
            print(f"🗑️  Deleted {len(breaks)} school breaks")
            
            db.session.commit()
            print("✅ Test data cleaned up successfully!")
            
            # Verify cleanup
            remaining_work_days = TeacherWorkDay.query.count()
            remaining_breaks = SchoolBreak.query.count()
            print(f"📊 Remaining records: {remaining_work_days} work days, {remaining_breaks} breaks")
            
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning up test data: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("=" * 50)
    print("TEST DATA CLEANUP")
    print("=" * 50)
    
    success = cleanup_test_data()
    
    if success:
        print("🎉 Cleanup completed successfully!")
    else:
        print("💥 Cleanup failed!")
    
    print("=" * 50)
