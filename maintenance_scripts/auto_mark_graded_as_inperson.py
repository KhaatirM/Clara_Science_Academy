"""
Automatic Submission Status Update for Graded Assignments (Percentage-Based)

Marks assignments as 'submitted in person' when:
  - A grade was inputted
  - No submission status was indicated (no Submission, or submission_type='not_submitted')
  - The grade percentage is 5% or above (points_earned / assignment.total_points >= 5%)

Leaves alone when grade is 4% or below.

Run on Render Shell:
    python maintenance_scripts/auto_mark_graded_as_inperson.py
    python maintenance_scripts/auto_mark_graded_as_inperson.py --yes   # Non-interactive
"""

import json
import argparse
from datetime import datetime

from app import create_app, db
from models import Submission, Grade, Assignment


def _get_points_earned(grade_data):
    """Safely get points_earned or score from grade_data."""
    if grade_data is None:
        return None
    val = grade_data.get('points_earned')
    if val is not None:
        return val
    return grade_data.get('score')


def auto_mark_graded_as_inperson(skip_confirm=False):
    """Mark graded assignments (5%+) as in-person when no submission status was indicated."""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 70)
            print("AUTO-MARK GRADED ASSIGNMENTS AS IN-PERSON (5%+ threshold)")
            print("=" * 70)

            updated_count = 0
            already_has_status_count = 0
            low_percentage_count = 0
            no_grade_data_count = 0

            # Get all non-voided grades with assignment eager-loaded
            grades = Grade.query.join(Assignment).filter(
                Grade.is_voided == False,
                Assignment.status != 'Voided'
            ).all()

            print(f"\n📊 Found {len(grades)} grades to process (excluding voided)")

            for grade in grades:
                try:
                    assignment = grade.assignment
                    if not assignment or not assignment.total_points or assignment.total_points <= 0:
                        continue

                    grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else (grade.grade_data or {})
                    points_earned = _get_points_earned(grade_data)
                    if points_earned is None:
                        no_grade_data_count += 1
                        continue

                    try:
                        points_earned = float(points_earned)
                    except (ValueError, TypeError):
                        no_grade_data_count += 1
                        continue

                    # Calculate percentage
                    total_points = float(assignment.total_points)
                    percentage = (points_earned / total_points * 100) if total_points > 0 else 0

                    # 4% and below: leave alone
                    if percentage <= 4:
                        low_percentage_count += 1
                        continue

                    # 5% and above: only update if no submission status was indicated
                    submission = Submission.query.filter_by(
                        student_id=grade.student_id,
                        assignment_id=grade.assignment_id
                    ).first()

                    # Skip if submission status was already indicated (in_person or online)
                    if submission and submission.submission_type in ('in_person', 'online'):
                        already_has_status_count += 1
                        continue

                    # Mark as submitted in person: update existing or create new
                    if submission:
                        submission.submission_type = 'in_person'
                        if not submission.submission_notes:
                            submission.submission_notes = 'Auto-marked as in-person (graded 5%+)'
                        updated_count += 1
                    else:
                        new_submission = Submission(
                            student_id=grade.student_id,
                            assignment_id=grade.assignment_id,
                            submission_type='in_person',
                            submission_notes='Auto-created for graded assignment (5%+)',
                            submitted_at=grade.graded_at or datetime.utcnow(),
                            file_path=None
                        )
                        db.session.add(new_submission)
                        updated_count += 1

                except Exception as e:
                    print(f"⚠️  Error processing grade {grade.id}: {e}")
                    continue

            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"\n📝 Will update/create: {updated_count} submission(s)")
            print(f"✅ Already has status (in_person/online): {already_has_status_count}")
            print(f"⏸️  Low grade (≤4%, left alone): {low_percentage_count}")
            print(f"📊 No parseable grade data: {no_grade_data_count}")

            if updated_count > 0:
                if skip_confirm:
                    db.session.commit()
                    print("\n" + "=" * 70)
                    print("✅ UPDATE COMPLETE (--yes)")
                    print("=" * 70)
                    print(f"\n🎉 Updated {updated_count} submission(s) to 'in_person'")
                else:
                    print("\n" + "=" * 70)
                    confirm = input("\n⚠️  Proceed with update? (yes/no): ")
                    if confirm.lower() in ('yes', 'y'):
                        db.session.commit()
                        print(f"\n✅ Updated {updated_count} submission(s).")
                    else:
                        db.session.rollback()
                        print("\n❌ Cancelled. No changes made.")
            else:
                print("\n✅ Nothing to update.")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mark graded assignments (5%+) as submitted in person')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    auto_mark_graded_as_inperson(skip_confirm=args.yes)
