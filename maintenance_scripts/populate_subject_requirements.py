"""
One-time script to create subject_requirement table and populate from current hardcoded lists.
Run with: python -c "from app import create_app; from maintenance_scripts.populate_subject_requirements import run; app = create_app(); app.app_context().push(); run()"
Or: flask shell then from maintenance_scripts.populate_subject_requirements import run; run()
"""
from extensions import db
from models import SubjectRequirement


# Same subject lists as services/grade_calculation.py fallback (source of truth before DB)
from services.grade_calculation import _fallback_subjects_for_grade_level


def run():
    """Create table if missing and insert default subject requirements."""
    db.create_all()
    if SubjectRequirement.query.first():
        print("SubjectRequirement already has data; skipping insert.")
        return
    for gl in (1, 2, 3, 4, 5, 6, 7, 8):
        subjects = _fallback_subjects_for_grade_level(gl)
        for order, name in enumerate(subjects, start=1):
            db.session.add(SubjectRequirement(
                grade_level_min=gl,
                grade_level_max=gl,
                subject_name=name,
                display_order=order,
            ))
    db.session.commit()
    print(f"Inserted {SubjectRequirement.query.count()} subject requirements.")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        run()
