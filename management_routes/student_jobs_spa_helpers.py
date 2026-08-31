"""Student Jobs hub data for the management React SPA."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from models import CleaningInspection, CleaningTask, CleaningTeam, CleaningTeamMember, db
from management_routes.students import get_team_detailed_description
from utils.student_jobs_catalog import (
    CLEANING,
    LUNCH_HALL,
    all_labels,
    get_inspection_type,
    inspection_type_options,
    normalize_type,
    read_flag,
)
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


def _serialize_member(
    member: CleaningTeamMember, duty_names: dict[int, str] | None = None
) -> dict[str, Any] | None:
    from utils.student_roster import student_is_archived

    if not member.student or student_is_archived(member.student):
        return None
    assignment_desc = ""
    try:
        assignment_desc = member.assignment_description or ""
    except Exception:
        pass
    task_id = getattr(member, "task_id", None)
    return {
        "id": member.student.id,
        "member_id": member.id,
        "name": f"{member.student.first_name} {member.student.last_name}",
        "role": member.role or "",
        "assignment_description": assignment_desc,
        "task_id": task_id,
        "task_name": (duty_names or {}).get(task_id) if task_id else None,
    }


VALID_TEAM_TYPES = frozenset(
    {"cleaning", "computer", "lunch_duty", "experiment_duty", "other"}
)

def inspection_deduction_options() -> list[dict[str, Any]]:
    """Labelled, point-valued deduction checkboxes for the standard cleaning form."""
    return list(get_inspection_type(CLEANING)["deductions"])


def inspection_bonus_options() -> list[dict[str, Any]]:
    return list(get_inspection_type(CLEANING)["bonuses"])


def _add_missing_columns(table: str, columns: dict[str, str]) -> bool:
    """Add columns to an existing table; this project has no migration framework.

    ``columns`` maps a column name to its DDL type clause. Each statement runs in
    its own transaction so one failure cannot leave the connection in an aborted
    state for the rest of the request.
    """
    from sqlalchemy import inspect as sa_inspect, text

    try:
        existing = {c["name"] for c in sa_inspect(db.engine).get_columns(table)}
    except Exception:
        from flask import current_app

        current_app.logger.exception("Could not inspect %s", table)
        return False

    ok = True
    for name, ddl_type in columns.items():
        if name in existing:
            continue
        try:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
        except Exception:
            from flask import current_app

            current_app.logger.exception("Could not add %s.%s", table, name)
            ok = False
    return ok


def _dialect_types() -> tuple[str, str]:
    is_postgres = db.engine.dialect.name == "postgresql"
    return ("false" if is_postgres else "0", "TIMESTAMP" if is_postgres else "DATETIME")


_INSPECTION_ARCHIVE_COLUMNS_READY = False


def ensure_inspection_archive_columns() -> bool:
    """Add the archive columns on existing databases.

    Returns whether the columns are usable, so callers can fall back to
    unfiltered queries instead of emitting SQL for a column that is missing.
    """
    global _INSPECTION_ARCHIVE_COLUMNS_READY
    if _INSPECTION_ARCHIVE_COLUMNS_READY:
        return True

    bool_default, timestamp_type = _dialect_types()
    ok = _add_missing_columns(
        "cleaning_inspection",
        {
            "is_archived": f"BOOLEAN NOT NULL DEFAULT {bool_default}",
            "archived_at": timestamp_type,
        },
    )
    _INSPECTION_ARCHIVE_COLUMNS_READY = ok
    return ok


_TEAM_COLUMNS_READY = False

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def ensure_team_columns() -> bool:
    """Add the workday column on databases created before teams had one."""
    global _TEAM_COLUMNS_READY
    if _TEAM_COLUMNS_READY:
        return True
    _TEAM_COLUMNS_READY = _add_missing_columns(
        "cleaning_team", {"days_of_week": "VARCHAR(40)"}
    )
    return _TEAM_COLUMNS_READY


def normalize_workdays(days: Any) -> list[int]:
    """Weekday ints (Mon=0) a team works; an empty list means every school day."""
    cleaned: list[int] = []
    for value in days or []:
        try:
            day = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= day <= 6 and day not in cleaned:
            cleaned.append(day)
    return sorted(cleaned)


def workday_labels(days: list[int]) -> list[str]:
    return [WEEKDAY_LABELS[d] for d in days if 0 <= d < len(WEEKDAY_LABELS)]


def _team_workdays(team: CleaningTeam) -> list[int]:
    try:
        return team.get_days_of_week()
    except Exception:
        return []


_DUTY_COLUMNS_READY = False


def ensure_duty_columns() -> bool:
    """Create the duty table and the columns that link duties, members and checklists."""
    global _DUTY_COLUMNS_READY
    if _DUTY_COLUMNS_READY:
        return True

    bool_default, _ = _dialect_types()
    try:
        CleaningTask.__table__.create(db.engine, checkfirst=True)
    except Exception:
        from flask import current_app

        current_app.logger.exception("Could not create the cleaning_task table")
        return False

    ok = _add_missing_columns(
        "cleaning_task",
        {
            "scoring_type": "VARCHAR(50)",
            "sort_order": "INTEGER DEFAULT 0",
            "is_active": f"BOOLEAN DEFAULT {'true' if bool_default == 'false' else '1'}",
        },
    )
    ok = _add_missing_columns("cleaning_team_member", {"task_id": "INTEGER"}) and ok
    ok = _add_missing_columns("cleaning_inspection", {"checklist_json": "TEXT"}) and ok

    _DUTY_COLUMNS_READY = ok
    return ok


def active_inspections_query():
    """Inspections that still 'count' — archived ones are treated as never having happened."""
    if not ensure_inspection_archive_columns():
        return CleaningInspection.query
    return CleaningInspection.query.filter(
        db.or_(CleaningInspection.is_archived.is_(False), CleaningInspection.is_archived.is_(None))
    )


def _serialize_duty(task: CleaningTask, members: list[CleaningTeamMember]) -> dict[str, Any]:
    assigned = [m for m in members if getattr(m, "task_id", None) == task.id]
    return {
        "id": task.id,
        "team_id": task.team_id,
        "name": task.task_name,
        "area": task.area_covered or "",
        "description": task.task_description or "",
        "scoring_type": normalize_type(getattr(task, "scoring_type", None)),
        "scoring_label": get_inspection_type(getattr(task, "scoring_type", None))["label"],
        "sort_order": getattr(task, "sort_order", 0) or 0,
        "assigned": [
            {"member_id": m.id, "student_id": m.student_id, "name": _member_name(m)}
            for m in assigned
        ],
    }


def _member_name(member: CleaningTeamMember) -> str:
    student = member.student
    if not student:
        return f"Student {member.student_id}"
    return f"{student.first_name} {student.last_name}"


def _team_duties(team_id: int) -> list[CleaningTask]:
    try:
        return (
            CleaningTask.query.filter(
                CleaningTask.team_id == team_id,
                db.or_(CleaningTask.is_active.is_(True), CleaningTask.is_active.is_(None)),
            )
            .order_by(CleaningTask.sort_order, CleaningTask.id)
            .all()
        )
    except Exception:
        return []


def seed_team_duties(team: CleaningTeam) -> bool:
    """Turn a team's built-in area list into editable duty records, once.

    The areas used to be hardcoded in Python and matched by team name. Seeding
    them means schools can edit, add and remove duties from the UI.
    """
    try:
        if CleaningTask.query.filter_by(team_id=team.id).first():
            return False
    except Exception:
        return False

    details = get_team_detailed_description(team) or {}
    created = 0
    order = 0

    for group_key, group in details.items():
        if group_key == "description" or not isinstance(group, dict):
            continue
        group_label = group_key.replace("_", " ").title()
        for area, instructions in group.items():
            text = str(instructions or "").strip()
            if text.upper() == "N/A":
                continue
            db.session.add(
                CleaningTask(
                    team_id=team.id,
                    task_name=area[:100],
                    area_covered=group_label[:200],
                    task_description=text,
                    scoring_type=LUNCH_HALL if area.strip().lower() == "lunch hall" else CLEANING,
                    sort_order=order,
                    is_active=True,
                )
            )
            order += 1
            created += 1

    description = details.get("description")
    if not created and isinstance(description, str) and description.strip():
        db.session.add(
            CleaningTask(
                team_id=team.id,
                task_name="Assigned duties",
                area_covered=team.team_name[:200],
                task_description=description.strip(),
                scoring_type=CLEANING,
                sort_order=0,
                is_active=True,
            )
        )
        created += 1

    if not created:
        return False
    db.session.commit()
    return True


STANDARD_CLEANING_DUTIES: list[dict[str, str]] = [
    {
        "name": "Stairway",
        "area": "Common Areas",
        "scoring_type": CLEANING,
        "description": (
            "• Swept top to bottom, including the corner of every step\n"
            "• No trash, paper or debris left on any step or landing\n"
            "• Handrail wiped down"
        ),
    },
    {
        "name": "Lunch Hall",
        "area": "Common Areas",
        "scoring_type": LUNCH_HALL,
        "description": (
            "• Tables wiped down and cleared\n"
            "• No trash on the floor\n"
            "• No dishes left out\n"
            "• All food and condiments put up\n"
            "• Trash taken out"
        ),
    },
]


def ensure_standard_duties(team: CleaningTeam) -> bool:
    """Make sure every cleaning team carries the school-wide areas.

    Teams that already had a duty list would otherwise never pick up areas added
    after they were set up.
    """
    team_type = (getattr(team, "team_type", None) or "cleaning").lower()
    if team_type != "cleaning":
        return False

    existing = _team_duties(team.id)
    have = {(duty.task_name or "").strip().lower() for duty in existing}
    order = max([duty.sort_order or 0 for duty in existing], default=-1)

    added = 0
    for standard in STANDARD_CLEANING_DUTIES:
        if standard["name"].lower() in have:
            continue
        order += 1
        db.session.add(
            CleaningTask(
                team_id=team.id,
                task_name=standard["name"],
                area_covered=standard["area"],
                task_description=standard["description"],
                scoring_type=standard["scoring_type"],
                sort_order=order,
                is_active=True,
            )
        )
        added += 1

    if not added:
        return False
    db.session.commit()
    return True


def create_team_duty(
    *,
    team_id: int,
    name: str,
    area: str = "",
    description: str = "",
    scoring_type: str = CLEANING,
) -> dict[str, Any]:
    ensure_duty_columns()
    team = CleaningTeam.query.filter_by(id=team_id, is_active=True).first()
    if not team:
        return {"success": False, "error": "Team not found."}

    duty_name = (name or "").strip()
    if not duty_name:
        return {"success": False, "error": "A duty needs a name."}

    existing = _team_duties(team_id)
    duty = CleaningTask(
        team_id=team_id,
        task_name=duty_name[:100],
        area_covered=(area or "").strip()[:200],
        task_description=(description or "").strip(),
        scoring_type=normalize_type(scoring_type),
        sort_order=(existing[-1].sort_order or 0) + 1 if existing else 0,
        is_active=True,
    )
    db.session.add(duty)
    db.session.commit()
    return {"success": True, "duty_id": duty.id, "message": f'Added duty "{duty_name}".'}


def update_team_duty(*, duty_id: int, **fields: Any) -> dict[str, Any]:
    ensure_duty_columns()
    duty = CleaningTask.query.get(duty_id)
    if not duty:
        return {"success": False, "error": "Duty not found."}

    if "name" in fields:
        new_name = (fields.get("name") or "").strip()
        if not new_name:
            return {"success": False, "error": "A duty needs a name."}
        duty.task_name = new_name[:100]
    if "area" in fields:
        duty.area_covered = (fields.get("area") or "").strip()[:200]
    if "description" in fields:
        duty.task_description = (fields.get("description") or "").strip()
    if "scoring_type" in fields:
        duty.scoring_type = normalize_type(fields.get("scoring_type"))

    db.session.commit()
    return {"success": True, "message": "Duty updated."}


def delete_team_duty(*, duty_id: int) -> dict[str, Any]:
    ensure_duty_columns()
    duty = CleaningTask.query.get(duty_id)
    if not duty:
        return {"success": False, "error": "Duty not found."}

    try:
        CleaningTeamMember.query.filter_by(task_id=duty.id).update(
            {"task_id": None}, synchronize_session=False
        )
    except Exception:
        pass
    name = duty.task_name
    db.session.delete(duty)
    db.session.commit()
    return {"success": True, "message": f'Removed duty "{name}".'}


def _serialize_inspection(inspection: CleaningInspection) -> dict[str, Any]:
    team = CleaningTeam.query.get(inspection.team_id)
    team_name = team.team_name if team else f"Team {inspection.team_id}"
    definition = get_inspection_type(inspection.inspection_type)
    status = (
        "Passed"
        if (inspection.final_score or 0) >= definition["pass_threshold"]
        else "Failed - Re-do Required"
    )
    return {
        "id": inspection.id,
        "inspection_type": definition["value"],
        "inspection_type_label": definition["label"],
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
    days_of_week: Any = None,
) -> dict[str, Any]:
    ensure_team_columns()
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
    try:
        team.set_days_of_week(normalize_workdays(days_of_week))
    except Exception:
        pass
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


def update_cleaning_team(
    *,
    team_id: int,
    name: Any = None,
    description: Any = None,
    team_type: Any = None,
    days_of_week: Any = None,
) -> dict[str, Any]:
    """Edit an existing team. Only the fields supplied are touched."""
    ensure_team_columns()
    team = CleaningTeam.query.filter_by(id=team_id, is_active=True).first()
    if not team:
        return {"success": False, "error": "Team not found or archived."}

    if name is not None:
        team_name = str(name).strip()
        if not team_name:
            return {"success": False, "error": "Team name is required."}
        clash = CleaningTeam.query.filter(
            CleaningTeam.team_name == team_name,
            CleaningTeam.id != team.id,
            CleaningTeam.is_active.is_(True),
        ).first()
        if clash:
            return {"success": False, "error": "Another team already uses this name."}
        team.team_name = team_name

    if description is not None:
        team.team_description = str(description).strip() or team.team_name

    if team_type is not None:
        normalized_type = str(team_type).strip().lower()
        if normalized_type not in VALID_TEAM_TYPES:
            return {
                "success": False,
                "error": f"Invalid team type. Choose one of: {', '.join(sorted(VALID_TEAM_TYPES))}.",
            }
        team.team_type = normalized_type

    if days_of_week is not None:
        try:
            team.set_days_of_week(normalize_workdays(days_of_week))
        except Exception:
            return {"success": False, "error": "Could not save the working days."}

    team.updated_at = datetime.utcnow()
    db.session.commit()
    return {"success": True, "team_id": team.id, "message": f'"{team.team_name}" updated.'}


def query_student_jobs_hub(*, user) -> dict[str, Any]:
    role = canonical_role_label(getattr(user, "role", None))
    ensure_team_columns()
    duties_ready = ensure_duty_columns()
    teams = _load_teams()
    team_payloads: list[dict[str, Any]] = []
    total_members = 0

    for team in teams:
        try:
            members = CleaningTeamMember.query.filter_by(team_id=team.id, is_active=True).all()
        except Exception:
            members = []

        duties: list[CleaningTask] = []
        if duties_ready:
            try:
                seed_team_duties(team)
                ensure_standard_duties(team)
                duties = _team_duties(team.id)
            except Exception:
                db.session.rollback()
                duties = []
        duty_names = {duty.id: duty.task_name for duty in duties}

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

        member_list = [
            m for m in (_serialize_member(member, duty_names) for member in members) if m
        ]
        total_members += len(member_list)
        team_type = getattr(team, "team_type", None) or (
            "computer" if "computer" in (team.team_name or "").lower() else "cleaning"
        )

        workdays = _team_workdays(team)
        team_payloads.append(
            {
                "id": team.id,
                "name": team.team_name,
                "description": team.team_description or "",
                "team_type": team_type,
                "days_of_week": workdays,
                "day_labels": workday_labels(workdays),
                "current_score": _team_current_score(team.id, recent_inspections),
                "stats": _team_stats(team_inspections),
                "members": member_list,
                "duties": [_serialize_duty(duty, members) for duty in duties],
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
        "inspection_types": inspection_type_options(),
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

    definition = get_inspection_type(inspection.inspection_type)
    labels = all_labels()
    detail = _serialize_inspection(inspection)
    detail.update(
        {
            "starting_score": inspection.starting_score,
            "is_archived": bool(getattr(inspection, "is_archived", False)),
            "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
            "deductions": [
                labels.get(item["key"], item["key"])
                for item in definition["deductions"]
                if read_flag(inspection, item["key"])
            ],
            "bonuses": [
                labels.get(item["key"], item["key"])
                for item in definition["bonuses"]
                if read_flag(inspection, item["key"])
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
