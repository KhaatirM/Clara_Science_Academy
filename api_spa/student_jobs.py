"""Student Jobs API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import management_required, permissions_required
from management_routes.student_jobs_spa_helpers import query_student_jobs_hub
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


@spa_api_blueprint.route("/student-jobs/teams/<team_identifier>/inspections")
@login_required
@management_required
def student_jobs_team_inspections(team_identifier: str):
    return api_team_inspections(team_identifier)


@spa_api_blueprint.route("/student-jobs/inspections/<int:inspection_id>")
@login_required
@management_required
def student_jobs_inspection_detail(inspection_id: int):
    return api_inspection_get(inspection_id)


@spa_api_blueprint.route("/student-jobs/inspections", methods=["POST"])
@login_required
@management_required
def student_jobs_save_inspection():
    return api_save_inspection()
