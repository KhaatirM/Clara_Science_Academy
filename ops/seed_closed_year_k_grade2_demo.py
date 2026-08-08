"""Bulk-seed Kindergarten + 2nd grade demo data for closed school year 2025-2026."""

from __future__ import annotations

import random
from datetime import datetime

from app import create_app
from extensions import db
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
from utils.report_card_school_year import record_student_school_year_grade

RANDOM = random.Random(20260807)

# Closed-year grade → live “promoted” grade after year close
K_COHORT = [
    # (student_id, closed_year_grade, live_grade_after_close)
    (45, 0, 1),  # Ongwa Isaya
    (46, 0, 1),  # Eto Isaya
    (51, 0, 1),  # Favor Heuston
    (52, 0, 1),  # Malani Hope
    (34, 0, 1),  # Zamaria Scales
]

G2_COHORT = [
    (29, 2, 3),  # Manasseh Ajuwa
    (36, 2, 3),  # Mata Amani
    (38, 2, 3),  # Misael Flores Perez
    (37, 2, 3),  # Praise Heuston (already seeded once)
    (40, 2, 3),  # Rylan Barley
    (43, 2, 3),  # Rebeka Eyana
]

G2_LETTERS = ["A", "A-", "B+", "B", "B-", "C+", "C"]
G2_LETTER_PCT = {
    "A": 96.0,
    "A-": 91.0,
    "B+": 88.0,
    "B": 84.0,
    "B-": 81.0,
    "C+": 78.0,
    "C": 74.0,
}
G2_MARKS = ["M", "W", "NA", "UA"]
K_ACADEMIC = ["M", "N", "I", "U"]
K_HABITS = ["E", "S", "N", "U"]


def _ensure_profile(student: Student, entrance: str) -> None:
    if not student.gender:
        student.gender = RANDOM.choice(["F", "M"])
    if not student.entrance_date or len(str(student.entrance_date)) < 9:
        student.entrance_date = entrance


def _get_or_create_class(
    *,
    name: str,
    subject: str,
    levels: list[int],
    school_year_id: int,
    teacher_id: int,
) -> Class:
    existing = Class.query.filter_by(name=name, school_year_id=school_year_id).first()
    if existing:
        existing.is_active = True
        existing.subject = subject
        existing.set_grade_levels(levels)
        existing.teacher_id = teacher_id
        existing.term_type = "full_year"
        return existing
    class_obj = Class(
        name=name,
        subject=subject,
        teacher_id=teacher_id,
        school_year_id=school_year_id,
        is_active=True,
        term_type="full_year",
    )
    class_obj.set_grade_levels(levels)
    db.session.add(class_obj)
    db.session.flush()
    return class_obj


def _ensure_enrollment(student_id: int, class_id: int) -> Enrollment:
    en = Enrollment.query.filter_by(student_id=student_id, class_id=class_id).first()
    if not en:
        en = Enrollment(student_id=student_id, class_id=class_id)
        db.session.add(en)
    en.is_active = True
    en.dropped_at = None
    en.enrolled_at = datetime(2025, 8, 4, 12, 0, 0)
    return en


def _set_quarter_grade(student_id: int, class_id: int, school_year_id: int, quarter: str, letter: str) -> None:
    row = QuarterGrade.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        school_year_id=school_year_id,
        quarter=quarter,
    ).first()
    if not row:
        row = QuarterGrade(
            student_id=student_id,
            class_id=class_id,
            school_year_id=school_year_id,
            quarter=quarter,
        )
        db.session.add(row)
    row.letter_grade = letter
    row.percentage = G2_LETTER_PCT.get(letter, 80.0) + RANDOM.uniform(-1.5, 1.5)
    row.assignments_count = RANDOM.randint(3, 8)
    row.last_calculated = datetime.utcnow()


def _upsert_comment(student_id: int, class_id: int, school_year_id: int, text: str) -> None:
    row = ReportCardComment.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        school_year_id=school_year_id,
        quarter="ALL",
    ).first()
    if not row:
        db.session.add(
            ReportCardComment(
                student_id=student_id,
                class_id=class_id,
                school_year_id=school_year_id,
                quarter="ALL",
                comment_text=text,
            )
        )
    else:
        row.comment_text = text


