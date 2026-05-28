import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app  # noqa: E402
from models import Class, Enrollment, SchoolYear, SchoolYearClosure, Student  # noqa: E402


def main():
    with app.app_context():
        years = SchoolYear.query.order_by(SchoolYear.id.asc()).all()
        print("school_years=", [(y.id, y.name, y.is_active) for y in years])

        closures = SchoolYearClosure.query.order_by(SchoolYearClosure.id.desc()).all()
        print("closures=", len(closures))
        for c in closures[:10]:
            sy = SchoolYear.query.get(c.school_year_id) if c.school_year_id else None
            print(
                "closure_id=",
                c.id,
                "sy=",
                getattr(sy, "id", None),
                getattr(sy, "name", None),
                "phase=",
                c.phase,
                "closure_date=",
                getattr(c, "closure_date", None),
                "student_lockout_at=",
                getattr(c, "student_lockout_at", None),
                "teacher_lockout_at=",
                getattr(c, "teacher_lockout_at", None),
                "finalize_at=",
                getattr(c, "finalize_at", None),
            )

        # Sanity: if only one year is active, count active classes/enrollments in that year
        active_year = SchoolYear.query.filter_by(is_active=True).first()
        if active_year:
            active_classes = Class.query.filter_by(school_year_id=active_year.id, is_active=True).all()
            active_enrs = (
                Enrollment.query.join(Class, Enrollment.class_id == Class.id)
                .filter(Class.school_year_id == active_year.id, Enrollment.is_active.is_(True))
                .count()
            )
            print("active_year=", active_year.id, active_year.name)
            print("active_classes_in_active_year=", len(active_classes))
            print("active_enrollments_in_active_year=", active_enrs)

        # Jayden Hope snapshot
        s = Student.query.filter_by(first_name="Jayden", last_name="Hope").first()
        if s:
            print("jayden_id=", s.id)
            enrs = Enrollment.query.filter_by(student_id=s.id, is_active=True).all()
            for e in enrs:
                cl = Class.query.get(e.class_id)
                sy = SchoolYear.query.get(cl.school_year_id) if cl else None
                print("jayden_active_enr=", e.id, "class=", getattr(cl, "id", None), getattr(cl, "name", None), "class_active=", getattr(cl, "is_active", None), "sy=", getattr(sy, "name", None), "sy_active=", getattr(sy, "is_active", None))


if __name__ == "__main__":
    main()

