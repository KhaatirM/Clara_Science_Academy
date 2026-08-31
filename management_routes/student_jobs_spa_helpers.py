"""Student Jobs hub data for the management React SPA."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from models import CleaningInspection, CleaningTeam, CleaningTeamMember, db
from management_routes.students import get_team_detailed_description
from utils.user_roles import canonical_role_label


def _load_teams() -> list[CleaningTeam]:
    from sqlalchemy import case, inspect

    inspector = inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns("cleaning_team")]

    if "team_type" in columns:
        return (
            CleaningTeam.query.filter_by(is_active=True)
            .order_by(
                case(
                    (CleaningTeam.team_type == "cleaning", 1),
                    (CleaningTeam.team_type == "computer", 2),
                    else_=3,
                ),
                CleaningTeam.team_name,
            )
            .all()
        )

    teams = CleaningTeam.query.filter_by(is_active=True).all()
    teams.sort(
        key=lambda team: (
            1
            if "computer" in team.team_name.lower() and "backup" not in team.team_name.lower()
            else 2
            if "backup" in team.team_name.lower() and "computer" in team.team_name.lower()
            else 0
            if "team 1" in team.team_name.lower() or team.team_name == "Team 1"
            else 0
            if "team 2" in team.team_name.lower() or team.team_name == "Team 2"
            else 3,
            team.team_name,
        )
    )
    return teams


def _current_week_start_est():
    from pytz import timezone as tz

    est = tz("US/Eastern")
    now_est = datetime.now(est)
    current_weekday = now_est.weekday()
    return now_est.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=current_weekday)


def _team_current_score(team_id: int, recent_inspections: list[CleaningInspection]) -> int:
    if not recent_inspections:
        return 100
    est = __import__("pytz").timezone("US/Eastern")
    current_week_start = _current_week_start_est()
    latest = recent_inspections[0]
    inspection_date = latest.inspection_date
    if isinstance(inspection_date, datetime):
        inspection_datetime = inspection_date
        if inspection_datetime.tzinfo is None:
            inspection_datetime = est.localize(inspection_datetime)
        else:
            inspection_datetime = inspection_datetime.astimezone(est)
    else:
        inspection_datetime = est.localize(datetime.combine(inspection_date, datetime.min.time()))
    if inspection_datetime < current_week_start:
        return 100
    return int(latest.final_score or 100)


def _team_stats(inspections: list[CleaningInspection]) -> dict[str, Any]:
    """Rolling performance for a team, newest inspection first."""
    scores = [int(i.final_score or 0) for i in inspections]
    if not scores:
        return {
            "inspection_count": 0,
            "average_score": None,
            "best_score": None,
            "pass_rate": None,
            "trend": None,
            "last_inspected": None,
            "sparkline": [],
        }

    passed = sum(1 for s in scores if s >= 60)
    trend = None
    if len(scores) >= 2:
        trend = scores[0] - scores[1]

    latest_date = inspections[0].inspection_date
    return {
        "inspection_count": len(scores),
        "average_score": round(sum(scores) / len(scores), 1),
        "best_score": max(scores),
        "pass_rate": round(100 * passed / len(scores)),
        "trend": trend,
        "last_inspected": latest_date.isoformat()
        if hasattr(latest_date, "isoformat")
        else str(latest_date),
        # Oldest → newest so the UI can draw it left to right.
        "sparkline": list(reversed(scores))[-10:],
    }


def _serialize_member(member: CleaningTeamMember) -> dict[str, Any] | None:
    from utils.student_roster import student_is_archived

    if not member.student or student_is_archived(member.student):
        return None
    assignment_desc = ""
    try:
        assignment_desc = member.assignment_description or ""
    except Exception:
        pass
    return {
        "id": member.student.id,
        "member_id": member.id,
        "name": f"{member.student.first_name} {member.student.last_name}",
        "role": member.role or "",
        "assignment_description": assignment_desc,
    }


VALID_TEAM_TYPES = frozenset(
    {"cleaning", "computer", "lunch_duty", "experiment_duty", "other"}
)

INSPECTION_DEDUCTION_LABELS: dict[str, str] = {
    "bathroom_not_restocked": "Bathroom not restocked",
    "trash_can_left_full": "Trash can left full",
    "floor_not_swept": "Floor not swept",
    "materials_left_out": "Materials left out",
    "tables_missed": "Tables missed",
    "classroom_trash_full": "Classroom trash full",
    "bathroom_floor_poor": "Bathroom floor in poor condition",
    "not_finished_on_time": "Not finished on time",
    "small_debris_left": "Small debris left behind",
    "trash_spilled": "Trash spilled",
    "dispensers_half_filled": "Dispensers only half filled",
}

INSPECTION_BONUS_LABELS: dict[str, str] = {
    "exceptional_finish": "Exceptional finish",
    "speed_efficiency": "Speed and efficiency",
    "going_above_beyond": "Going above and beyond",
    "teamwork_award": "Teamwork award",
}

# Point values must stay in step with frontend/src/utils/studentJobsScoring.ts.
INSPECTION_DEDUCTION_POINTS: dict[str, int] = {
    "bathroom_not_restocked": 10,
    "trash_can_left_full": 10,
    "floor_not_swept": 10,
    "materials_left_out": 10,
    "tables_missed": 5,
    "classroom_trash_full": 5,
    "bathroom_floor_poor": 5,
    "not_finished_on_time": 5,
    "small_debris_left": 2,
    "trash_spilled": 2,
    "dispensers_half_filled": 2,
}

INSPECTION_BONUS_POINTS: dict[str, int] = {
    "exceptional_finish": 5,
    "speed_efficiency": 5,
    "going_above_beyond": 3,
    "teamwork_award": 2,
}

_SEVERITY_BY_POINTS = {10: "major", 5: "moderate", 2: "minor"}


def inspection_deduction_options() -> list[dict[str, Any]]:
    """Labelled, point-valued deduction checkboxes for the inspection form."""
    return [
        {
            "key": key,
            "label": label,
            "points": INSPECTION_DEDUCTION_POINTS.get(key, 0),
            "severity": _SEVERITY_BY_POINTS.get(INSPECTION_DEDUCTION_POINTS.get(key, 0), "minor"),
        }
        for key, label in INSPECTION_DEDUCTION_LABELS.items()
    ]


def inspection_bonus_options() -> list[dict[str, Any]]:
    return [
        {"key": key, "label": label, "points": INSPECTION_BONUS_POINTS.get(key, 0)}
        for key, label in INSPECTION_BONUS_LABELS.items()
    ]


_INSPECTION_ARCHIVE_COLUMNS_READY = False


def ensure_inspection_archive_columns() -> bool:
    """Add the archive columns on existing databases (no migration framework here).

    Returns whether the columns are usable, so callers can fall back to
    unfiltered queries instead of emitting SQL for a column that is missing.
    """
    global _INSPECTION_ARCHIVE_COLUMNS_READY
    if _INSPECTION_ARCHIVE_COLUMNS_READY:
        return True
    from sqlalchemy import inspect as sa_inspect, text

    try:
        is_postgres = db.engine.dialect.name == 'postgresql'
        bool_default = 'false' if is_postgres else '0'
        timestamp_type = 'TIMESTAMP' if is_postgres else 'DATETIME'

        columns = {c["name"] for c in sa_inspect(db.engine).get_columns("cleaning_inspection")}
        statements = []
        if "is_archived" not in columns:
            statements.append(
                "ALTER TABLE cleaning_inspection "
                f"ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT {bool_default}"
            )
        if "archived_at" not in columns:
            statements.append(
                f"ALTER TABLE cleaning_inspection ADD COLUMN archived_at {timestamp_type}"
            )
        # Each statement gets its own transaction so one failure cannot leave the
        # connection in an aborted state for the rest of the request.
        for statement in statements:
            with db.engine.begin() as conn:
                conn.execute(text(statement))
    except Exception:
        from flask import current_app

        current_app.logger.exception("Could not add cleaning_inspection archive columns")
        return False
    _INSPECTION_ARCHIVE_COLUMNS_READY = True
    return True


def active_inspections_query():
    """Inspections that still 'count' — archived ones are treated as never having happened."""
    if not ensure_inspection_archive_columns():
        return CleaningInspection.query
    return CleaningInspection.query.filter(
        db.or_(CleaningInspection.is_archived.is_(False), CleaningInspection.is_archived.is_(None))
    )


def _serialize_inspection(inspection: CleaningInspection) -> dict[str, Any]:
    team = CleaningTeam.query.get(inspection.team_id)
    team_name = team.team_name if team else f"Team {inspection.team_id}"
    status = "Passed" if inspection.final_score >= 60 else "Failed - Re-do Required"
    return {
        "id": inspection.id,
        "date": inspection.inspection_date.isoformat()
        if hasattr(inspection.inspection_date, "isoformat")
        else str(inspection.inspection_date),
        "team_id": inspection.team_id,
        "team_name": team_name,
        "score": inspection.final_score,
        "major_deductions": inspection.major_deductions,
        "moderate_deductions": inspection.moderate_deductions,
        "minor_deductions": inspection.minor_deductions,
        "bonus_points": inspection.bonus_points,
        "status": status,
        "inspector_name": inspection.inspector_name,
        "inspector_notes": inspection.inspector_notes or "",
    }


def query_inspection_history(*, page: int = 1, per_page: int = 10) -> dict[str, Any]:
    page = max(1, page)
    per_page = max(1, min(per_page, 100))

    try:
        total = active_inspections_query().count()
        inspections = (
            active_inspections_query()
            .order_by(CleaningInspection.inspection_date.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    except Exception:
        total = 0
        inspections = []

    items = [_serialize_inspection(inspection) for inspection in inspections]
    passed_on_page = sum(1 for item in items if item["status"] == "Passed")

    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page) if total else 1,
        },
        "passed_on_page": passed_on_page,
    }


def create_cleaning_team(
    *,
    name: str,
    description: str,
    team_type: str,
    student_ids: list[int] | None = None,
) -> dict[str, Any]:
    team_name = (name or "").strip()
    if not team_name:
        return {"success": False, "error": "Team name is required."}

    normalized_type = (team_type or "other").strip().lower()
    if normalized_type not in VALID_TEAM_TYPES:
        return {"success": False, "error": f"Invalid team type. Choose one of: {', '.join(sorted(VALID_TEAM_TYPES))}."}

    existing = CleaningTeam.query.filter_by(team_name=team_name, is_active=True).first()
    if existing:
        return {"success": False, "error": "A team with this name already exists."}

    team = CleaningTeam(
        team_name=team_name,
        team_description=(description or "").strip() or team_name,
        team_type=normalized_type,
        is_active=True,
    )
    db.session.add(team)
    db.session.flush()

    added = 0
    from utils.student_roster import filter_student_ids_on_roster

    allowed_ids = set(
        filter_student_ids_on_roster(
            [int(x) for x in (student_ids or []) if str(x).isdigit() or isinstance(x, int)],
            require_active_enrollment=False,
        )
    )
    for raw_id in student_ids or []:
        try:
            sid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if sid not in allowed_ids:
            continue
        already = CleaningTeamMember.query.filter_by(
            team_id=team.id, student_id=sid, is_active=True
        ).first()
        if already:
            continue
        db.session.add(
            CleaningTeamMember(
                team_id=team.id,
                student_id=sid,
                role="Team Member",
                is_active=True,
            )
        )
        added += 1

    db.session.commit()
    member_note = f" with {added} member(s)" if added else ""
    return {
        "success": True,
        "team_id": team.id,
        "message": f'Team "{team_name}" created{member_note}.',
    }


def query_student_jobs_hub(*, user) -> dict[str, Any]:
    role = canonical_role_label(getattr(user, "role", None))
    teams = _load_teams()
    team_payloads: list[dict[str, Any]] = []
    total_members = 0

    for team in teams:
        try:
            members = CleaningTeamMember.query.filter_by(team_id=team.id, is_active=True).all()
        except Exception:
            members = []

        try:
            team_inspections = (
                active_inspections_query()
                .filter(CleaningInspection.team_id == team.id)
                .order_by(CleaningInspection.inspection_date.desc())
                .limit(20)
                .all()
            )
        except Exception:
            team_inspections = []
        recent_inspections = team_inspections[:5]

        member_list = [m for m in (_serialize_member(member) for member in members) if m]
        total_members += len(member_list)
        team_type = getattr(team, "team_type", None) or (
            "computer" if "computer" in (team.team_name or "").lower() else "cleaning"
        )

        team_payloads.append(
            {
                "id": team.id,
                "name": team.team_name,
                "description": team.team_description or "",
                "team_type": team_type,
                "current_score": _team_current_score(team.id, recent_inspections),
                "stats": _team_stats(team_inspections),
                "members": member_list,
                "detailed_description": get_team_detailed_description(team),
                "recent_inspections": [
                    {
                        "id": inspection.id,
                        "date": inspection.inspection_date.isoformat()
                        if hasattr(inspection.inspection_date, "isoformat")
                        else str(inspection.inspection_date),
                        "score": inspection.final_score,
                        "status": "Passed" if inspection.final_score >= 60 else "Failed - Re-do Required",
                        "inspector_name": inspection.inspector_name,
                    }
                    for inspection in recent_inspections
                ],
            }
        )

    try:
        inspection_total = active_inspections_query().count()
        passed_count = active_inspections_query().filter(
            CleaningInspection.final_score >= 60
        ).count()
    except Exception:
        inspection_total = 0
        passed_count = 0

    inspection_page = query_inspection_history(page=1, per_page=10)

    return {
        "role_canonical": role,
        "is_director": role == "Director",
        "summary": {
            "teams": len(team_payloads),
            "members": total_members,
            "inspections": inspection_total,
            "passed": passed_count,
        },
        "teams": team_payloads,
        "inspection_history": inspection_page["items"],
        "inspection_pagination": inspection_page["pagination"],
        "point_system": {
            "starting_points": 100,
            "redo_threshold": 60,
            "max_bonus": 15,
            "deduction_levels": "-10 / -5 / -2",
        },
        "deduction_options": inspection_deduction_options(),
        "bonus_options": inspection_bonus_options(),
        "team_type_options": [
            {"value": "cleaning", "label": "Cleaning"},
            {"value": "computer", "label": "Computer"},
            {"value": "lunch_duty", "label": "Lunch duty"},
            {"value": "experiment_duty", "label": "Experiment duty"},
            {"value": "other", "label": "Other"},
        ],
        "urls": {"home": "/management"},
    }


def archive_cleaning_team(*, team_id: int) -> dict[str, Any]:
    """Soft-archive a team so it no longer appears in the active hub."""
    team = CleaningTeam.query.filter_by(id=team_id, is_active=True).first()
    if not team:
        return {"success": False, "error": "Team not found or already archived."}

    team.is_active = False
    team.updated_at = datetime.utcnow()

    CleaningTeamMember.query.filter_by(team_id=team.id, is_active=True).update(
        {"is_active": False},
        synchronize_session=False,
    )

    db.session.commit()
    return {
        "success": True,
        "message": f'Team "{team.team_name}" archived. Inspection history is preserved.',
    }


def get_inspection_detail(*, inspection_id: int) -> dict[str, Any]:
    ensure_inspection_archive_columns()
    inspection = CleaningInspection.query.get(inspection_id)
    if not inspection:
        return {"success": False, "error": "Inspection not found."}

    detail = _serialize_inspection(inspection)
    detail.update(
        {
            "inspection_type": inspection.inspection_type or "cleaning",
            "starting_score": inspection.starting_score,
            "is_archived": bool(getattr(inspection, "is_archived", False)),
            "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
            "deductions": [
                label
                for attr, label in INSPECTION_DEDUCTION_LABELS.items()
                if getattr(inspection, attr, False)
            ],
            "bonuses": [
                label
                for attr, label in INSPECTION_BONUS_LABELS.items()
                if getattr(inspection, attr, False)
            ],
        }
    )
    return {"success": True, "inspection": detail}


def archive_inspection(*, inspection_id: int, archived: bool = True) -> dict[str, Any]:
    """Hide an inspection so it no longer counts, keeping the record recoverable."""
    if not ensure_inspection_archive_columns():
        return {"success": False, "error": "Archiving is unavailable until the database is updated."}
    inspection = CleaningInspection.query.get(inspection_id)
    if not inspection:
        return {"success": False, "error": "Inspection not found."}

    inspection.is_archived = bool(archived)
    inspection.archived_at = datetime.utcnow() if archived else None
    db.session.commit()
    return {
        "success": True,
        "message": (
            "Inspection archived. It no longer counts toward the team's score."
            if archived
            else "Inspection restored."
        ),
    }


def delete_inspection(*, inspection_id: int) -> dict[str, Any]:
    """Permanently remove an inspection."""
    ensure_inspection_archive_columns()
    inspection = CleaningInspection.query.get(inspection_id)
    if not inspection:
        return {"success": False, "error": "Inspection not found."}

    db.session.delete(inspection)
    db.session.commit()
    return {"success": True, "message": "Inspection deleted."}
