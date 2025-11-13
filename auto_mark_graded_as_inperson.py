"""
Automatic Submission Status Update for Graded Assignments

This script automatically marks ALL submissions that have grades as 'in_person'.
This is useful for retroactively updating existing data where physical papers
were collected and graded.

Run this on Render Shell:
    python auto_mark_graded_as_inperson.py
"""

from app import create_app, db
from models import Submission, Grade
from datetime import datetime

def auto_mark_graded_as_inperson():
    """Automatically mark all graded submissions as in-person."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 70)
            print("AUTO-MARK GRADED ASSIGNMENTS AS IN-PERSON SUBMISSIONS")
            print("=" * 70)
            
            # Get all submissions
            all_submissions = Submission.query.all()
            total_submissions = len(all_submissions)
            
            print(f"\n📊 Found {total_submissions} total submissions")
            print("\n🔍 Checking which ones have grades...")
            
            updated_count = 0
            already_inperson_count = 0
            no_grade_count = 0
            
            for submission in all_submissions:
                # Skip if already marked as in_person
                if submission.submission_type == 'in_person':
                    already_inperson_count += 1
                    continue
                
                # Check if there's a grade for this submission
                grade = Grade.query.filter_by(
                    student_id=submission.student_id,
                    assignment_id=submission.assignment_id
                ).first()
                
                if grade:
                    # Has a grade, so mark as in_person
                    submission.submission_type = 'in_person'
                    
                    # Add note if it doesn't have one already
                    if not submission.submission_notes:
                        submission.submission_notes = 'Auto-marked as in-person (graded assignment)'
                    
                    updated_count += 1
                else:
                    # No grade yet
                    no_grade_count += 1
            
            # Show summary before committing
            print("\n" + "=" * 70)
            print("SUMMARY OF CHANGES")
            print("=" * 70)
            print(f"\n📝 Will update: {updated_count} submission(s)")
            print(f"✅ Already marked as in-person: {already_inperson_count}")
            print(f"⏸️  No grade (will skip): {no_grade_count}")
            print(f"📊 Total checked: {total_submissions}")
            
            if updated_count > 0:
                print("\n" + "=" * 70)
                confirm = input("\n⚠️  Proceed with updating these submissions? (yes/no): ")
                
                if confirm.lower() in ['yes', 'y']:
                    db.session.commit()
                    
                    print("\n" + "=" * 70)
                    print("✅ UPDATE COMPLETE!")
                    print("=" * 70)
                    print(f"\n🎉 Successfully updated {updated_count} submission(s) to 'in_person'")
                    print("\n✨ All graded assignments are now marked as in-person submissions!")
                    print("\nℹ️  Students can now see their submission status reflected correctly.")
                else:
                    db.session.rollback()
                    print("\n❌ Update cancelled. No changes made.")
            else:
                print("\n✅ All graded submissions are already marked as in-person!")
                print("   Nothing to update.")
                
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during update: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    auto_mark_graded_as_inperson()

