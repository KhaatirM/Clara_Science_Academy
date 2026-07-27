"""Student discussion board/thread payloads for the React SPA."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

from flask import current_app
from flask_login import current_user
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from management_routes.student_assistant_utils import assignment_visible_to_students
from models import (
    Assignment,
    DiscussionAttachment,
    DiscussionPost,
    DiscussionThread,
    Enrollment,
    Student,
    db,
)

ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "doc",
    "docx",
    "txt",
    "md",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
}


def _student() -> Student | None:
    sid = getattr(current_user, "student_id", None)
    return Student.query.get(sid) if sid else None


def _fmt(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        pass
    return str(value)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _student_name(student: Student | None) -> str:
    if not student:
        return "Unknown"
    return f"{student.first_name} {student.last_name}".strip()


def _initials(student: Student | None) -> str:
    if not student:
        return "?"
    a = (student.first_name or "?")[:1]
    b = (student.last_name or "")[:1]
    return f"{a}{b}".upper()


def _parse_discussion_meta(description: str | None) -> dict[str, Any]:
    raw = description or ""
    prompt = raw
    if "**Discussion Prompt:**" in raw:
        prompt = raw.split("**Discussion Prompt:**", 1)[1]
    if "**Instructions:**" in prompt:
        prompt = prompt.split("**Instructions:**", 1)[0]
    if "**Participation Requirements:**" in prompt:
        prompt = prompt.split("**Participation Requirements:**", 1)[0]
    prompt = prompt.replace("**", "").strip()

    min_initial_posts = 1
    min_replies = 2
    if "**Participation Requirements:**" in raw:
        reqs_text = raw.split("**Participation Requirements:**", 1)[1]
        initial_match = re.search(r"Minimum (\d+) initial post", reqs_text)
        replies_match = re.search(r"Minimum (\d+) reply", reqs_text)
        if initial_match:
            min_initial_posts = int(initial_match.group(1))
        if replies_match:
            min_replies = int(replies_match.group(1))

    return {
        "prompt": prompt,
        "min_initial_posts": min_initial_posts,
        "min_replies": min_replies,
    }


def _attachment_payload(att: DiscussionAttachment) -> dict[str, Any]:
    mime = att.attachment_mime_type or ""
    return {
        "id": att.id,
        "filename": att.attachment_original_filename or att.attachment_filename,
        "mime_type": mime,
        "is_image": mime.startswith("image/"),
        "size": att.attachment_file_size,
        "download_url": f"/student/discussion/attachment/{att.id}/download",
        "preview_url": f"/student/discussion/attachment/{att.id}/download?inline=1",
    }


def _access_assignment(
    assignment_id: int, student: Student
) -> tuple[Assignment | None, str | None, int]:
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return None, "Discussion not found", 404
    if not assignment_visible_to_students(assignment):
        return None, "This assignment is not available.", 403
    if assignment.assignment_type != "discussion":
        return None, "This is not a discussion assignment.", 400
    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrollment:
        return None, "You are not enrolled in this class.", 403
    return assignment, None, 200


def _save_attachments(
    files: list[FileStorage],
    *,
    thread_id: int | None = None,
    post_id: int | None = None,
    prefix: str,
) -> None:
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "discussion_attachments")
    os.makedirs(upload_dir, exist_ok=True)
    for file in files:
        if not file or not file.filename or not _allowed_file(file.filename):
            continue
        filename = secure_filename(file.filename)
        unique_filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        filepath = os.path.join(upload_dir, unique_filename)
        file.save(filepath)
        db.session.add(
            DiscussionAttachment(
                thread_id=thread_id,
                post_id=post_id,
                attachment_filename=unique_filename,
                attachment_original_filename=filename,
                attachment_file_path=os.path.join("discussion_attachments", unique_filename),
                attachment_file_size=os.path.getsize(filepath),
                attachment_mime_type=file.content_type,
            )
        )


def build_discussion_board_payload(
    assignment_id: int,
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    assignment, err, status = _access_assignment(assignment_id, student)
    if err or not assignment:
        return None, err or "Discussion not found", status

    meta = _parse_discussion_meta(assignment.description)
    threads = (
        DiscussionThread.query.filter_by(assignment_id=assignment_id)
        .order_by(DiscussionThread.is_pinned.desc(), DiscussionThread.created_at.desc())
        .all()
    )
    student_threads = DiscussionThread.query.filter_by(
        assignment_id=assignment_id, student_id=student.id
    ).all()
    student_replies = (
        DiscussionPost.query.join(DiscussionThread)
        .filter(
            DiscussionThread.assignment_id == assignment_id,
            DiscussionPost.student_id == student.id,
        )
        .all()
    )

    posts_done = len(student_threads) >= meta["min_initial_posts"]
    replies_done = len(student_replies) >= meta["min_replies"]
    participation_complete = posts_done and replies_done
    posts_pct = (
        100
        if meta["min_initial_posts"] == 0
        else min(int(len(student_threads) * 100 / meta["min_initial_posts"]), 100)
    )
    replies_pct = (
        100
        if meta["min_replies"] == 0
        else min(int(len(student_replies) * 100 / meta["min_replies"]), 100)
    )
    overall_pct = int((posts_pct + replies_pct) / 2)

    allow_edit = bool(getattr(assignment, "allow_student_edit_posts", False))
    is_active = assignment.status == "Active"

    threads_out = []
    for t in threads:
        reply_count = DiscussionPost.query.filter_by(thread_id=t.id).count()
        threads_out.append(
            {
                "id": t.id,
                "title": t.title,
                "content_preview": (t.content or "")[:180],
                "is_pinned": bool(t.is_pinned),
                "is_locked": bool(t.is_locked),
                "created_display": _fmt(t.created_at),
                "author_name": _student_name(t.student),
                "author_initials": _initials(t.student),
                "is_mine": t.student_id == student.id,
                "can_edit": allow_edit and t.student_id == student.id and is_active,
                "reply_count": reply_count,
                "url": f"/app/student/discussion/{assignment.id}/thread/{t.id}",
            }
        )

    return {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "class_name": assignment.class_info.name if assignment.class_info else None,
            "due_display": _fmt(assignment.due_date) or "No due date",
            "quarter": assignment.quarter,
            "status": assignment.status,
            "prompt": meta["prompt"],
            "is_active": is_active,
        },
        "participation": {
            "min_initial_posts": meta["min_initial_posts"],
            "min_replies": meta["min_replies"],
            "my_posts": len(student_threads),
            "my_replies": len(student_replies),
            "posts_done": posts_done,
            "replies_done": replies_done,
            "complete": participation_complete,
            "overall_pct": overall_pct,
        },
        "allow_student_threads": True,
        "allow_student_edit_posts": allow_edit,
        "threads": threads_out,
        "links": {
            "assignments": "/app/student/assignments",
            "board": f"/app/student/discussion/{assignment.id}",
        },
    }, None, 200


def build_discussion_thread_payload(
    thread_id: int,
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return None, "Thread not found", 404

    assignment = thread.assignment
    if not assignment:
        return None, "Discussion not found", 404
    if not assignment_visible_to_students(assignment):
        return None, "This assignment is not available.", 403

    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrollment:
        return None, "You are not enrolled in this class.", 403

    posts = (
        DiscussionPost.query.filter_by(thread_id=thread_id)
        .order_by(DiscussionPost.created_at.asc())
        .all()
    )
    allow_edit = bool(getattr(assignment, "allow_student_edit_posts", False))
    is_active = assignment.status == "Active"

    posts_out = []
    for p in posts:
        posts_out.append(
            {
                "id": p.id,
                "content": p.content,
                "created_display": _fmt(p.created_at),
                "author_name": (
                    "Teacher" if p.is_teacher_post else _student_name(p.student)
                ),
                "author_initials": "T" if p.is_teacher_post else _initials(p.student),
                "is_teacher_post": bool(p.is_teacher_post),
                "is_mine": (not p.is_teacher_post) and p.student_id == student.id,
                "can_edit": (
                    allow_edit
                    and (not p.is_teacher_post)
                    and p.student_id == student.id
                    and is_active
                ),
                "attachments": [_attachment_payload(a) for a in (p.attachments or [])],
            }
        )

    return {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "status": assignment.status,
            "is_active": is_active,
        },
        "thread": {
            "id": thread.id,
            "title": thread.title,
            "content": thread.content,
            "is_pinned": bool(thread.is_pinned),
            "is_locked": bool(thread.is_locked),
            "created_display": _fmt(thread.created_at),
            "author_name": _student_name(thread.student),
            "author_initials": _initials(thread.student),
            "is_mine": thread.student_id == student.id,
            "can_edit": allow_edit and thread.student_id == student.id and is_active,
            "attachments": [_attachment_payload(a) for a in (thread.attachments or [])],
        },
        "posts": posts_out,
        "allow_student_edit_posts": allow_edit,
        "can_reply": is_active and not thread.is_locked,
        "links": {
            "board": f"/app/student/discussion/{assignment.id}",
            "thread": f"/app/student/discussion/{assignment.id}/thread/{thread.id}",
            "assignments": "/app/student/assignments",
        },
    }, None, 200


def create_discussion_thread_spa(
    assignment_id: int,
    *,
    title: str,
    content: str,
    files: list[FileStorage] | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    assignment, err, status = _access_assignment(assignment_id, student)
    if err or not assignment:
        return None, err or "Discussion not found", status

    if assignment.status != "Active":
        return None, "This discussion is not currently active.", 403

    title = (title or "").strip()
    content = (content or "").strip()
    if not title or not content:
        return None, "Please provide both a title and content for your thread.", 400

    try:
        thread = DiscussionThread(
            assignment_id=assignment_id,
            student_id=student.id,
            title=title,
            content=content,
            is_pinned=False,
            is_locked=False,
        )
        db.session.add(thread)
        db.session.flush()
        _save_attachments(
            files or [],
            thread_id=thread.id,
            prefix=f"disc_{thread.id}",
        )
        db.session.commit()
        return {
            "success": True,
            "message": "Discussion thread created successfully!",
            "thread_id": thread.id,
            "redirect": f"/app/student/discussion/{assignment_id}/thread/{thread.id}",
        }, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error creating thread: {exc}", 500


def reply_to_thread_spa(
    thread_id: int,
    *,
    content: str,
    files: list[FileStorage] | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return None, "Thread not found", 404

    assignment = thread.assignment
    if not assignment:
        return None, "Discussion not found", 404

    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrollment:
        return None, "You are not enrolled in this class.", 403
    if thread.is_locked:
        return None, "This thread is locked and no longer accepts replies.", 403
    if assignment.status != "Active":
        return None, "This discussion is not currently active.", 403

    content = (content or "").strip()
    if not content:
        return None, "Please provide content for your reply.", 400

    try:
        post = DiscussionPost(
            thread_id=thread_id,
            student_id=student.id,
            content=content,
            is_teacher_post=False,
        )
        db.session.add(post)
        db.session.flush()
        _save_attachments(
            files or [],
            post_id=post.id,
            prefix=f"disc_reply_{post.id}",
        )
        db.session.commit()
        return {
            "success": True,
            "message": "Reply posted successfully!",
            "post_id": post.id,
            "redirect": f"/app/student/discussion/{assignment.id}/thread/{thread_id}",
        }, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error posting reply: {exc}", 500


def edit_thread_spa(
    thread_id: int, *, title: str, content: str
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return None, "Thread not found", 404
    assignment = thread.assignment
    if not assignment or assignment.assignment_type != "discussion":
        return None, "This is not a discussion assignment.", 400
    if not getattr(assignment, "allow_student_edit_posts", False):
        return None, "Editing posts is not allowed for this discussion.", 403
    if thread.student_id != student.id:
        return None, "You can only edit your own posts.", 403
    if assignment.status != "Active":
        return None, "This discussion is no longer active.", 403

    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrollment:
        return None, "You are not enrolled in this class.", 403

    title = (title or "").strip()
    content = (content or "").strip()
    if not title or not content:
        return None, "Please provide both a title and content.", 400

    try:
        thread.title = title
        thread.content = content
        db.session.commit()
        return {
            "success": True,
            "message": "Thread updated successfully!",
            "redirect": f"/app/student/discussion/{assignment.id}/thread/{thread_id}",
        }, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error updating thread: {exc}", 500


def edit_post_spa(
    post_id: int, *, content: str
) -> tuple[dict[str, Any] | None, str | None, int]:
    student = _student()
    if not student:
        return None, "Student profile required", 403

    post = DiscussionPost.query.get(post_id)
    if not post:
        return None, "Post not found", 404
    thread = post.thread
    assignment = thread.assignment if thread else None
    if not assignment or assignment.assignment_type != "discussion":
        return None, "This is not a discussion assignment.", 400
    if not getattr(assignment, "allow_student_edit_posts", False):
        return None, "Editing posts is not allowed for this discussion.", 403
    if post.student_id != student.id:
        return None, "You can only edit your own posts.", 403
    if post.is_teacher_post:
        return None, "Teacher posts cannot be edited by students.", 403
    if assignment.status != "Active":
        return None, "This discussion is no longer active.", 403

    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrollment:
        return None, "You are not enrolled in this class.", 403

    content = (content or "").strip()
    if not content:
        return None, "Please provide content for your post.", 400

    try:
        post.content = content
        db.session.commit()
        return {
            "success": True,
            "message": "Post updated successfully!",
            "redirect": f"/app/student/discussion/{assignment.id}/thread/{thread.id}",
        }, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error updating post: {exc}", 500
