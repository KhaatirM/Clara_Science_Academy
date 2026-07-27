"""School years API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import management_required
from extensions import db
from management_routes.school_year_closure_spa_helpers import create_next_school_year
from management_routes.school_years_spa_helpers import (
    add_academic_period,
    create_school_year_from_body,
    edit_academic_period,
    edit_active_school_year_dates,
    edit_school_year_dates,
    generate_academic_periods,
    query_school_years_page,
    set_active_school_year,
    upload_calendar_pdf_from_request,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/school-years")
@login_required
@management_required
def school_years_page():
    return jsonify(query_school_years_page())


@spa_api_blueprint.route("/school-years", methods=["POST"])
@login_required
@management_required
def school_years_create():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(create_school_year_from_body(body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/<int:year_id>/set-active", methods=["POST"])
@login_required
@management_required
def school_years_set_active(year_id: int):
    try:
        return jsonify(set_active_school_year(year_id))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/active", methods=["PATCH"])
@login_required
@management_required
def school_years_edit_active():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(edit_active_school_year_dates(body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/<int:year_id>", methods=["PATCH"])
@login_required
@management_required
def school_years_edit(year_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(edit_school_year_dates(year_id, body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/<int:year_id>/periods/generate", methods=["POST"])
@login_required
@management_required
def school_years_generate_periods(year_id: int):
    try:
        return jsonify(generate_academic_periods(year_id))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/<int:year_id>/periods", methods=["POST"])
@login_required
@management_required
def school_years_add_period(year_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(add_academic_period(year_id, body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/periods/<int:period_id>", methods=["PATCH"])
@login_required
@management_required
def school_years_edit_period(period_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(edit_academic_period(period_id, body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/next", methods=["POST"])
@login_required
@management_required
def school_years_create_next():
    """Create next school year from closure dashboard."""
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(create_next_school_year(body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-years/upload-calendar-pdf", methods=["POST"])
@login_required
@management_required
def school_years_upload_calendar_pdf():
    try:
        return jsonify(upload_calendar_pdf_from_request())
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500
