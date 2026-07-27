"""Management home dashboard API for the React SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import current_user, login_required

from decorators import permissions_required
from management_routes.dashboard import _serialize_feed_timestamp, build_management_home_payload

from . import spa_api_blueprint


def _json_from_payload(payload: dict) -> dict:
    out = {k: v for k, v in payload.items() if k != "notification_rows"}
    out["notifications"] = [
        {
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "timestamp": _serialize_feed_timestamp(n.timestamp),
            "link": n.link,
        }
        for n in payload.get("notification_rows") or []
    ]
    out["recent_activity"] = [
        {
            **item,
            "timestamp": _serialize_feed_timestamp(item.get("timestamp")),
        }
        for item in payload.get("recent_activity") or []
    ]
    return out


@spa_api_blueprint.route("/dashboard/home")
@login_required
@permissions_required(
    "students:view",
    "students:edit",
    "teachers_staff:manage",
    "classes:manage",
    "assignments_grades:manage",
    "attendance:manage",
    "report_cards:view",
    "report_cards:generate",
)
def dashboard_home():
    payload, error = build_management_home_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load dashboard"}), 500
    return jsonify(_json_from_payload(payload))
