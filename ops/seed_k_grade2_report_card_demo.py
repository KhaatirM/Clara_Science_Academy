"""Seed local demo data for Kindergarten + 2nd grade report card preview."""

from __future__ import annotations

from datetime import datetime

from app import create_app
from extensions import db
from management_routes.reports import persist_report_card_record
from models import (
    Class,
    Enrollment,
    Grade2StandardMark,
    GradeKStandardMark,
    QuarterGrade,
    ReportCardComment,
    SchoolYear,
    Student,
    TeacherStaff,
)
from utils.report_card_grade2_standards import flat_standards as g2_flat
from utils.report_card_grade2_standards import upsert_mark as g2_upsert
from utils.report_card_kindergarten_standards import flat_standards as k_flat
from utils.report_card_kindergarten_standards import scale_for_standard
from utils.report_card_kindergarten_standards import upsert_mark as k_upsert

G2_MARK_PATTERN = {
    0: ("W", "W", "M", "M"),
    1: ("W", "M", "M", "M"),
    2: ("NA", "W", "M", "M"),
    3: ("NA", "NA", "W", "M"),
    4: ("W", "W", "W", "M"),
}

K_ACADEMIC = {
    0: ("N", "N", "M", "M"),
    1: ("N", "M", "M", "M"),
    2: ("I", "N", "N", "M"),
    3: ("U", "I", "N", "N"),
}


