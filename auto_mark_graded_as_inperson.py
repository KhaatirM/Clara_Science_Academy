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
            low_grade_count = 0
            
            # Get all grades
            all_grades = Grade.query.all()
            print(f"📊 Found {len(all_grades)} total grades")
            
            # Process all grades and mark corresponding submissions as in_person
            for grade in all_grades:
                # Parse grade data to get score
                try:
                    import json
                    grade_data = json.loads(grade.grade_data) if grade.grade_data else {}
                    score = grade_data.get('score', 0)
                    
                    # Only process if score > 2%
                    if score <= 2:
                        low_grade_count += 1
                        continue
                    
                    # Find or create submission for this grade
                    submission = Submission.query.filter_by(
                        student_id=grade.student_id,
                        assignment_id=grade.assignment_id
                    ).first()
                    
                    if submission:
                        # Update existing submission
                        if submission.submission_type != 'in_person':
                            submission.submission_type = 'in_person'
                            if not submission.submission_notes:
                                submission.submission_notes = 'Auto-marked as in-person (graded assignment)'
                            updated_count += 1
                        else:
                            already_inperson_count += 1
                    else:
                        # Create new submission record for graded assignment
                        new_submission = Submission(
                            student_id=grade.student_id,
                            assignment_id=grade.assignment_id,
                            submission_type='in_person',
                            submission_notes='Auto-created for graded assignment (physical paper)',
                            submitted_at=grade.graded_at if grade.graded_at else datetime.utcnow(),
                            file_path=None
                        )
                        db.session.add(new_submission)
                        updated_count += 1
                        
                except Exception as e:
                    print(f"⚠️  Error processing grade {grade.id}: {e}")
                    continue
            
            # Show summary before committing
            print("\n" + "=" * 70)
            print("SUMMARY OF CHANGES")
            print("=" * 70)
            print(f"\n📝 Will update/create: {updated_count} submission(s)")
            print(f"✅ Already marked as in-person: {already_inperson_count}")
            print(f"⏸️  Low grade (≤2%, skipped): {low_grade_count}")
            print(f"📊 Total grades processed: {len(all_grades)}")
            
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

