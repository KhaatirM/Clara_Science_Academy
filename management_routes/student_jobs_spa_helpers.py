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


def _serialize_member(member: CleaningTeamMember) -> dict[str, Any] | None:
    if not member.student:
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
        total = CleaningInspection.query.count()
        inspections = (
            CleaningInspection.query.order_by(CleaningInspection.inspection_date.desc())
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

    existing = CleaningTeam.query.filter_by(team_name=team_name).first()
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
    for raw_id in student_ids or []:
        try:
            sid = int(raw_id)
        except (TypeError, ValueError):
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
            recent_inspections = (
                CleaningInspection.query.filter_by(team_id=team.id)
                .order_by(CleaningInspection.inspection_date.desc())
                .limit(5)
                .all()
            )
        except Exception:
            recent_inspections = []

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
        inspection_total = CleaningInspection.query.count()
        passed_count = CleaningInspection.query.filter(CleaningInspection.final_score >= 60).count()
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
        "urls": {"home": "/management"},
    }
