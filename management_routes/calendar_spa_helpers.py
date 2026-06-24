"""SPA helpers for the management school calendar."""

from __future__ import annotations

import calendar as cal
from datetime import date, datetime, timedelta
from typing import Any

from models import (
    CalendarEvent,
    SchoolBreak,
    SchoolYear,
    SchoolYearClosure,
    TeacherWorkDay,
    db,
)
from services import school_year_closure as syc

from .calendar import get_academic_dates_for_calendar


def _date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _serialize_work_day(wd: TeacherWorkDay) -> dict[str, Any]:
    return {
        "id": wd.id,
        "title": wd.title,
        "date": _date_str(wd.date),
        "attendance_requirement": getattr(wd, "attendance_requirement", None),
        "description": wd.description or "",
    }


def _serialize_break(br: SchoolBreak) -> dict[str, Any]:
    return {
        "id": br.id,
        "name": br.name,
        "start_date": _date_str(br.start_date),
        "end_date": _date_str(br.end_date),
        "break_type": br.break_type,
        "description": br.description or "",
    }


def build_calendar_month(year: int, month: int) -> dict[str, Any]:
    """Month grid payload for React calendar view."""
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    month_name = current_date.strftime("%B")
    academic_dates = get_academic_dates_for_calendar(year, month)
    today = date.today()

    weeks: list[list[dict[str, Any]]] = []
    for week in cal.monthcalendar(year, month):
        week_data: list[dict[str, Any]] = []
        for day in week:
            if day == 0:
                week_data.append(
                    {
                        "day_num": None,
                        "is_current_month": False,
                        "is_today": False,
                        "events": [],
                    }
                )
            else:
                day_events = [
                    {
                        "title": academic_date["title"],
                        "category": academic_date.get("category", ""),
                        "type": academic_date.get("type", "other_event"),
                        "description": academic_date.get("description", ""),
                    }
                    for academic_date in academic_dates
                    if academic_date["day"] == day
                ]
                week_data.append(
                    {
                        "day_num": day,
                        "is_current_month": True,
                        "is_today": day == today.day and month == today.month and year == today.year,
                        "events": day_events,
                    }
                )
        weeks.append(week_data)

    events_this_month = sum(
        len(d["events"]) for week in weeks for d in week if d["is_current_month"]
    )

    return {
        "month": month,
        "year": year,
        "month_name": month_name,
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "weeks": weeks,
        "prev_month": {"month": prev_month.month, "year": prev_month.year},
        "next_month": {"month": next_month.month, "year": next_month.year},
        "events_this_month": events_this_month,
    }


def query_calendar_page(year: int | None = None, month: int | None = None) -> dict[str, Any]:
    today = date.today()
    month = month or today.month
    year = year or today.year

    active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    work_days: list[TeacherWorkDay] = []
    breaks: list[SchoolBreak] = []
    if active_school_year:
        work_days = (
            TeacherWorkDay.query.filter_by(school_year_id=active_school_year.id)
            .order_by(TeacherWorkDay.date)
            .all()
        )
        breaks = (
            SchoolBreak.query.filter_by(school_year_id=active_school_year.id)
            .order_by(SchoolBreak.start_date)
            .all()
        )

    active_closures = [
        {
            "id": c.id,
            "phase": c.phase,
            "phase_label": syc.PHASE_LABELS.get(c.phase, c.phase),
            "school_year_id": c.school_year_id,
            "school_year_name": c.school_year.name if c.school_year else None,
        }
        for c in SchoolYearClosure.query.filter(
            SchoolYearClosure.phase.notin_(syc.TERMINAL_PHASES)
        ).all()
    ]

    grid = build_calendar_month(year, month)
    return {
        **grid,
        "active_school_year": (
            {
                "id": active_school_year.id,
                "name": active_school_year.name,
                "start_date": _date_str(active_school_year.start_date),
                "end_date": _date_str(active_school_year.end_date),
            }
            if active_school_year
            else None
        ),
        "work_days": [_serialize_work_day(w) for w in work_days],
        "breaks": [_serialize_break(b) for b in breaks],
        "active_closures": active_closures,
        "event_categories": [
            {"value": "holiday", "label": "Holiday"},
            {"value": "professional_development", "label": "Professional development"},
            {"value": "other_event", "label": "Other event"},
        ],
        "break_types": ["Vacation", "Holiday", "Other"],
    }


