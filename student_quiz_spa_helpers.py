"""Student quiz take/submit payloads for the React SPA."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from itertools import groupby
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from management_routes.student_assistant_utils import assignment_visible_to_students
from models import (
    Assignment,
    AssignmentReopening,
    Enrollment,
    Grade,
    QuizAnswer,
    QuizOption,
    QuizProgress,
    QuizQuestion,
    Student,
    Submission,
    db,
)
from teacher_routes.assignment_utils import _as_utc_aware, is_assignment_open_for_student


def _student() -> Student | None:
    sid = getattr(current_user, "student_id", None)
    return Student.query.get(sid) if sid else None


def _fmt_due(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        pass
    return str(value)


def _access_error(assignment: Assignment, student: Student) -> tuple[str | None, int]:
    if not assignment_visible_to_students(assignment):
        return "This assignment is not available.", 403
    if getattr(assignment, "quiz_authoring_is_draft", False):
        return "This quiz has not been published yet.", 403
    if assignment.assignment_type != "quiz":
        return "This is not a quiz assignment.", 400
    if assignment.status == "Voided":
        return "This assignment is no longer available.", 403
    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrollment:
        return "You are not enrolled in this class.", 403
    return None, 200


def build_student_quiz_payload(
    assignment_id: int, *, retake: bool = False
) -> tuple[dict[str, Any] | None, str | None, int]:
    from studentroutes import _pick_best_quiz_grade_row

    student = _student()
    if not student:
        return None, "Student profile required", 403

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return None, "Quiz not found", 404

    err, status = _access_error(assignment, student)
    if err:
        return None, err, status

    all_quiz_grades = (
        Grade.query.filter_by(student_id=student.id, assignment_id=assignment_id)
        .order_by(Grade.graded_at.desc(), Grade.id.desc())
        .all()
    )
    grade = _pick_best_quiz_grade_row(all_quiz_grades, assignment.total_points)
    if grade and grade.is_voided:
        return (
            None,
            "Your score for this assignment was voided. Ask your teacher to restore it before opening this quiz.",
            403,
        )

    if assignment.google_form_linked and assignment.google_form_url:
        return {
            "mode": "google_form",
            "assignment": {
                "id": assignment.id,
                "title": assignment.title,
                "google_form_url": assignment.google_form_url,
            },
            "links": {"assignments": "/app/student/assignments"},
        }, None, 200

    active_reopening = AssignmentReopening.query.filter_by(
        assignment_id=assignment_id, student_id=student.id, is_active=True
    ).first()
    if (not is_assignment_open_for_student(assignment, student.id)) and (not active_reopening):
        return None, "This assignment is no longer available.", 403

    is_retake = bool(retake)
    submission = (
        Submission.query.filter_by(student_id=student.id, assignment_id=assignment_id)
        .order_by(Submission.submitted_at.desc())
        .first()
    )
    submissions_count = Submission.query.filter_by(
        student_id=student.id, assignment_id=assignment_id
    ).count()

    effective_max_attempts = assignment.max_attempts
    if active_reopening and active_reopening.additional_attempts > 0:
        effective_max_attempts = (assignment.max_attempts or 0) + active_reopening.additional_attempts

    attempts_remaining = None
    if assignment.max_attempts:
        attempts_remaining = max(0, (effective_max_attempts or 0) - submissions_count)

    if (
        assignment.max_attempts
        and effective_max_attempts
        and submissions_count >= effective_max_attempts
        and not submission
        and not grade
    ):
        return (
            None,
            f"You have reached the maximum number of attempts ({effective_max_attempts}) for this quiz.",
            403,
        )

    grade_data = None
    grading_status = None
    grade_percentage = None
    if grade and grade.grade_data:
        try:
            grade_data = (
                json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            )
            if isinstance(grade_data, dict):
                grading_status = (grade_data.get("grading_status") or "").strip().lower() or None
                grade_percentage = grade_data.get("percentage")
        except Exception:
            grade_data = None

    if is_retake and attempts_remaining and attempts_remaining > 0:
        submission = None
        grade = None
        grade_data = None
        grading_status = None
        grade_percentage = None
        QuizProgress.query.filter_by(
            student_id=student.id, assignment_id=assignment_id
        ).delete(synchronize_session=False)
        db.session.commit()

    questions = (
        QuizQuestion.query.options(joinedload(QuizQuestion.section), joinedload(QuizQuestion.options))
        .filter_by(assignment_id=assignment_id)
        .order_by(QuizQuestion.order)
        .all()
    )

    if is_retake and assignment.shuffle_questions:
        questions = list(questions)
        shuffled: list = []
        for _section_id, group in groupby(questions, key=lambda q: q.section_id):
            chunk = list(group)
            random.shuffle(chunk)
            shuffled.extend(chunk)
        questions = shuffled

    show_correct = bool(assignment.show_correct_answers and submission and not is_retake)
    results_mode = bool(submission and not is_retake)

    existing_answers: dict[int, Any] = {}
    if results_mode:
        answers = (
            QuizAnswer.query.join(QuizQuestion)
            .filter(
                QuizAnswer.student_id == student.id,
                QuizQuestion.assignment_id == assignment_id,
            )
            .all()
        )
        for answer in answers:
            existing_answers[answer.question_id] = {
                "selected_option_id": answer.selected_option_id,
                "answer_text": answer.answer_text,
                "is_correct": answer.is_correct,
                "points_earned": answer.points_earned,
            }

    questions_out = []
    for q in questions:
        opts = sorted(q.options or [], key=lambda o: o.order or 0)
        options_out = []
        for opt in opts:
            row = {"id": opt.id, "option_text": opt.option_text, "order": opt.order}
            if show_correct:
                row["is_correct"] = bool(opt.is_correct)
            options_out.append(row)
        existing = existing_answers.get(q.id)
        questions_out.append(
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "points": q.points,
                "order": q.order,
                "section": (
                    {
                        "id": q.section.id,
                        "title": q.section.title,
                        "order": q.section.order,
                    }
                    if q.section
                    else None
                ),
                "options": options_out,
                "student_answer": existing,
            }
        )

    timer_remaining_seconds = (
        assignment.time_limit_minutes * 60 if assignment.time_limit_minutes else None
    )
    if (
        assignment.time_limit_minutes
        and assignment.allow_save_and_continue
        and not results_mode
    ):
        now_utc = datetime.utcnow()
        progress = QuizProgress.query.filter_by(
            student_id=student.id, assignment_id=assignment_id, is_submitted=False
        ).first()
        if not progress:
            progress = QuizProgress(
                student_id=student.id,
                assignment_id=assignment_id,
                answers_data=json.dumps({}),
                progress_percentage=0,
                questions_answered=0,
                total_questions=len(questions),
                last_saved_at=now_utc,
                timer_started_at=now_utc,
                timer_remaining_seconds=timer_remaining_seconds,
            )
            db.session.add(progress)
            db.session.commit()
        else:
            if progress.timer_remaining_seconds is None:
                progress.timer_remaining_seconds = timer_remaining_seconds
                if progress.timer_started_at is None:
                    progress.timer_started_at = now_utc
                db.session.commit()
            if progress.timer_started_at and progress.timer_remaining_seconds is not None:
                elapsed = (now_utc - progress.timer_started_at).total_seconds()
                timer_remaining_seconds = max(0, int(progress.timer_remaining_seconds - elapsed))
            elif progress.timer_remaining_seconds is not None:
                timer_remaining_seconds = max(0, int(progress.timer_remaining_seconds))
                progress.timer_started_at = now_utc
                db.session.commit()

    if is_retake and assignment.time_limit_minutes:
        timer_remaining_seconds = assignment.time_limit_minutes * 60

    closes_at = assignment.close_date or assignment.due_date
    closes_at_utc = _as_utc_aware(closes_at) if closes_at else None
    server_now_utc = datetime.now(timezone.utc)

    can_retake = bool(
        results_mode
        and attempts_remaining is not None
        and attempts_remaining > 0
        and is_assignment_open_for_student(assignment, student.id)
    )

    return {
        "mode": "results" if results_mode else "take",
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "class_name": assignment.class_info.name if assignment.class_info else None,
            "due_display": _fmt_due(assignment.due_date),
            "quarter": assignment.quarter,
            "status": assignment.status,
            "total_points": assignment.total_points,
            "time_limit_minutes": assignment.time_limit_minutes,
            "allow_save_and_continue": bool(assignment.allow_save_and_continue),
            "save_timeout_minutes": assignment.save_timeout_minutes or 30,
            "max_attempts": assignment.max_attempts,
            "show_correct_answers": bool(assignment.show_correct_answers),
        },
        "attempt": {
            "is_retake": is_retake,
            "submissions_count": submissions_count,
            "attempts_remaining": attempts_remaining,
            "can_retake": can_retake,
            "has_open_ended": any(q["question_type"] in ("short_answer", "essay") for q in questions_out),
        },
        "grade": (
            {
                "percentage": grade_percentage,
                "grading_status": grading_status,
                "points_earned": (grade_data or {}).get("points_earned") if isinstance(grade_data, dict) else None,
                "total_points": (grade_data or {}).get("total_points") if isinstance(grade_data, dict) else None,
                "score": (grade_data or {}).get("score") if isinstance(grade_data, dict) else None,
            }
            if grade
            else None
        ),
        "questions": questions_out,
        "timer_remaining_seconds": timer_remaining_seconds,
        "closes_at_iso": closes_at_utc.isoformat() if closes_at_utc else None,
        "server_now_iso": server_now_utc.isoformat(),
        "quiz_opened_at": server_now_utc.isoformat(),
        "links": {
            "assignments": "/app/student/assignments",
            "retake": f"/app/student/take-quiz/{assignment.id}?retake=true",
            "save_progress": f"/student/save-quiz-progress/{assignment.id}",
            "load_progress": f"/student/load-quiz-progress/{assignment.id}",
            "keepalive": f"/student/quiz-keepalive/{assignment.id}",
        },
    }, None, 200


def submit_student_quiz(
    assignment_id: int, *, answers: dict[str, Any], quiz_opened_at: str | None = None
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return None, "Quiz not found", 404

    err, status = _access_error(assignment, student)
    if err:
        return None, err, status

    active_reopening = AssignmentReopening.query.filter_by(
        assignment_id=assignment_id, student_id=student.id, is_active=True
    ).first()
    if not is_assignment_open_for_student(assignment, student.id) and not active_reopening:
        closes_at = assignment.close_date or assignment.due_date
        closes_at_utc = _as_utc_aware(closes_at) if closes_at else None
        now_utc = datetime.now(timezone.utc)
        opened_at_utc = None
        if quiz_opened_at:
            try:
                opened_at_utc = datetime.fromisoformat(quiz_opened_at)
                if opened_at_utc.tzinfo is None:
                    opened_at_utc = opened_at_utc.replace(tzinfo=timezone.utc)
            except ValueError:
                opened_at_utc = None
        allow_grace = (
            closes_at_utc is not None
            and opened_at_utc is not None
            and opened_at_utc <= closes_at_utc
            and (now_utc - closes_at_utc).total_seconds() <= 120
        )
        if not allow_grace:
            return None, "This quiz is not currently open for submission.", 403

    submissions_count = Submission.query.filter_by(
        student_id=student.id, assignment_id=assignment_id
    ).count()
    effective_max_attempts = assignment.max_attempts
    if active_reopening and active_reopening.additional_attempts > 0:
        effective_max_attempts = (assignment.max_attempts or 0) + active_reopening.additional_attempts
    if assignment.max_attempts and effective_max_attempts and submissions_count >= effective_max_attempts:
        return (
            None,
            f"You have reached the maximum number of attempts ({effective_max_attempts}) for this quiz.",
            403,
        )

    timed_meta = None
    if assignment.time_limit_minutes and assignment.allow_save_and_continue:
        now_utc = datetime.utcnow()
        progress = QuizProgress.query.filter_by(
            student_id=student.id, assignment_id=assignment_id, is_submitted=False
        ).first()
        if progress:
            limit_seconds = int(assignment.time_limit_minutes * 60)
            if progress.timer_remaining_seconds is None:
                progress.timer_remaining_seconds = limit_seconds
            if progress.timer_started_at and progress.timer_remaining_seconds is not None:
                elapsed = (now_utc - progress.timer_started_at).total_seconds()
                remaining = max(0, int(progress.timer_remaining_seconds - elapsed))
            else:
                remaining = max(0, int(progress.timer_remaining_seconds or limit_seconds))
            timed_meta = {
                "time_limit_seconds": limit_seconds,
                "time_remaining_seconds": remaining,
                "submitted_due_to_timer": remaining <= 0,
            }

    try:
        questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).all()
        q_ids = [q.id for q in questions]
        if q_ids:
            QuizAnswer.query.filter(
                QuizAnswer.student_id == student.id,
                QuizAnswer.question_id.in_(q_ids),
            ).delete(synchronize_session=False)

        total_points = 0
        earned_points = 0
        has_open_ended = False

        for question in questions:
            raw = answers.get(str(question.id), answers.get(question.id))
            if question.question_type in ("multiple_choice", "true_false"):
                if raw not in (None, ""):
                    try:
                        selected_option = QuizOption.query.get(int(raw))
                        is_correct = bool(selected_option and selected_option.is_correct)
                        points_earned = question.points if is_correct else 0
                        db.session.add(
                            QuizAnswer(
                                student_id=student.id,
                                question_id=question.id,
                                selected_option_id=selected_option.id if selected_option else None,
                                is_correct=is_correct,
                                points_earned=points_earned,
                            )
                        )
                        if is_correct:
                            earned_points += points_earned
                    except (ValueError, TypeError):
                        pass
            elif question.question_type in ("short_answer", "essay"):
                has_open_ended = True
                db.session.add(
                    QuizAnswer(
                        student_id=student.id,
                        question_id=question.id,
                        answer_text=str(raw or ""),
                        is_correct=None,
                        points_earned=0,
                    )
                )
            total_points += question.points or 0

        db.session.add(
            Submission(
                student_id=student.id,
                assignment_id=assignment_id,
                comments=f"Quiz submitted with {earned_points}/{total_points} points",
            )
        )

        grade_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        grade_data = {
            "score": earned_points,
            "points_earned": earned_points,
            "total_points": total_points,
            "max_score": total_points,
            "percentage": round(grade_percentage, 2),
            "feedback": "",
            "auto_score_summary": f"{earned_points}/{total_points}",
            "graded_at": datetime.now().isoformat(),
            "grading_status": "pending" if has_open_ended else "final",
        }
        if timed_meta:
            grade_data["timed_quiz"] = timed_meta
        db.session.add(
            Grade(
                student_id=student.id,
                assignment_id=assignment_id,
                grade_data=json.dumps(grade_data),
                graded_at=datetime.now(),
            )
        )

        if assignment.allow_save_and_continue:
            progress = QuizProgress.query.filter_by(
                student_id=student.id, assignment_id=assignment_id, is_submitted=False
            ).first()
            if progress:
                progress.is_submitted = True
                progress.timer_started_at = None

        db.session.commit()
        return {
            "success": True,
            "message": "Quiz submitted successfully!",
            "redirect": f"/app/student/take-quiz/{assignment_id}",
        }, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error submitting quiz: {exc}", 500
