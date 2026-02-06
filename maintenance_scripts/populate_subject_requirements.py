"""
One-time script to create subject_requirement table and populate from current hardcoded lists.
Run with: python -c "from app import create_app; from maintenance_scripts.populate_subject_requirements import run; app = create_app(); app.app_context().push(); run()"
Or: flask shell then from maintenance_scripts.populate_subject_requirements import run; run()
"""
from extensions import db
from models import SubjectRequirement


# Same subject lists as in services/grade_calculation.py (source of truth before DB)
SUBJECTS_1_2 = [
    "Reading Comprehension", "Language Arts", "Spelling", "Handwriting",
    "Math", "Science", "Social Studies", "Art", "Physical Education"
]
SUBJECTS_3 = [
    "Reading", "English", "Spelling", "Math", "Science", "Social Studies",
    "Art", "Physical Education", "Islamic Studies", "Quran", "Arabic"
]
SUBJECTS_4_8 = [
    "Reading", "English", "Spelling", "Vocabulary", "Math", "Science",
    "Social Studies", "Art", "Physical Education", "Islamic Studies", "Quran", "Arabic"
]


def run():
    """Create table if missing and insert default subject requirements."""
    db.create_all()
    if SubjectRequirement.query.first():
        print("SubjectRequirement already has data; skipping insert.")
        return
    order = 0
    for name in SUBJECTS_1_2:
        order += 1
        db.session.add(SubjectRequirement(grade_level_min=1, grade_level_max=2, subject_name=name, display_order=order))
    order = 0
    for name in SUBJECTS_3:
        order += 1
        db.session.add(SubjectRequirement(grade_level_min=3, grade_level_max=3, subject_name=name, display_order=order))
    order = 0
    for name in SUBJECTS_4_8:
        order += 1
        db.session.add(SubjectRequirement(grade_level_min=4, grade_level_max=8, subject_name=name, display_order=order))
    db.session.commit()
    print(f"Inserted {SubjectRequirement.query.count()} subject requirements.")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        run()