def add_calendar_event(body: dict[str, Any]) -> dict[str, Any]:
    event_title = (body.get("event_title") or body.get("title") or "").strip()
    event_date_str = (body.get("event_date") or body.get("date") or "").strip()
    event_category = (body.get("event_category") or body.get("category") or "other_event").strip()
    event_description = (body.get("event_description") or body.get("description") or "").strip()

    if not event_title or not event_date_str:
        raise ValueError("Event title and date are required.")

    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        raise ValueError("No active school year found.")

    event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
    event_type = event_category if event_category else "other_event"
    if event_type == "other":
        event_type = "other_event"

    calendar_event = CalendarEvent(
        school_year_id=active_year.id,
        name=event_title,
        start_date=event_date,
        end_date=event_date,
        event_type=event_type,
        description=event_description or None,
    )
    db.session.add(calendar_event)
    db.session.commit()
    return {"success": True, "message": "Calendar event added successfully."}


def delete_calendar_event(event_id: int) -> dict[str, Any]:
    event = CalendarEvent.query.get(event_id)
    if not event:
        raise ValueError("Event not found.")
    db.session.delete(event)
    db.session.commit()
    return {"success": True, "message": "Calendar event deleted successfully."}


def add_school_break(body: dict[str, Any]) -> dict[str, Any]:
    name = (body.get("name") or "").strip()
    start_date_str = (body.get("start_date") or "").strip()
    end_date_str = (body.get("end_date") or "").strip()
    break_type = (body.get("break_type") or "Vacation").strip()
    description = (body.get("description") or "").strip()

    if not all([name, start_date_str, end_date_str]):
        raise ValueError("Name, start date, and end date are required.")

    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        raise ValueError("No active school year found.")

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date.")

    existing = SchoolBreak.query.filter(
        SchoolBreak.school_year_id == active_year.id,
        SchoolBreak.start_date <= end_date,
        SchoolBreak.end_date >= start_date,
    ).first()
    if existing:
        raise ValueError("A break already exists for this date range.")

    school_break = SchoolBreak(
        school_year_id=active_year.id,
        name=name,
        start_date=start_date,
        end_date=end_date,
        break_type=break_type,
        description=description,
    )
    db.session.add(school_break)
    db.session.commit()
    return {"success": True, "message": "School break added successfully."}


def delete_school_break(break_id: int) -> dict[str, Any]:
    school_break = SchoolBreak.query.get(break_id)
    if not school_break:
        raise ValueError("School break not found.")
    db.session.delete(school_break)
    db.session.commit()
    return {"success": True, "message": "School break deleted successfully."}


def add_teacher_work_days(body: dict[str, Any]) -> dict[str, Any]:
    dates_str = (body.get("dates") or "").strip()
    title = (body.get("title") or "").strip()
    attendance_requirement = (body.get("attendance_requirement") or "Mandatory").strip()
    description = (body.get("description") or "").strip()

    if not dates_str or not title:
        raise ValueError("Dates and title are required.")

    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        raise ValueError("No active school year found.")

    dates = [d.strip() for d in dates_str.split(",") if d.strip()]
    added_count = 0
    for date_str in dates:
        if "/" in date_str:
            month, day, yr = date_str.strip().split("/")
            date_obj = datetime.strptime(f"{yr}-{month.zfill(2)}-{day.zfill(2)}", "%Y-%m-%d").date()
        else:
            date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()

        existing = TeacherWorkDay.query.filter_by(
            school_year_id=active_year.id,
            date=date_obj,
        ).first()
        if not existing:
            db.session.add(
                TeacherWorkDay(
                    school_year_id=active_year.id,
                    date=date_obj,
                    title=title,
                    attendance_requirement=attendance_requirement,
                    description=description or None,
                )
            )
            added_count += 1

    db.session.commit()
    return {
        "success": True,
        "message": f"Added {added_count} teacher work day(s).",
    }


def delete_teacher_work_day(work_day_id: int) -> dict[str, Any]:
    work_day = TeacherWorkDay.query.get(work_day_id)
    if not work_day:
        raise ValueError("Teacher work day not found.")
    db.session.delete(work_day)
    db.session.commit()
    return {"success": True, "message": "Teacher work day deleted successfully."}
