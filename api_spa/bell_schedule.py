"""Bell schedule APIs for SPA (read, management edit, grade master PDF)."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import management_required, permissions_required
from extensions import db
from management_routes.bell_schedule_spa_helpers import (
    build_grade_master_grid,
    build_management_bell_schedule_payload,
    render_grade_master_pdf,
    save_management_bell_schedule,
)
from utils.bell_schedule import ensure_active_bell_schedule, serialize_bell_schedule

from . import spa_api_blueprint


@spa_api_blueprint.route("/bell-schedule")
@login_required
def spa_bell_schedule():
    schedule = ensure_active_bell_schedule()
    return jsonify({"bell_schedule": serialize_bell_schedule(schedule)})


@spa_api_blueprint.route("/management/bell-schedule", methods=["GET"])
@login_required
@management_required
@permissions_required("classes:manage")
def management_bell_schedule_get():
    from management_routes.bell_schedule_spa_helpers import _parse_grade_arg

    try:
        grade = _parse_grade_arg(request.args.get("grade"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(build_management_bell_schedule_payload(grade))


@spa_api_blueprint.route("/management/bell-schedule", methods=["PUT"])
@login_required
@management_required
@permissions_required("classes:manage")
def management_bell_schedule_put():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_management_bell_schedule(body))
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/management/schedule/grades")
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_grades():
    payload = build_management_bell_schedule_payload()
    return jsonify(
        {
            "grades": payload.get("grades") or [],
            "school_year": payload.get("school_year"),
            "bell_schedule": payload.get("bell_schedule"),
        }
    )


@spa_api_blueprint.route("/management/schedule/grade/<int:grade>")
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_grade_preview(grade: int):
    try:
        return jsonify(build_grade_master_grid(grade))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@spa_api_blueprint.route("/management/schedule/grade/<int:grade>.pdf")
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_grade_pdf(grade: int):
    try:
        return render_grade_master_pdf(grade)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
