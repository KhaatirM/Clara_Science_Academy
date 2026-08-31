"""Student Jobs API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import management_required, permissions_required
from management_routes.student_jobs_spa_helpers import (
    archive_cleaning_team,
    archive_inspection,
    create_cleaning_team,
    create_team_duty,
    delete_inspection,
    delete_team_duty,
    get_inspection_detail,
    query_inspection_history,
    query_student_jobs_hub,
    reset_lunch_service_checks,
    set_lunch_service_check,
    update_cleaning_team,
    update_team_duty,
)
from models import db
from management_routes.students import (
    api_get_students,
    api_inspection_get,
    api_save_inspection,
    api_team_inspections,
    api_team_member_update,
    api_team_members_add,
    api_team_members_remove,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/student-jobs/hub")
@login_required
@management_required
def student_jobs_hub():
    return jsonify(query_student_jobs_hub(user=current_user))


@spa_api_blueprint.route("/student-jobs/teams", methods=["POST"])
@login_required
@management_required
def student_jobs_create_team():
    data = request.get_json(silent=True) or {}
    try:
        result = create_cleaning_team(
            name=data.get("name", ""),
            description=data.get("description", ""),
            team_type=data.get("team_type", "other"),
            student_ids=data.get("student_ids") or data.get("members") or [],
            days_of_week=data.get("days_of_week"),
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/teams/<int:team_id>", methods=["POST"])
@login_required
@management_required
def student_jobs_update_team(team_id: int):
    data = request.get_json(silent=True) or {}
    try:
        result = update_cleaning_team(
            team_id=team_id,
            name=data.get("name"),
            description=data.get("description"),
            team_type=data.get("team_type"),
            days_of_week=data.get("days_of_week"),
        )
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/teams/<int:team_id>/archive", methods=["POST"])
@login_required
@management_required
def student_jobs_archive_team(team_id: int):
    try:
        result = archive_cleaning_team(team_id=team_id)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/teams/<int:team_id>/duties", methods=["POST"])
@login_required
@management_required
def student_jobs_create_duty(team_id: int):
    data = request.get_json(silent=True) or {}
    try:
        result = create_team_duty(
            team_id=team_id,
            name=data.get("name", ""),
            area=data.get("area", ""),
            description=data.get("description", ""),
            scoring_type=data.get("scoring_type", "cleaning"),
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/duties/<int:duty_id>", methods=["POST"])
@login_required
@management_required
def student_jobs_update_duty(duty_id: int):
    data = request.get_json(silent=True) or {}
    allowed = {k: v for k, v in data.items() if k in {"name", "area", "description", "scoring_type"}}
    try:
        result = update_team_duty(duty_id=duty_id, **allowed)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/duties/<int:duty_id>", methods=["DELETE"])
@login_required
@management_required
def student_jobs_delete_duty(duty_id: int):
    try:
        result = delete_team_duty(duty_id=duty_id)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/inspections")
@login_required
@management_required
def student_jobs_inspections_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    export_all = request.args.get("export", "").lower() in {"1", "true", "yes"}
    if export_all:
        per_page = min(request.args.get("per_page", 5000, type=int), 5000)
        page = 1
    return jsonify(query_inspection_history(page=page, per_page=per_page))


@spa_api_blueprint.route("/student-jobs/students")
@login_required
@management_required
def student_jobs_students():
    return api_get_students()


@spa_api_blueprint.route("/student-jobs/teams/<int:team_id>/members", methods=["POST"])
@login_required
@management_required
def student_jobs_add_members(team_id: int):
    return api_team_members_add(team_id)


@spa_api_blueprint.route("/student-jobs/teams/<int:team_id>/members/remove", methods=["POST"])
@login_required
@management_required
def student_jobs_remove_members(team_id: int):
    return api_team_members_remove(team_id)


@spa_api_blueprint.route("/student-jobs/members/<int:member_id>", methods=["POST"])
@login_required
@management_required
def student_jobs_update_member(member_id: int):
    return api_team_member_update(member_id)


@spa_api_blueprint.route("/student-jobs/members/<int:member_id>/lunch-check", methods=["POST"])
@login_required
@management_required
def student_jobs_lunch_check(member_id: int):
    data = request.get_json(silent=True) or {}
    served = bool(data.get("served", True))
    recorded_by = " ".join(
        part
        for part in [
            getattr(current_user, "first_name", "") or "",
            getattr(current_user, "last_name", "") or "",
        ]
        if part
    )
    try:
        result = set_lunch_service_check(
            member_id=member_id, served=served, recorded_by=recorded_by
        )
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/teams/<int:team_id>/lunch-check/reset", methods=["POST"])
@login_required
@management_required
def student_jobs_lunch_check_reset(team_id: int):
    try:
        result = reset_lunch_service_checks(team_id=team_id)
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/teams/<team_identifier>/inspections")
@login_required
@management_required
def student_jobs_team_inspections(team_identifier: str):
    return api_team_inspections(team_identifier)


@spa_api_blueprint.route("/student-jobs/inspections/<int:inspection_id>")
@login_required
@management_required
def student_jobs_inspection_detail(inspection_id: int):
    try:
        result = get_inspection_detail(inspection_id=inspection_id)
    except Exception:
        # Fall back to the legacy payload rather than breaking the view action.
        return api_inspection_get(inspection_id)
    status = 200 if result.get("success") else 404
    return jsonify(result), status


@spa_api_blueprint.route(
    "/student-jobs/inspections/<int:inspection_id>/archive", methods=["POST"]
)
@login_required
@management_required
def student_jobs_archive_inspection(inspection_id: int):
    data = request.get_json(silent=True) or {}
    archived = data.get("archived", True)
    try:
        result = archive_inspection(inspection_id=inspection_id, archived=bool(archived))
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/inspections/<int:inspection_id>", methods=["DELETE"])
@login_required
@management_required
def student_jobs_delete_inspection(inspection_id: int):
    try:
        result = delete_inspection(inspection_id=inspection_id)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/student-jobs/inspections", methods=["POST"])
@login_required
@management_required
def student_jobs_save_inspection():
    return api_save_inspection()
