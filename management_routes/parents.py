"""Management: provision parent portal logins and list family accounts."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import permissions_required
from extensions import db
from models import ParentStudentLink, Student, User
from utils.parent_portal import (
    parent_portal_status_for_student,
    parent_slot_fields,
    sync_student_parent_portal,
)
from utils.user_roles import user_has_management_entry_access
from utils.spa_management_urls import react_spa_enabled

bp = Blueprint("parents", __name__)


def _parents_wants_json() -> bool:
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    return "application/json" in (request.headers.get("Accept") or "").lower()


def query_parents_hub() -> dict:
    """Shared list + stats for legacy hub and SPA API."""
    parent_users = User.query.filter_by(role="Parent").order_by(User.username).all()
    items = []
    for u in parent_users:
        links = (
            ParentStudentLink.query.filter_by(parent_user_id=u.id)
            .join(Student)
            .order_by(Student.last_name, Student.first_name)
            .all()
        )
        children = []
        for lnk in links:
            if not lnk.student:
                continue
            children.append(
                {
                    "id": lnk.student.id,
                    "display_name": f"{lnk.student.first_name} {lnk.student.last_name}".strip(),
                }
            )
        items.append(
            {
                "id": u.id,
                "username": u.username or "",
                "email": u.email or "",
                "initial": (u.username or "P")[0].upper(),
                "children": children,
                "link_count": len(links),
            }
        )

    students_with_parent_email = Student.query.filter(
        Student.is_deleted.is_(False),
        db.or_(
            Student.parent1_email.isnot(None),
            Student.parent2_email.isnot(None),
        ),
    ).count()

    linked_student_ids = {
        row[0] for row in db.session.query(ParentStudentLink.student_id).distinct().all()
    }
    students_pending_link = Student.query.filter(
        Student.is_deleted.is_(False),
        Student.is_active.is_(True),
        db.or_(
            Student.parent1_email.isnot(None),
            Student.parent2_email.isnot(None),
        ),
    ).all()
    students_not_linked = sum(1 for s in students_pending_link if s.id not in linked_student_ids)
    total_child_links = ParentStudentLink.query.count()

    return {
        "items": items,
        "stats": {
            "parent_accounts": len(parent_users),
            "students_with_parent_email": students_with_parent_email,
            "total_child_links": total_child_links,
            "students_not_linked": students_not_linked,
        },
    }


@bp.route("/parents")
@login_required
@permissions_required("students:view", "students:edit")
def parents_hub():
    """List parent portal accounts and linked children."""
    if (
        react_spa_enabled()
        and user_has_management_entry_access(current_user)
        and request.args.get("legacy") != "1"
    ):
        return redirect("/app/management/parents")

    payload = query_parents_hub()
    rows = [
        {
            "user": User.query.get(item["id"]),
            "children": [c["display_name"] for c in item["children"]],
            "link_count": item["link_count"],
        }
        for item in payload["items"]
    ]
    stats = payload["stats"]
    return render_template(
        "management/parents_hub.html",
        rows=rows,
        parent_accounts=stats["parent_accounts"],
        students_with_parent_email=stats["students_with_parent_email"],
        students_not_linked=stats["students_not_linked"],
        total_child_links=stats["total_child_links"],
        section="parents",
    )


@bp.route("/parents/status/<int:student_id>")
@login_required
@permissions_required("students:view")
def parent_status_json(student_id: int):
    student = Student.query.get_or_404(student_id)
    return jsonify(parent_portal_status_for_student(student))


@bp.route("/parents/provision/<int:student_id>", methods=["POST"])
@login_required
@permissions_required("students:edit")
def provision_parent_login(student_id: int):
    student = Student.query.get_or_404(student_id)
    payload = request.get_json(silent=True) if request.is_json else None
    slot_raw = (payload or {}).get("slot") or request.form.get("slot") or "both"
    want_json = request.is_json or _parents_wants_json()

    try:
        if slot_raw in ("1", "2"):
            info = parent_slot_fields(student, int(slot_raw))
            if not info.get("email"):
                msg = f"Parent {slot_raw} has no email on file."
                if want_json:
                    return jsonify({"success": False, "message": msg}), 400
                flash(msg, "warning")
                return redirect(request.referrer or url_for("management.students"))

        status_before = parent_portal_status_for_student(student)
        if not (status_before["parent1"]["has_email"] or status_before["parent2"]["has_email"]):
            msg = "No parent emails on file for this student."
            if want_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "warning")
            return redirect(request.referrer or url_for("management.students"))

        results = sync_student_parent_portal(student)
        db.session.commit()

        emails_sent = 0
        parents_emailed = 0
        if results:
            try:
                from services.email_service import notify_parent_login_credentials

                mail_stats = notify_parent_login_credentials(
                    results,
                    context_note=f"Provisioned from student record (#{student.id}).",
                )
                emails_sent = mail_stats.get("admins_emailed", 0)
                parents_emailed = mail_stats.get("parents_emailed", 0)
            except Exception as e:
                current_app.logger.warning("Parent login credential emails failed: %s", e)

        if results:
            msg = f"Parent portal ready — {len(results)} login(s) with temporary passwords."
            if parents_emailed:
                msg += f" Emailed {parents_emailed} parent(s) their own login."
            if emails_sent:
                msg += f" Emailed {emails_sent} school admin recipient(s)."
        else:
            msg = "Parent portal links synced with parent info on file (no new temporary passwords)."
        if want_json:
            return jsonify(
                {
                    "success": True,
                    "message": msg,
                    "results": results,
                    "emails_sent": emails_sent,
                    "parents_emailed": parents_emailed,
                }
            )
        flash(msg, "success")
    except ValueError as e:
        db.session.rollback()
        if want_json:
            return jsonify({"success": False, "message": str(e)}), 400
        flash(str(e), "danger")
    except Exception:
        db.session.rollback()
        if want_json:
            return jsonify({"success": False, "message": "Failed to provision parent login."}), 500
        flash("Failed to provision parent login.", "danger")

    return redirect(request.referrer or url_for("management.students"))


def _run_bulk_parent_provision() -> dict:
    students = Student.query.filter(
        Student.is_deleted.is_(False),
        Student.is_active.is_(True),
        db.or_(
            Student.parent1_email.isnot(None),
            Student.parent2_email.isnot(None),
        ),
    ).all()

    created = 0
    reissued = 0
    linked = 0
    skipped = 0
    errors: list[str] = []
    credentials: list[dict] = []
    seen_usernames: set[str] = set()

    for student in students:
        try:
            status = parent_portal_status_for_student(student)
            if not (status["parent1"]["has_email"] or status["parent2"]["has_email"]):
                skipped += 1
                continue
            before = ParentStudentLink.query.filter_by(student_id=student.id).count()
            rows = sync_student_parent_portal(student)
            after = ParentStudentLink.query.filter_by(student_id=student.id).count()
            created += sum(1 for r in rows if r.get("created_new"))
            reissued += sum(1 for r in rows if r.get("password_reissued") and not r.get("created_new"))
            linked += max(0, after - before)
            for row in rows:
                uname = (row.get("username") or "").lower()
                if not row.get("portal_password") or not uname or uname in seen_usernames:
                    continue
                seen_usernames.add(uname)
                credentials.append(row)
        except ValueError as e:
            errors.append(f"{student.first_name} {student.last_name}: {e}")
        except Exception:
            errors.append(f"{student.first_name} {student.last_name}: unexpected error")

    db.session.commit()

    emails_sent = 0
    parents_emailed = 0
    if credentials:
        try:
            from services.email_service import notify_parent_login_credentials

            mail_stats = notify_parent_login_credentials(
                credentials,
                context_note="Bulk provision from Management → Family Portal.",
            )
            emails_sent = mail_stats.get("admins_emailed", 0)
            parents_emailed = mail_stats.get("parents_emailed", 0)
        except Exception as e:
            current_app.logger.warning("Parent login credential emails failed: %s", e)

    return {
        "linked": linked,
        "created": created,
        "reissued": reissued,
        "skipped": skipped,
        "errors": errors,
        "credentials": credentials,
        "emails_sent": emails_sent,
        "parents_emailed": parents_emailed,
    }


@bp.route("/parents/provision-all", methods=["POST"])
@login_required
@permissions_required("students:edit")
def provision_all_parent_logins():
    """Bulk-create parent accounts from parent1/parent2 emails on active students."""
    try:
        result = _run_bulk_parent_provision()
    except Exception:
        db.session.rollback()
        msg = "Bulk parent provisioning failed to save."
        if _parents_wants_json():
            return jsonify({"success": False, "message": msg}), 500
        flash(msg, "danger")
        return redirect(url_for("management.parents.parents_hub"))

    linked = result["linked"]
    created = result["created"]
    reissued = result.get("reissued", 0)
    skipped = result["skipped"]
    errors = result["errors"]
    credentials = result.get("credentials") or []
    emails_sent = result.get("emails_sent") or 0
    parents_emailed = result.get("parents_emailed") or 0
    msg = (
        f"Parent provisioning complete: {linked} link(s), {created} new account(s), "
        f"{reissued} temporary password(s) re-issued, {skipped} student(s) skipped."
    )
    if credentials:
        msg += f" {len(credentials)} login(s) ready."
    if parents_emailed:
        msg += f" Emailed {parents_emailed} parent(s) their own login."
    elif credentials:
        msg += " Could not email parents (check mail config or parent emails on file)."
    if emails_sent:
        msg += f" Emailed {emails_sent} school admin recipient(s)."
    elif credentials:
        msg += " Could not email school admins (check mail config or admin emails on file)."

    if _parents_wants_json():
        return jsonify(
            {
                "success": True,
                "message": msg,
                "linked": linked,
                "created": created,
                "reissued": reissued,
                "skipped": skipped,
                "errors": errors[:5],
                "credentials": [
                    {
                        "slot": r.get("slot"),
                        "student_id": r.get("student_id"),
                        "student_name": r.get("student_name"),
                        "parent_name": r.get("parent_name"),
                        "email": r.get("email"),
                        "username": r.get("username"),
                        "portal_password": r.get("portal_password"),
                        "created_new": bool(r.get("created_new")),
                        "password_reissued": bool(r.get("password_reissued")),
                    }
                    for r in credentials
                ],
                "emails_sent": emails_sent,
                "parents_emailed": parents_emailed,
            }
        )

    flash(msg, "success" if not errors else "warning")
    for err in errors[:5]:
        flash(err, "warning")
    return redirect(url_for("management.parents.parents_hub"))
