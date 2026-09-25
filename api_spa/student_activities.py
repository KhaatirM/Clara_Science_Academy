"""Student quiz + discussion activity APIs for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import student_required
from student_routes.discussion_spa_helpers import (
    build_discussion_board_payload,
    build_discussion_thread_payload,
    create_discussion_thread_spa,
    edit_post_spa,
    edit_thread_spa,
    reply_to_thread_spa,
)
from student_routes.quiz_spa_helpers import build_student_quiz_payload, submit_student_quiz
from student_routes.test_lockdown_helpers import (
    MAX_SNAPSHOT_BYTES,
    report_violation,
    save_events,
    save_snapshot,
    start_test_session,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/quiz/<int:assignment_id>")
@login_required
@student_required
def student_quiz_get(assignment_id: int):
    retake = request.args.get("retake", "").lower() in ("1", "true", "yes")
    attempt_raw = request.args.get("attempt")
    attempt_submission_id = None
    if attempt_raw not in (None, ""):
        try:
            attempt_submission_id = int(attempt_raw)
        except (TypeError, ValueError):
            attempt_submission_id = None
    payload, error, status = build_student_quiz_payload(
        assignment_id, retake=retake, attempt_submission_id=attempt_submission_id
    )
    if error or not payload:
        return jsonify({"error": error or "Could not load quiz"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/quiz/<int:assignment_id>/submit", methods=["POST"])
@login_required
@student_required
def student_quiz_submit(assignment_id: int):
    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or {}
    quiz_opened_at = data.get("quiz_opened_at")
    payload, error, status = submit_student_quiz(
        assignment_id, answers=answers, quiz_opened_at=quiz_opened_at
    )
    if error or not payload:
        return jsonify({"error": error or "Could not submit quiz"}), status
    return jsonify(payload)


def _current_student_id() -> int | None:
    return getattr(current_user, "student_id", None)


@spa_api_blueprint.route("/student/test/<int:assignment_id>/start", methods=["POST"])
@login_required
@student_required
def student_test_start(assignment_id: int):
    from models import Assignment, Enrollment

    student_id = _current_student_id()
    assignment = Assignment.query.get(assignment_id)
    if not student_id or not assignment:
        return jsonify({"error": "Test not found"}), 404
    if not Enrollment.query.filter_by(student_id=student_id, class_id=assignment.class_id, is_active=True).first():
        return jsonify({"error": "You are not enrolled in this class."}), 403
    payload, error, status = start_test_session(assignment, student_id)
    if error or not payload:
        return jsonify({"error": error or "Could not start test"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/test/session/<int:session_id>/snapshot", methods=["POST"])
@login_required
@student_required
def student_test_snapshot(session_id: int):
    student_id = _current_student_id()
    file = request.files.get("image")
    data = file.read(MAX_SNAPSHOT_BYTES + 1) if file else b""
    payload, error, status = save_snapshot(session_id, student_id, request.form.get("kind", ""), data)
    if error or not payload:
        return jsonify({"error": error or "Could not save snapshot"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/test/session/<int:session_id>/events", methods=["POST"])
@login_required
@student_required
def student_test_events(session_id: int):
    data = request.get_json(silent=True) or {}
    payload, error, status = save_events(
        session_id, _current_student_id(), data.get("events"), data.get("answers")
    )
    if error or not payload:
        return jsonify({"error": error or "Could not save events"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/test/session/<int:session_id>/violation", methods=["POST"])
@login_required
@student_required
def student_test_violation(session_id: int):
    data = request.get_json(silent=True) or {}
    payload, error, status = report_violation(
        session_id, _current_student_id(), str(data.get("reason") or ""), data.get("answers")
    )
    if error or not payload:
        return jsonify({"error": error or "Could not record violation"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/discussion/<int:assignment_id>")
@login_required
@student_required
def student_discussion_board(assignment_id: int):
    payload, error, status = build_discussion_board_payload(assignment_id)
    if error or not payload:
        return jsonify({"error": error or "Could not load discussion"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/discussion/<int:assignment_id>/threads", methods=["POST"])
@login_required
@student_required
def student_discussion_create_thread(assignment_id: int):
    if request.content_type and "multipart/form-data" in request.content_type:
        title = request.form.get("thread_title", "")
        content = request.form.get("thread_content", "")
        files = request.files.getlist("attachments")
    else:
        data = request.get_json(silent=True) or {}
        title = data.get("thread_title") or data.get("title") or ""
        content = data.get("thread_content") or data.get("content") or ""
        files = []
    payload, error, status = create_discussion_thread_spa(
        assignment_id, title=title, content=content, files=files
    )
    if error or not payload:
        return jsonify({"error": error or "Could not create thread"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/discussion/thread/<int:thread_id>")
@login_required
@student_required
def student_discussion_thread(thread_id: int):
    payload, error, status = build_discussion_thread_payload(thread_id)
    if error or not payload:
        return jsonify({"error": error or "Could not load thread"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/discussion/thread/<int:thread_id>/reply", methods=["POST"])
@login_required
@student_required
def student_discussion_reply(thread_id: int):
    if request.content_type and "multipart/form-data" in request.content_type:
        content = request.form.get("reply_content", "")
        files = request.files.getlist("attachments")
    else:
        data = request.get_json(silent=True) or {}
        content = data.get("reply_content") or data.get("content") or ""
        files = []
    payload, error, status = reply_to_thread_spa(thread_id, content=content, files=files)
    if error or not payload:
        return jsonify({"error": error or "Could not post reply"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/discussion/thread/<int:thread_id>", methods=["PATCH"])
@login_required
@student_required
def student_discussion_edit_thread(thread_id: int):
    data = request.get_json(silent=True) or {}
    payload, error, status = edit_thread_spa(
        thread_id,
        title=data.get("thread_title") or data.get("title") or "",
        content=data.get("thread_content") or data.get("content") or "",
    )
    if error or not payload:
        return jsonify({"error": error or "Could not update thread"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/discussion/post/<int:post_id>", methods=["PATCH"])
@login_required
@student_required
def student_discussion_edit_post(post_id: int):
    data = request.get_json(silent=True) or {}
    payload, error, status = edit_post_spa(
        post_id, content=data.get("post_content") or data.get("content") or ""
    )
    if error or not payload:
        return jsonify({"error": error or "Could not update post"}), status
    return jsonify(payload)
