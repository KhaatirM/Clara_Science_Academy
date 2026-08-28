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


@spa_api_blueprint.route("/management/schedule/planner")
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_planner():
    from management_routes.bell_schedule_spa_helpers import _parse_grade_arg

    try:
        grade = _parse_grade_arg(request.args.get("grade"))
        if grade is None:
            return jsonify({"error": "Select a specific grade for the planner"}), 400
        from utils.bell_schedule import build_schedule_planner_payload

        return jsonify(build_schedule_planner_payload(grade))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@spa_api_blueprint.route("/management/schedule/assign", methods=["POST"])
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_assign():
    from utils.bell_schedule import assign_class_to_bell_period

    body = request.get_json(silent=True) or {}
    try:
        class_id = int(body.get("class_id"))
        period_id = int(body.get("period_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "class_id and period_id are required"}), 400
    try:
        return jsonify(assign_class_to_bell_period(class_id=class_id, period_id=period_id))
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/management/schedule/unassign", methods=["POST"])
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_unassign():
    from management_routes.bell_schedule_spa_helpers import _parse_grade_arg
    from utils.bell_schedule import unassign_class_from_bell_schedule

    body = request.get_json(silent=True) or {}
    try:
        class_id = int(body.get("class_id"))
        grade_level = _parse_grade_arg(body.get("grade_level"))
        if grade_level is None:
            raise ValueError("grade_level is required")
    except (TypeError, ValueError) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    try:
        return jsonify(unassign_class_from_bell_schedule(class_id=class_id, grade_level=grade_level))
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/management/schedule/grade/<int:grade>.pdf")
@login_required
@management_required
@permissions_required("classes:manage")
def management_schedule_grade_pdf(grade: int):
    try:
        return render_grade_master_pdf(grade)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
