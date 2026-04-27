import os
import sys
import json
from datetime import datetime

from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from config import TestingConfig
from extensions import db
from models import (
    User,
    TeacherStaff,
    Student,
    Class,
    SchoolYear,
    Enrollment,
    Assignment,
    Submission,
    Grade,
    QuizQuestion,
    QuizOption,
    QuizAnswer,
)


def _force_login(client, user_id: int) -> None:
    """Log in a user without knowing a password (test-only)."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def _get_grade_points(grade: Grade) -> float:
    try:
        data = json.loads(grade.grade_data or "{}")
        return float(data.get("points_earned", data.get("score", 0.0)) or 0.0)
    except Exception:
        return 0.0


def main() -> int:
    app = create_app(TestingConfig)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False

    with app.test_client() as client, app.app_context():
        db.create_all()

        # --- Users ---
        teacher_staff = TeacherStaff(first_name="Test", last_name="Teacher", email="t@example.com")
        db.session.add(teacher_staff)
        db.session.flush()

        teacher_user = User(
            username="teacher_test",
            password_hash=generate_password_hash("pw"),
            role="Teacher",
            teacher_staff_id=teacher_staff.id,
            email="teacher_test@example.com",
        )
        director_user = User(
            username="director_test",
            password_hash=generate_password_hash("pw"),
            role="Director",
            email="director_test@example.com",
        )
        db.session.add_all([teacher_user, director_user])
        db.session.flush()

        # --- School year + class + students ---
        sy = SchoolYear(
            name="2099-2100",
            start_date=datetime(2099, 8, 1).date(),
            end_date=datetime(2100, 6, 1).date(),
            is_active=True,
        )
        db.session.add(sy)
        db.session.flush()

        c = Class(name="Test Class", subject="Science", teacher_id=teacher_staff.id, school_year_id=sy.id)
        c.set_grade_levels([6])
        s1 = Student(first_name="Submitted", last_name="Student", grade_level=6, email="s1@example.com")
        s2 = Student(first_name="NotSubmitted", last_name="Student", grade_level=6, email="s2@example.com")
        db.session.add_all([c, s1, s2])
        db.session.flush()

        db.session.add_all(
            [
                Enrollment(class_id=c.id, student_id=s1.id, is_active=True),
                Enrollment(class_id=c.id, student_id=s2.id, is_active=True),
            ]
        )
        db.session.flush()

        # --- PDF assignment ---
        a_pdf = Assignment(
            title="PDF Assignment",
            class_id=c.id,
            assignment_type="pdf",
            total_points=10.0,
            quarter="Q1",
            school_year_id=sy.id,
            due_date=datetime.utcnow(),
        )
        db.session.add(a_pdf)
        db.session.flush()

        # Only s1 has confirmed submission
        db.session.add(
            Submission(
                student_id=s1.id,
                assignment_id=a_pdf.id,
                submission_type="online",
                submitted_at=datetime.utcnow(),
            )
        )

        # --- Quiz assignment (mixed: MC + essay) ---
        a_quiz = Assignment(
            title="Mixed Quiz",
            class_id=c.id,
            assignment_type="quiz",
            total_points=5.0,
            quarter="Q1",
            school_year_id=sy.id,
            due_date=datetime.utcnow(),
        )
        db.session.add(a_quiz)
        db.session.flush()

        q_mc = QuizQuestion(
            assignment_id=a_quiz.id,
            question_text="MC?",
            question_type="multiple_choice",
            points=2.0,
            order=1,
        )
        q_essay = QuizQuestion(
            assignment_id=a_quiz.id,
            question_text="Essay?",
            question_type="essay",
            points=3.0,
            order=2,
        )
        db.session.add_all([q_mc, q_essay])
        db.session.flush()

        opt_a = QuizOption(question_id=q_mc.id, option_text="A", is_correct=True)
        opt_b = QuizOption(question_id=q_mc.id, option_text="B", is_correct=False)
        db.session.add_all([opt_a, opt_b])
        db.session.flush()

        # s1 submitted quiz; s2 did not.
        db.session.add(
            Submission(
                student_id=s1.id,
                assignment_id=a_quiz.id,
                submission_type="online",
                submitted_at=datetime.utcnow(),
            )
        )
        db.session.add(
            QuizAnswer(
                student_id=s1.id,
                question_id=q_mc.id,
                selected_option_id=opt_a.id,
                is_correct=True,
                points_earned=2.0,
            )
        )
        db.session.add(
            QuizAnswer(
                student_id=s1.id,
                question_id=q_essay.id,
                answer_text="hello",
                is_correct=None,
                points_earned=0.0,
            )
        )

        db.session.commit()

        # 1) Teacher PDF bulk grading: score entered for both, only submitted should save.
        _force_login(client, teacher_user.id)
        resp = client.post(
            f"/teacher/grade/assignment/{a_pdf.id}",
            data={
                f"score_{s1.id}": "8",
                f"score_{s2.id}": "8",
                # no submission_type changes
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        g1 = Grade.query.filter_by(assignment_id=a_pdf.id, student_id=s1.id).first()
        g2 = Grade.query.filter_by(assignment_id=a_pdf.id, student_id=s2.id).first()
        assert g1 is not None, "Expected grade saved for submitted PDF student"
        assert g2 is None, "Expected no grade for NOT-submitted PDF student"

        # 2) Teacher PDF: attempt to grade s2 after marking in_person in same request.
        resp = client.post(
            f"/teacher/grade/assignment/{a_pdf.id}",
            data={
                f"submission_type_{s2.id}": "in_person",
                f"score_{s2.id}": "7",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        g2 = Grade.query.filter_by(assignment_id=a_pdf.id, student_id=s2.id).first()
        assert g2 is not None, "Expected grade saved after marking in_person"

        # 3) Teacher quiz per-question save-all: should NOT create grade for non-submitted student.
        resp = client.post(
            f"/teacher/grade/assignment/{a_quiz.id}",
            data={
                "grading_mode": "per_question",
                f"points_{s1.id}_q{q_essay.id}": "2.5",
                f"comment_{s1.id}": "ok",
                # s2 omitted intentionally (defaults in form, but route must skip)
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        gq1 = Grade.query.filter_by(assignment_id=a_quiz.id, student_id=s1.id).first()
        gq2 = Grade.query.filter_by(assignment_id=a_quiz.id, student_id=s2.id).first()
        assert gq1 is not None, "Expected quiz grade saved for submitted student"
        assert gq2 is None, "Expected no quiz grade for NOT-submitted student"
        assert _get_grade_points(gq1) > 0, "Expected quiz grade points to be > 0 after essay scoring"

        # 4) Management quiz per-question save-all: should behave same as teacher.
        _force_login(client, director_user.id)
        resp = client.post(
            f"/management/grade/assignment/{a_quiz.id}",
            data={
                "grading_mode": "per_question",
                f"points_{s1.id}_q{q_essay.id}": "3",
                f"comment_{s1.id}": "final",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        gq1b = Grade.query.filter_by(assignment_id=a_quiz.id, student_id=s1.id).first()
        gq2b = Grade.query.filter_by(assignment_id=a_quiz.id, student_id=s2.id).first()
        assert gq1b is not None
        assert gq2b is None

    print("Smoke tests passed: grading scenarios behaved as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