def main() -> None:
    app = create_app()
    with app.app_context():
        sy = db.session.get(SchoolYear, 1)
        if not sy:
            raise SystemExit("No school year id=1")

        sy.is_active = True
        for other in SchoolYear.query.filter(SchoolYear.id != sy.id).all():
            other.is_active = False

        teacher = TeacherStaff.query.filter(TeacherStaff.first_name.ilike("%varsty%")).first()
        if not teacher:
            teacher = TeacherStaff.query.first()
        print("Using teacher", teacher.id, teacher.first_name, teacher.last_name)

        k_student = Student.query.filter_by(grade_level=0).first()
        g2_student = db.session.get(Student, 37)
        if not k_student or not g2_student:
            raise SystemExit(f"Missing students k={k_student} g2={g2_student}")

        # Profile fields required by report-card generation
        g2_student.gender = g2_student.gender or "F"
        g2_student.entrance_date = g2_student.entrance_date or "2024-2025"
        k_student.gender = k_student.gender or "F"
        k_student.entrance_date = k_student.entrance_date or "2025-2026"

        def get_or_create_class(name: str, subject: str, levels: list[int]) -> Class:
            existing = Class.query.filter_by(name=name, school_year_id=sy.id).first()
            if existing:
                existing.is_active = True
                existing.subject = subject
                existing.set_grade_levels(levels)
                existing.teacher_id = teacher.id
                return existing
            c = Class(
                name=name,
                subject=subject,
                teacher_id=teacher.id,
                school_year_id=sy.id,
                is_active=True,
                term_type="full_year",
            )
            c.set_grade_levels(levels)
            db.session.add(c)
            db.session.flush()
            return c

        g2_specs = [
            ("Writing 2 [Demo]", "Writing", [2]),
            ("Language Arts 2 [Demo]", "Language Arts", [2]),
            ("Math 2 [Demo]", "Math", [2]),
            ("Science 2 [Demo]", "Science", [2]),
            ("Social Studies 2 [Demo]", "Social Studies", [2]),
            ("Art/Music 2 [Demo]", "Art", [2]),
            ("Physical Education 2 [Demo]", "Physical Education", [2]),
        ]
        g2_classes = [get_or_create_class(*spec) for spec in g2_specs]

        k_specs = [
            ("Kindergarten Language Arts [Demo]", "Language Arts", [0]),
            ("Kindergarten Math [Demo]", "Math", [0]),
            ("Kindergarten Homeroom [Demo]", "Homeroom", [0]),
        ]
        k_classes = [get_or_create_class(*spec) for spec in k_specs]
        db.session.flush()

        def ensure_enrollment(student: Student, class_obj: Class) -> None:
            en = Enrollment.query.filter_by(student_id=student.id, class_id=class_obj.id).first()
            if not en:
                en = Enrollment(student_id=student.id, class_id=class_obj.id)
                db.session.add(en)
            en.is_active = True
            en.dropped_at = None
            en.enrolled_at = datetime(2025, 8, 4, 12, 0, 0)

        for class_obj in g2_classes:
            ensure_enrollment(g2_student, class_obj)
        for class_obj in k_classes:
            ensure_enrollment(k_student, class_obj)

        letter_cycle = ["B", "B+", "A", "A-", "B", "A", "B+"]
        for idx, class_obj in enumerate(g2_classes):
            letter = letter_cycle[idx % len(letter_cycle)]
            pct = {"A": 95.0, "A-": 91.0, "B+": 88.0, "B": 84.0}.get(letter, 85.0)
            for q in ("Q1", "Q2", "Q3", "Q4"):
                row = QuarterGrade.query.filter_by(
                    student_id=g2_student.id,
                    class_id=class_obj.id,
                    school_year_id=sy.id,
                    quarter=q,
                ).first()
                if not row:
                    row = QuarterGrade(
                        student_id=g2_student.id,
                        class_id=class_obj.id,
                        school_year_id=sy.id,
                        quarter=q,
                    )
                    db.session.add(row)
                row.letter_grade = letter
                row.percentage = pct
                row.assignments_count = 4
                row.last_calculated = datetime.utcnow()

        Grade2StandardMark.query.filter_by(student_id=g2_student.id, school_year_id=sy.id).delete()
        for i, std in enumerate(g2_flat("language_arts") + g2_flat("math")):
            pattern = G2_MARK_PATTERN[i % 5]
            for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
                g2_upsert(g2_student.id, std["id"], sy.id, q, pattern[qi])

        GradeKStandardMark.query.filter_by(student_id=k_student.id, school_year_id=sy.id).delete()
        for i, std in enumerate(k_flat("language_arts")):
            if scale_for_standard(std["id"]) == "proficiency":
                for q, mark in (("Q3", "X"), ("Q4", "X")):
                    k_upsert(k_student.id, std["id"], sy.id, q, mark)
            else:
                pattern = K_ACADEMIC[i % 4]
                for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
                    k_upsert(k_student.id, std["id"], sy.id, q, pattern[qi])

        for i, std in enumerate(k_flat("math")):
            pattern = K_ACADEMIC[(i + 1) % 4]
            for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
                k_upsert(k_student.id, std["id"], sy.id, q, pattern[qi])

        for q, lvl in (("Q1", "2"), ("Q2", "3"), ("Q3", "5"), ("Q4", "6")):
            k_upsert(k_student.id, "k_writing_level", sy.id, q, lvl)

        for std in k_flat("kindergarten_skills"):
            k_upsert(k_student.id, std["id"], sy.id, "Q3", "X")
            k_upsert(k_student.id, std["id"], sy.id, "Q4", "X")

        habit_pattern = [("S", "S", "E", "E"), ("N", "S", "S", "E"), ("S", "E", "E", "E")]
        for i, std in enumerate(k_flat("work_habits")):
            pat = habit_pattern[i % 3]
            for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
                k_upsert(k_student.id, std["id"], sy.id, q, pat[qi])

        def upsert_comment(student: Student, class_obj: Class, text: str) -> None:
            row = ReportCardComment.query.filter_by(
                student_id=student.id,
                class_id=class_obj.id,
                school_year_id=sy.id,
                quarter="ALL",
            ).first()
            if not row:
                db.session.add(
                    ReportCardComment(
                        student_id=student.id,
                        class_id=class_obj.id,
                        school_year_id=sy.id,
                        quarter="ALL",
                        comment_text=text,
                    )
                )
            else:
                row.comment_text = text

        upsert_comment(
            g2_student,
            g2_classes[1],
            (
                "Praise is a joy to teach. She reads with growing fluency and participates thoughtfully. "
                "Continue daily reading at home and double-check written work before turning it in."
            ),
        )
        upsert_comment(
            g2_student,
            g2_classes[2],
            "Strong progress in multi-digit addition/subtraction. Practice skip-counting and word problems over breaks.",
        )
        upsert_comment(
            k_student,
            k_classes[0],
            (
                "Bridgite is building strong print concepts and letter recognition. "
                "She loves story time and is moving through the writing continuum nicely. "
                "Please continue letter-sound practice at home."
            ),
        )
        upsert_comment(
            k_student,
            k_classes[1],
            "Counting and comparing sets are strengths. Keep practicing writing numbers 0–20.",
        )

        db.session.commit()

        g2_rc = persist_report_card_record(
            g2_student.id,
            sy.id,
            [c.id for c in g2_classes],
            ["Q1", "Q2", "Q3", "Q4"],
            report_type="unofficial",
            include_attendance=True,
            include_comments=True,
            additional_comments="Demo data for layout review — not an official transcript.",
            notify_admins=False,
        )
        k_rc = persist_report_card_record(
            k_student.id,
            sy.id,
            [c.id for c in k_classes],
            ["Q1", "Q2", "Q3", "Q4"],
            report_type="unofficial",
            include_attendance=True,
            include_comments=True,
            additional_comments="Demo data for Kindergarten layout review — not an official transcript.",
            notify_admins=False,
        )

        print("G2 ok=", g2_rc.get("ok"), "error=", g2_rc.get("error"), "rc_id=", getattr(g2_rc.get("report_card"), "id", None))
        print("K ok=", k_rc.get("ok"), "error=", k_rc.get("error"), "rc_id=", getattr(k_rc.get("report_card"), "id", None))
        print("---")
        print(f"GRADE 2: {g2_student.first_name} {g2_student.last_name} (id={g2_student.id})")
        print(f"KINDERGARTEN: {k_student.first_name} {k_student.last_name} (id={k_student.id})")
        print(f"School year active: {sy.name}")
        print(f"G2 standard marks: {Grade2StandardMark.query.filter_by(student_id=g2_student.id).count()}")
        print(f"K standard marks: {GradeKStandardMark.query.filter_by(student_id=k_student.id).count()}")


if __name__ == "__main__":
    main()
