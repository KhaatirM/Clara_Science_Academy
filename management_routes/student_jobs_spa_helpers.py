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
        all_inspections = (
            CleaningInspection.query.order_by(CleaningInspection.inspection_date.desc()).limit(50).all()
        )
    except Exception:
        all_inspections = []

    inspection_history: list[dict[str, Any]] = []
    passed_count = 0
    for inspection in all_inspections:
        team = CleaningTeam.query.get(inspection.team_id)
        team_name = team.team_name if team else f"Team {inspection.team_id}"
        status = "Passed" if inspection.final_score >= 60 else "Failed - Re-do Required"
        if status == "Passed":
            passed_count += 1
        inspection_history.append(
            {
                "id": inspection.id,
                "date": inspection.inspection_date.isoformat()
                if hasattr(inspection.inspection_date, "isoformat")
                else str(inspection.inspection_date),
                "team_id": inspection.team_id,
                "team_name": team_name,
                "score": inspection.final_score,
                "major_deductions": inspection.major_deductions,
                "bonus_points": inspection.bonus_points,
                "status": status,
                "inspector_name": inspection.inspector_name,
            }
        )

    return {
        "role_canonical": role,
        "is_director": role == "Director",
        "summary": {
            "teams": len(team_payloads),
            "members": total_members,
            "inspections": len(inspection_history),
            "passed": passed_count,
        },
        "teams": team_payloads,
        "inspection_history": inspection_history,
        "point_system": {
            "starting_points": 100,
            "redo_threshold": 60,
            "max_bonus": 15,
            "deduction_levels": "-10 / -5 / -2",
        },
        "urls": {"home": "/management"},
    }