def _seed_g2_standards(student_id: int, school_year_id: int) -> None:
    Grade2StandardMark.query.filter_by(student_id=student_id, school_year_id=school_year_id).delete()
    for std in g2_flat("language_arts") + g2_flat("math"):
        # Bias toward improvement over the year
        weights_by_q = [
            [0.15, 0.45, 0.30, 0.10],
            [0.35, 0.40, 0.20, 0.05],
            [0.55, 0.30, 0.10, 0.05],
            [0.70, 0.20, 0.08, 0.02],
        ]
        for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
            mark = RANDOM.choices(G2_MARKS, weights=weights_by_q[qi], k=1)[0]
            g2_upsert(student_id, std["id"], school_year_id, q, mark)


def _seed_k_standards(student_id: int, school_year_id: int) -> None:
    GradeKStandardMark.query.filter_by(student_id=student_id, school_year_id=school_year_id).delete()

    for std in k_flat("language_arts"):
        if scale_for_standard(std["id"]) == "proficiency":
            for q in ("Q3", "Q4"):
                if RANDOM.random() < 0.7:
                    k_upsert(student_id, std["id"], school_year_id, q, "X")
            continue
        for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
            weights = [
                [0.15, 0.35, 0.35, 0.15],
                [0.30, 0.40, 0.20, 0.10],
                [0.50, 0.30, 0.15, 0.05],
                [0.65, 0.25, 0.08, 0.02],
            ][qi]
            mark = RANDOM.choices(K_ACADEMIC, weights=weights, k=1)[0]
            k_upsert(student_id, std["id"], school_year_id, q, mark)

    for std in k_flat("math"):
        for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
            weights = [
                [0.20, 0.35, 0.30, 0.15],
                [0.35, 0.35, 0.20, 0.10],
                [0.55, 0.30, 0.10, 0.05],
                [0.70, 0.20, 0.08, 0.02],
            ][qi]
            mark = RANDOM.choices(K_ACADEMIC, weights=weights, k=1)[0]
            k_upsert(student_id, std["id"], school_year_id, q, mark)

    # Writing continuum progression
    start = RANDOM.randint(1, 3)
    for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
        level = min(7, start + qi + RANDOM.randint(0, 1))
        k_upsert(student_id, "k_writing_level", school_year_id, q, str(level))

    for std in k_flat("kindergarten_skills"):
        for q in ("Q2", "Q3", "Q4"):
            if RANDOM.random() < (0.4 if q == "Q2" else 0.75):
                k_upsert(student_id, std["id"], school_year_id, q, "X")

    for std in k_flat("work_habits"):
        for qi, q in enumerate(("Q1", "Q2", "Q3", "Q4")):
            weights = [
                [0.15, 0.45, 0.30, 0.10],
                [0.25, 0.45, 0.25, 0.05],
                [0.40, 0.40, 0.15, 0.05],
                [0.50, 0.40, 0.08, 0.02],
            ][qi]
            mark = RANDOM.choices(K_HABITS, weights=weights, k=1)[0]
            k_upsert(student_id, std["id"], school_year_id, q, mark)

    # Occasional retention risk flag in Q3 only
    if RANDOM.random() < 0.15:
        k_upsert(student_id, "k_int_risk", school_year_id, "Q3", "X")


