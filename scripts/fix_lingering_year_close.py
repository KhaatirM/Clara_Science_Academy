import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app  # noqa: E402
from models import Class, Enrollment, SchoolYear, Student, db  # noqa: E402


def main():
    with app.app_context():
        sy = SchoolYear.query.filter_by(is_active=True).first()
        print("active_school_year:", getattr(sy, "id", None), getattr(sy, "name", None), getattr(sy, "is_active", None))

        s = Student.query.filter_by(first_name="Jayden", last_name="Hope").first()
        print("jayden_id:", getattr(s, "id", None))

        # Deactivate any remaining active classes/enrollments in the active school year.
        if sy:
            class_ids_for_year = [c.id for c in Class.query.filter_by(school_year_id=sy.id).all()]
            n_enr = 0
            if class_ids_for_year:
                n_enr = (
                    Enrollment.query.filter(
                        Enrollment.class_id.in_(class_ids_for_year),
                        Enrollment.is_active.is_(True),
                    ).update(
                        {Enrollment.is_active: False, Enrollment.dropped_at: datetime.utcnow()},
                        synchronize_session=False,
                    )
                )
            n_cls = (
                Class.query.filter(Class.school_year_id == sy.id, Class.is_active.is_(True))
                .update({Class.is_active: False}, synchronize_session=False)
            )
            sy.is_active = False
            db.session.commit()
            print("deactivated_enrollments:", n_enr)
            print("deactivated_classes:", n_cls)
            print("school_year_set_inactive:", sy.id)


if __name__ == "__main__":
    main()

