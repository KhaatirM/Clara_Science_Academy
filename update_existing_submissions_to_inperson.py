"""
Retroactive Update Script: Mark Existing Submissions as In-Person

This script updates all existing submissions that have grades to be marked as 'in_person'
submissions, since they were likely physical papers that were graded.

This is useful for migrating existing data after adding the manual submission tracking system.

Run this script once after installing the manual submission tracking:
    python update_existing_submissions_to_inperson.py
"""

from app import create_app, db
from models import Submission, Grade, Assignment
from datetime import datetime
from sqlalchemy import text

def update_existing_submissions():
    """Update all graded submissions to be marked as in-person."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 60)
            print("RETROACTIVE SUBMISSION UPDATE SCRIPT")
            print("=" * 60)
            print("\nThis will update existing submissions to 'in_person' type.")
            print("\nCriteria:")
            print("  - Submissions that have corresponding grades")
            print("  - Or submissions for PDF/Paper assignments")
            print("  - Will NOT touch Quiz or Discussion assignments")
            print("\n" + "=" * 60)
            
            # First, check if submission_type column exists
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('submission')]
            
            if 'submission_type' not in existing_columns:
                print("\n❌ ERROR: submission_type column doesn't exist yet!")
                print("Please run this first: python add_manual_submission_tracking.py")
                return
            
            # Get all submissions
            all_submissions = Submission.query.all()
            total_submissions = len(all_submissions)
            
            print(f"\n📊 Found {total_submissions} total submissions in database")
            
            # Count different types
            updated_count = 0
            already_set_count = 0
            skipped_quiz_count = 0
            no_grade_count = 0
            
            for submission in all_submissions:
                # Check if submission_type is already set (not None, not empty, not 'online')
                if submission.submission_type and submission.submission_type != 'online':
                    already_set_count += 1
                    continue
                
                # Get the assignment
                assignment = Assignment.query.get(submission.assignment_id)
                
                if not assignment:
                    continue
                
                # Skip Quiz and Discussion assignments - those are always online
                if assignment.assignment_type and assignment.assignment_type.lower() in ['quiz', 'discussion']:
                    skipped_quiz_count += 1
                    continue
                
                # Check if there's a grade for this submission
                grade = Grade.query.filter_by(
                    student_id=submission.student_id,
                    assignment_id=submission.assignment_id
                ).first()
                
                if grade:
                    # Has a grade, so it was submitted and graded
                    submission.submission_type = 'in_person'
                    submission.submission_notes = 'Retroactively marked as in-person submission (existing grade found)'
                    updated_count += 1
                elif assignment.assignment_type and assignment.assignment_type.lower() in ['pdf', 'paper']:
                    # PDF/Paper assignment without grade - likely in-person but not graded yet
                    submission.submission_type = 'in_person'
                    submission.submission_notes = 'Retroactively marked as in-person submission (PDF/Paper assignment)'
                    updated_count += 1
                else:
                    # No grade and not a paper assignment
                    no_grade_count += 1
            
            # Commit changes
            if updated_count > 0:
                confirm = input(f"\n⚠️  About to update {updated_count} submission(s). Continue? (yes/no): ")
                if confirm.lower() in ['yes', 'y']:
                    db.session.commit()
                    print("\n" + "=" * 60)
                    print("✅ UPDATE COMPLETE!")
                    print("=" * 60)
                    print(f"\n📊 Summary:")
                    print(f"   ✅ Updated to 'in_person': {updated_count}")
                    print(f"   ℹ️  Already had type set: {already_set_count}")
                    print(f"   ⏭️  Skipped (Quiz/Discussion): {skipped_quiz_count}")
                    print(f"   ⏸️  Left as-is (no grade): {no_grade_count}")
                    print(f"   📝 Total processed: {total_submissions}")
                    print("\n✨ Your existing graded assignments are now marked as in-person!")
                    print("\nNote: Future submissions will need to be marked manually")
                    print("      or students can upload files online.")
                else:
                    print("\n❌ Update cancelled. No changes made.")
            else:
                print("\n✅ No submissions need updating!")
                print(f"\n📊 Summary:")
                print(f"   ℹ️  Already had type set: {already_set_count}")
                print(f"   ⏭️  Skipped (Quiz/Discussion): {skipped_quiz_count}")
                print(f"   ⏸️  No grade found: {no_grade_count}")
                print(f"   📝 Total checked: {total_submissions}")
                
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during update: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    update_existing_submissions()

