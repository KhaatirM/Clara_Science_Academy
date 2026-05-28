import os
import sys

# Ensure repo root is importable when running from scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app  # noqa: E402
from models import Class, Enrollment, SchoolYear, Student  # noqa: E402


def main():
    with app.app_context():
        s = Student.query.filter_by(first_name="Jayden", last_name="Hope").first()
        print("student_id=", getattr(s, "id", None))
        if not s:
            return

        enrs = (
            Enrollment.query.filter_by(student_id=s.id)
            .order_by(Enrollment.is_active.desc(), Enrollment.class_id.asc())
            .all()
        )
        print("enrollments=", len(enrs))
        for e in enrs:
            c = Class.query.get(e.class_id)
            sy = SchoolYear.query.get(c.school_year_id) if c and c.school_year_id else None
            print(
                "enr_id=",
                e.id,
                "enr_active=",
                e.is_active,
                "| class_id=",
                getattr(c, "id", None),
                "class_name=",
                getattr(c, "name", None),
                "class_active=",
                getattr(c, "is_active", None),
                "| sy_id=",
                getattr(sy, "id", None),
                "sy_name=",
                getattr(sy, "name", None),
                "sy_active=",
                getattr(sy, "is_active", None),
            )

        weird = (
            Class.query.join(SchoolYear, Class.school_year_id == SchoolYear.id)
            .filter(Class.is_active.is_(True), SchoolYear.is_active.is_(False))
            .all()
        )
        print("classes_active_but_year_inactive=", len(weird))
        for c in weird[:25]:
            sy = SchoolYear.query.get(c.school_year_id) if c.school_year_id else None
            print("weird_class_id=", c.id, "name=", c.name, "sy=", getattr(sy, "name", None))


if __name__ == "__main__":
    main()