def main() -> None:
    app = create_app()
    with app.app_context():
        sy = db.session.get(SchoolYear, 1)
        if not sy:
            raise SystemExit("School year 2025-2026 (id=1) not found")

        teacher = TeacherStaff.query.filter(TeacherStaff.first_name.ilike("%varsty%")).first()
        if not teacher:
            teacher = TeacherStaff.query.first()

        g2_specs = [
            ("Writing 2 [Demo]", "Writing", [2]),
            ("Language Arts 2 [Demo]", "Language Arts", [2]),
            ("Math 2 [Demo]", "Math", [2]),
            ("Science 2 [Demo]", "Science", [2]),
            ("Social Studies 2 [Demo]", "Social Studies", [2]),
            ("Art/Music 2 [Demo]", "Art", [2]),
            ("Physical Education 2 [Demo]", "Physical Education", [2]),
        ]
        k_specs = [
            ("Kindergarten Language Arts [Demo]", "Language Arts", [0]),
            ("Kindergarten Math [Demo]", "Math", [0]),
            ("Kindergarten Homeroom [Demo]", "Homeroom", [0]),
        ]
        g2_classes = [
            _get_or_create_class(
                name=n, subject=s, levels=lv, school_year_id=sy.id, teacher_id=teacher.id
            )
            for n, s, lv in g2_specs
        ]
        k_classes = [
            _get_or_create_class(
                name=n, subject=s, levels=lv, school_year_id=sy.id, teacher_id=teacher.id
            )
            for n, s, lv in k_specs
        ]
        db.session.flush()

        print("=== KINDERGARTEN cohort (closed-year grade K) ===")
        for student_id, closed_grade, live_grade in K_COHORT:
            student = db.session.get(Student, student_id)
            if not student:
                print(f"  missing student {student_id}")
                continue
            _ensure_profile(student, "2025-2026")
            student.grade_level = live_grade  # promoted after close
            record_student_school_year_grade(student.id, sy.id, closed_grade, enrolled=True)
            for class_obj in k_classes:
                _ensure_enrollment(student.id, class_obj.id)
            _seed_k_standards(student.id, sy.id)
            _upsert_comment(
                student.id,
                k_classes[0].id,
                sy.id,
                (
                    f"{student.first_name} made steady growth in letters, sounds, and listening. "
                    f"Continue reading aloud at home each evening."
                ),
            )
            _upsert_comment(
                student.id,
                k_classes[1].id,
                sy.id,
                f"{student.first_name} is building number sense. Practice counting objects to 20.",
            )
            print(f"  {student.id} {student.first_name} {student.last_name}  (was K -> now grade {live_grade})")

        print("=== 2ND GRADE cohort (closed-year grade 2) ===")
        for student_id, closed_grade, live_grade in G2_COHORT:
            student = db.session.get(Student, student_id)
            if not student:
                print(f"  missing student {student_id}")
                continue
            _ensure_profile(student, "2023-2024")
            student.grade_level = live_grade
            record_student_school_year_grade(student.id, sy.id, closed_grade, enrolled=True)
            for class_obj in g2_classes:
                _ensure_enrollment(student.id, class_obj.id)
                for q in ("Q1", "Q2", "Q3", "Q4"):
                    _set_quarter_grade(
                        student.id,
                        class_obj.id,
                        sy.id,
                        q,
                        RANDOM.choice(G2_LETTERS),
                    )
            _seed_g2_standards(student.id, sy.id)
            _upsert_comment(
                student.id,
                g2_classes[1].id,
                sy.id,
                (
                    f"{student.first_name} participates well and is growing as a reader/writer. "
                    f"Keep practicing fluency with nightly reading."
                ),
            )
            _upsert_comment(
                student.id,
                g2_classes[2].id,
                sy.id,
                f"{student.first_name} shows solid effort in math. Review regrouping and word problems.",
            )
            print(f"  {student.id} {student.first_name} {student.last_name}  (was 2nd -> now grade {live_grade})")

        db.session.commit()

        # Close the school year and deactivate its enrollments (historical generate path)
        class_ids = [c.id for c in g2_classes + k_classes]
        Enrollment.query.filter(Enrollment.class_id.in_(class_ids)).update(
            {"is_active": False, "dropped_at": datetime(2026, 5, 29, 17, 0, 0)},
            synchronize_session=False,
        )
        for class_obj in g2_classes + k_classes:
            class_obj.is_active = False
        sy.is_active = False
        db.session.commit()

        print()
        print("School year 2025-2026 is now CLOSED (inactive).")
        print("Demo classes/enrollments deactivated for historical report-card generation.")
        print()
        print("Kindergarten students to generate (select school year 2025-2026):")
        for student_id, _, _ in K_COHORT:
            s = db.session.get(Student, student_id)
            if s:
                print(f"  - {s.first_name} {s.last_name} (id {s.id})")
        print("2nd grade students to generate (select school year 2025-2026):")
        for student_id, _, _ in G2_COHORT:
            s = db.session.get(Student, student_id)
            if s:
                print(f"  - {s.first_name} {s.last_name} (id {s.id})")


if __name__ == "__main__":
    main()
