"""Staff list API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import management_required
from extensions import db
from models import TeacherStaff
from utils.user_roles import (
    ordered_role_labels_for_teacher_staff,
    role_badge_bootstrap_class,
    user_has_management_entry_access,
)

from . import spa_api_blueprint


def _staff_search_filter(search_query: str, search_type: str):
    if not search_query:
        return None
    q = f"%{search_query}%"
    if search_type == "name":
        return db.or_(
            TeacherStaff.first_name.ilike(q),
            TeacherStaff.last_name.ilike(q),
            TeacherStaff.middle_initial.ilike(q),
        )
    if search_type == "contact":
        return db.or_(TeacherStaff.email.ilike(q), TeacherStaff.phone.ilike(q))
    if search_type == "role":
        return db.or_(
            TeacherStaff.assigned_role.ilike(q),
            TeacherStaff.position.ilike(q),
        )
    if search_type == "department":
        return TeacherStaff.department.ilike(q)
    if search_type == "subject":
        return TeacherStaff.subject.ilike(q)
    if search_type == "staff_id":
        return TeacherStaff.staff_id.ilike(q)
    if search_type == "employment":
        return TeacherStaff.employment_type.ilike(q)
    return db.or_(
        TeacherStaff.first_name.ilike(q),
        TeacherStaff.last_name.ilike(q),
        TeacherStaff.email.ilike(q),
        TeacherStaff.assigned_role.ilike(q),
        TeacherStaff.department.ilike(q),
        TeacherStaff.staff_id.ilike(q),
    )


def _query_staff():
    search_query = (request.args.get("search") or "").strip()
    search_type = (request.args.get("search_type") or "all").strip()
    department_filter = (request.args.get("department") or "").strip()
    role_filter = (request.args.get("role") or "").strip()
    employment_filter = (request.args.get("employment") or "").strip()
    sort_by = (request.args.get("sort") or "name").strip()
    sort_order = (request.args.get("order") or "asc").strip()

    query = TeacherStaff.query.filter(TeacherStaff.is_deleted.is_(False))

    sf = _staff_search_filter(search_query, search_type)
    if sf is not None:
        query = query.filter(sf)
    if department_filter:
        query = query.filter(TeacherStaff.department.ilike(f"%{department_filter}%"))
    if role_filter:
        query = query.filter(TeacherStaff.assigned_role.ilike(f"%{role_filter}%"))
    if employment_filter:
        query = query.filter(TeacherStaff.employment_type == employment_filter)

    if sort_by == "role":
        col = TeacherStaff.assigned_role
        query = query.order_by(col.desc() if sort_order == "desc" else col)
    elif sort_by == "department":
        col = TeacherStaff.department
        query = query.order_by(col.desc() if sort_order == "desc" else col)
    elif sort_by == "hire_date":
        col = TeacherStaff.hire_date
        query = query.order_by(col.desc() if sort_order == "desc" else col)
    else:
        if sort_order == "desc":
            query = query.order_by(TeacherStaff.last_name.desc(), TeacherStaff.first_name.desc())
        else:
            query = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name)

    return query.all()


def _serialize_staff(teacher: TeacherStaff) -> dict:
    labels = ordered_role_labels_for_teacher_staff(teacher)
    status = teacher.employment_status or "Active"
    if teacher.marked_for_removal:
        status_display = "Marked for removal"
        status_tone = "danger"
    elif status == "Inactive":
        status_display = "Inactive"
        status_tone = "muted"
    elif status == "On Leave":
        status_display = "On leave"
        status_tone = "warning"
    else:
        status_display = "Active"
        status_tone = "success"

    image_url = None
    if teacher.image:
        image_url = f"/static/uploads/{teacher.image}"

    return {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "middle_initial": teacher.middle_initial,
        "last_name": teacher.last_name,
        "display_name": f"{teacher.first_name} {teacher.last_name}".strip(),
        "staff_id": teacher.staff_id,
        "email": teacher.email,
        "phone": teacher.phone,
        "department": teacher.department,
        "employment_type": teacher.employment_type,
        "employment_status": status,
        "status_display": status_display,
        "status_tone": status_tone,
        "marked_for_removal": bool(teacher.marked_for_removal),
        "portal_login": bool(getattr(teacher, "portal_login", True)),
        "has_account": teacher.user is not None,
        "username": teacher.user.username if teacher.user else None,
        "role_labels": labels,
        "role_badges": [
            {"label": lbl, "class": role_badge_bootstrap_class(lbl)} for lbl in labels
        ],
        "image_url": image_url,
        "hire_date": teacher.hire_date,
        "assigned_role": teacher.assigned_role,
    }


def _staff_directory_search_filter(q: str):
    if not q:
        return None
    like = f"%{q}%"
    return db.or_(
        TeacherStaff.first_name.ilike(like),
        TeacherStaff.last_name.ilike(like),
        TeacherStaff.middle_initial.ilike(like),
        TeacherStaff.email.ilike(like),
        TeacherStaff.staff_id.ilike(like),
        TeacherStaff.assigned_role.ilike(like),
        TeacherStaff.department.ilike(like),
        TeacherStaff.position.ilike(like),
        TeacherStaff.subject.ilike(like),
        TeacherStaff.phone.ilike(like),
    )


def _staff_display_name(teacher: TeacherStaff) -> str:
    mi = f" {teacher.middle_initial}." if teacher.middle_initial else ""
    return f"{teacher.first_name}{mi} {teacher.last_name}".strip()


def _serialize_roster_staff(teacher: TeacherStaff) -> dict:
    user = teacher.user
    role_display = user.role if user else None
    if teacher.is_deleted:
        status_display = "Removed"
        status_tone = "muted"
    elif teacher.employment_status == "Inactive":
        status_display = "Inactive"
        status_tone = "muted"
    elif teacher.marked_for_removal:
        status_display = "Marked"
        status_tone = "danger"
    elif (teacher.employment_status or "Active") == "On Leave":
        status_display = "On leave"
        status_tone = "warning"
    else:
        status_display = "Active"
        status_tone = "success"

    deleted_at = None
    if teacher.deleted_at:
        deleted_at = teacher.deleted_at.strftime("%Y-%m-%d")

    return {
        "id": teacher.id,
        "display_name": _staff_display_name(teacher),
        "staff_id": teacher.staff_id,
        "email": teacher.email,
        "department": teacher.department,
        "has_account": user is not None,
        "role_display": role_display,
        "assigned_role": teacher.assigned_role,
        "status_display": status_display,
        "status_tone": status_tone,
        "marked_for_removal": bool(teacher.marked_for_removal),
        "is_deleted": bool(teacher.is_deleted),
        "deleted_at": deleted_at,
    }


@spa_api_blueprint.route("/staff/roster")
@login_required
@management_required
def staff_roster():
    if not user_has_management_entry_access(current_user):
        return jsonify({"error": "Roster access requires Director or School Administrator role."}), 403

    tab = (request.args.get("tab") or "current").strip()
    if tab not in ("current", "former"):
        tab = "current"
    q = (request.args.get("q") or "").strip()

    current_base = TeacherStaff.query.filter(
        TeacherStaff.is_deleted.is_(False),
        db.or_(
            TeacherStaff.employment_status.in_(["Active", "On Leave"]),
            TeacherStaff.employment_status == "",
            TeacherStaff.employment_status.is_(None),
        ),
    )
    former_base = TeacherStaff.query.filter(
        db.or_(
            TeacherStaff.is_deleted.is_(True),
            TeacherStaff.employment_status == "Inactive",
        )
    )

    sf = _staff_directory_search_filter(q)
    current_count = current_base.count()
    former_count = former_base.count()

    query = current_base if tab == "current" else former_base
    if sf is not None:
        query = query.filter(sf)

    staff = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()

    return jsonify(
        {
            "tab": tab,
            "q": q,
            "counts": {"current": current_count, "former": former_count},
            "items": [_serialize_roster_staff(t) for t in staff],
        }
    )


@spa_api_blueprint.route("/staff")
@login_required
@management_required
def staff_list():
    teachers = _query_staff()
    items = [_serialize_staff(t) for t in teachers]
    with_accounts = sum(1 for t in teachers if t.user)
    full_time = sum(1 for t in teachers if t.employment_type == "Full Time")
    return jsonify(
        {
            "items": items,
            "stats": {
                "total": len(teachers),
                "with_accounts": with_accounts,
                "without_accounts": len(teachers) - with_accounts,
                "full_time": full_time,
            },
            "filters": {
                "search": (request.args.get("search") or "").strip(),
                "search_type": request.args.get("search_type") or "all",
                "department": (request.args.get("department") or "").strip(),
                "role": (request.args.get("role") or "").strip(),
                "employment": (request.args.get("employment") or "").strip(),
                "sort": request.args.get("sort") or "name",
                "order": request.args.get("order") or "asc",
            },
        }
    )
