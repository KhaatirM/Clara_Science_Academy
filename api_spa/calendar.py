"""Calendar API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import management_required
from extensions import db
from management_routes.calendar_spa_helpers import (
    add_calendar_event,
    add_school_break,
    add_teacher_work_days,
    delete_calendar_event,
    delete_school_break,
    delete_teacher_work_day,
    query_calendar_page,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/calendar")
@login_required
@management_required
def calendar_page():
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    return jsonify(query_calendar_page(year=year, month=month))


@spa_api_blueprint.route("/calendar/events", methods=["POST"])
@login_required
@management_required
def calendar_add_event():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(add_calendar_event(body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/calendar/events/<int:event_id>", methods=["DELETE"])
@login_required
@management_required
def calendar_delete_event(event_id: int):
    try:
        return jsonify(delete_calendar_event(event_id))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/calendar/breaks", methods=["POST"])
@login_required
@management_required
def calendar_add_break():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(add_school_break(body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/calendar/breaks/<int:break_id>", methods=["DELETE"])
@login_required
@management_required
def calendar_delete_break(break_id: int):
    try:
        return jsonify(delete_school_break(break_id))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/calendar/work-days", methods=["POST"])
@login_required
@management_required
def calendar_add_work_days():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(add_teacher_work_days(body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/calendar/work-days/<int:work_day_id>", methods=["DELETE"])
@login_required
@management_required
def calendar_delete_work_day(work_day_id: int):
    try:
        return jsonify(delete_teacher_work_day(work_day_id))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500
