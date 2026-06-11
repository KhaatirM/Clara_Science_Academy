"""Parent / family portal routes (read-only access to linked children)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from werkzeug.exceptions import HTTPException
from flask_login import current_user, login_required

from decorators import parent_required
from models import ReportCard, Student
from utils.parent_portal import (
    build_child_academic_summary,
    get_active_school_year,
    get_linked_students,
    parent_display_name,
    parent_has_access,
)
from utils.report_card_portal import (
    get_parent_visible_report_cards,
    parent_can_download_report_card,
)

parent_blueprint = Blueprint("parent", __name__)


def _resolve_active_child_id() -> int | None:
    children = get_linked_students(current_user.id)
    if not children:
        return None
    raw = session.get("parent_active_student_id")
    if raw is not None:
        try:
            sid = int(raw)
            if parent_has_access(current_user.id, sid):
                return sid
        except (TypeError, ValueError):
            pass
    session["parent_active_student_id"] = children[0].id
    return children[0].id


def _require_child_access(student_id: int) -> Student:
    if not parent_has_access(current_user.id, student_id):
        abort(403)
    return Student.query.get_or_404(student_id)


def _template_context(section: str, tab: str, **extra):
    children = get_linked_students(current_user.id)
    active_id = _resolve_active_child_id()
    active_child = None
    if active_id:
        active_child = next((c for c in children if c.id == active_id), None)
    ctx = {
        "section": section,
        "active_tab": tab,
        "dashboard_title": "Family Portal",
        "children": children,
        "active_child": active_child,
        "active_child_id": active_id,
        "parent_display_name": parent_display_name(current_user),
        "has_active_school_year": get_active_school_year() is not None,
        "school_year": get_active_school_year(),
    }
    ctx.update(extra)
    return ctx


@parent_blueprint.route("/dashboard")
@login_required
@parent_required
def parent_dashboard():
    children = get_linked_students(current_user.id)
    if not children:
        return render_template(
            "parents/role_parent_dashboard.html",
            **_template_context("home", "home", child_summaries=[]),
        )

    summaries = []
    for child in children:
        summaries.append({"child": child, **build_child_academic_summary(child.id)})

    active_id = _resolve_active_child_id()
    active_summary = next((s for s in summaries if s["child"].id == active_id), summaries[0])

    return render_template(
        "parents/role_parent_dashboard.html",
        **_template_context(
            "home",
            "home",
            child_summaries=summaries,
            active_summary=active_summary,
        ),
    )


@parent_blueprint.route("/select-child/<int:student_id>", methods=["POST"])
@login_required
@parent_required
def select_child(student_id: int):
    _require_child_access(student_id)
    session["parent_active_student_id"] = student_id
    nxt = request.args.get("next") or url_for("parent.parent_dashboard")
    return redirect(nxt)


@parent_blueprint.route("/child/<int:student_id>/grades")
@login_required
@parent_required
def child_grades(student_id: int):
    child = _require_child_access(student_id)
    session["parent_active_student_id"] = student_id
    summary = build_child_academic_summary(student_id)
    return render_template(
        "parents/role_parent_dashboard.html",
        **_template_context("grades", "grades", child=child, **summary),
    )


@parent_blueprint.route("/child/<int:student_id>/attendance")
@login_required
@parent_required
def child_attendance(student_id: int):
    child = _require_child_access(student_id)
    session["parent_active_student_id"] = student_id
    summary = build_child_academic_summary(student_id)
    return render_template(
        "parents/role_parent_dashboard.html",
        **_template_context("attendance", "attendance", child=child, **summary),
    )


@parent_blueprint.route("/child/<int:student_id>/classes")
@login_required
@parent_required
def child_classes(student_id: int):
    child = _require_child_access(student_id)
    session["parent_active_student_id"] = student_id
    summary = build_child_academic_summary(student_id)
    return render_template(
        "parents/role_parent_dashboard.html",
        **_template_context("classes", "classes", child=child, **summary),
    )


@parent_blueprint.route("/child/<int:student_id>/report-cards")
@login_required
@parent_required
def child_report_cards(student_id: int):
    child = _require_child_access(student_id)
    session["parent_active_student_id"] = student_id
    report_cards = get_parent_visible_report_cards(student_id)
    return render_template(
        "parents/role_parent_dashboard.html",
        **_template_context(
            "report_cards",
            "report_cards",
            child=child,
            report_cards=report_cards,
        ),
    )


@parent_blueprint.route("/report-card/<int:report_card_id>/pdf")
@login_required
@parent_required
def parent_report_card_pdf(report_card_id: int):
    if not parent_can_download_report_card(current_user.id, report_card_id):
        abort(403)
    report_card = ReportCard.query.get_or_404(report_card_id)
    try:
        from management_routes.reports import build_report_card_pdf_response

        return build_report_card_pdf_response(report_card)
    except ImportError:
        flash("PDF download is temporarily unavailable.", "danger")
        return redirect(url_for("parent.child_report_cards", student_id=report_card.student_id))
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        flash("Could not generate the report card PDF. Please try again later.", "danger")
        return redirect(url_for("parent.child_report_cards", student_id=report_card.student_id))


@parent_blueprint.route("/settings")
@login_required
@parent_required
def parent_settings():
    return render_template(
        "parents/role_parent_dashboard.html",
        **_template_context("settings", "settings"),
    )
