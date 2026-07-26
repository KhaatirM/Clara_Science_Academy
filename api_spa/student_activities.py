"""Student quiz + discussion activity APIs for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import student_required
from student_discussion_spa_helpers import (
    build_discussion_board_payload,
    build_discussion_thread_payload,
    create_discussion_thread_spa,
    edit_post_spa,
    edit_thread_spa,
    reply_to_thread_spa,
)
from student_quiz_spa_helpers import build_student_quiz_payload, submit_student_quiz

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/quiz/<int:assignment_id>")
@login_required
@student_required
def student_quiz_get(assignment_id: int):
    retake = request.args.get("retake", "").lower() in ("1", "true", "yes")
    payload, error, status = build_student_quiz_payload(assignment_id, retake=retake)
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
