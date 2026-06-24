"""SPA helpers for the school years management page."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from models import AcademicPeriod, CalendarEvent, SchoolYear, db
from management_routes.utils import add_academic_periods_for_year


def _date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _serialize_period(period: AcademicPeriod) -> dict[str, Any]:
    return {
        "id": period.id,
        "name": period.name,
        "period_type": period.period_type,
        "start_date": _date_str(period.start_date),
        "end_date": _date_str(period.end_date),
    }


def _serialize_event(ev: CalendarEvent) -> dict[str, Any]:
    return {
        "id": ev.id,
        "name": ev.name,
        "event_type": ev.event_type or "other",
        "start_date": _date_str(ev.start_date),
        "end_date": _date_str(ev.end_date),
    }


def _serialize_year(year: SchoolYear) -> dict[str, Any]:
    periods = AcademicPeriod.query.filter_by(school_year_id=year.id, is_active=True).all()
    events = CalendarEvent.query.filter_by(school_year_id=year.id).all()
    total_days = None
    if year.start_date and year.end_date:
        total_days = (year.end_date - year.start_date).days
    return {
        "id": year.id,
        "name": year.name,
        "is_active": year.is_active,
        "start_date": _date_str(year.start_date),
        "end_date": _date_str(year.end_date),
        "total_days": total_days,
        "academic_periods": [_serialize_period(p) for p in periods],
        "calendar_events": [_serialize_event(e) for e in events],
    }


def query_school_years_page() -> dict[str, Any]:
    school_years = SchoolYear.query.order_by(SchoolYear.start_date.desc()).all()
    active = SchoolYear.query.filter_by(is_active=True).first()
    serialized = [_serialize_year(y) for y in school_years]
    active_data = next((y for y in serialized if y["is_active"]), None)
    inactive_count = sum(1 for y in serialized if not y["is_active"])
    return {
        "school_years": serialized,
        "active_school_year": active_data,
        "stats": {
            "total_years": len(serialized),
            "inactive_count": inactive_count,
            "active_periods": len(active_data["academic_periods"]) if active_data else 0,
            "active_total_days": active_data["total_days"] if active_data else None,
        },
    }


def _sync_periods_after_year_edit(school_year: SchoolYear) -> None:
    academic_periods = AcademicPeriod.query.filter_by(school_year_id=school_year.id).all()
    period_map = {period.name: period for period in academic_periods}
    start_date = school_year.start_date
    end_date = school_year.end_date
    if not start_date or not end_date:
        return

    year_duration = (end_date - start_date).days
    quarter_duration = year_duration // 4

    if "Quarter 1" in period_map:
        period_map["Quarter 1"].start_date = start_date
        period_map["Quarter 1"].end_date = start_date + timedelta(days=quarter_duration - 1)

    if "Semester 1" in period_map:
        period_map["Semester 1"].start_date = start_date

    if "Quarter 2" in period_map:
        q2_start = start_date + timedelta(days=quarter_duration)
        q2_end = q2_start + timedelta(days=quarter_duration - 1)
        period_map["Quarter 2"].start_date = q2_start
        period_map["Quarter 2"].end_date = q2_end
        if "Semester 1" in period_map:
            period_map["Semester 1"].end_date = q2_end

    if "Quarter 3" in period_map:
        q3_start = start_date + timedelta(days=quarter_duration * 2)
        q3_end = q3_start + timedelta(days=quarter_duration - 1)
        period_map["Quarter 3"].start_date = q3_start
        period_map["Quarter 3"].end_date = q3_end
        if "Semester 2" in period_map:
            period_map["Semester 2"].start_date = q3_start

    if "Quarter 4" in period_map:
        q4_start = start_date + timedelta(days=quarter_duration * 3)
        period_map["Quarter 4"].start_date = q4_start
        period_map["Quarter 4"].end_date = end_date

    if "Semester 2" in period_map:
        period_map["Semester 2"].end_date = end_date


def _sync_period_edit(period: AcademicPeriod) -> None:
    academic_periods = AcademicPeriod.query.filter_by(school_year_id=period.school_year_id).all()
    period_map = {p.name: p for p in academic_periods}
    start_date = period.start_date
    end_date = period.end_date

    if period.name == "Quarter 1":
        if "Semester 1" in period_map:
            period_map["Semester 1"].start_date = start_date
        school_year = SchoolYear.query.get(period.school_year_id)
        if school_year and school_year.start_date != start_date:
            school_year.start_date = start_date
    elif period.name == "Quarter 2":
        if "Semester 1" in period_map:
            period_map["Semester 1"].end_date = end_date
    elif period.name == "Quarter 3":
        if "Semester 2" in period_map:
            period_map["Semester 2"].start_date = start_date
    elif period.name == "Quarter 4":
        if "Semester 2" in period_map:
            period_map["Semester 2"].end_date = end_date
        school_year = SchoolYear.query.get(period.school_year_id)
        if school_year and school_year.end_date != end_date:
            school_year.end_date = end_date
    elif period.name == "Semester 1":
        if "Quarter 1" in period_map:
            period_map["Quarter 1"].start_date = start_date
        school_year = SchoolYear.query.get(period.school_year_id)
        if school_year and school_year.start_date != start_date:
            school_year.start_date = start_date
        if "Quarter 2" in period_map:
            period_map["Quarter 2"].end_date = end_date
    elif period.name == "Semester 2":
        if "Quarter 3" in period_map:
            period_map["Quarter 3"].start_date = start_date
        if "Quarter 4" in period_map:
            period_map["Quarter 4"].end_date = end_date
        school_year = SchoolYear.query.get(period.school_year_id)
        if school_year and school_year.end_date != end_date:
            school_year.end_date = end_date


def create_school_year_from_body(body: dict[str, Any]) -> dict[str, Any]:
    name = (body.get("name") or "").strip()
    start_date = _parse_date(body.get("start_date"))
    end_date = _parse_date(body.get("end_date"))
    is_active = bool(body.get("is_active"))
    auto_generate_quarters = bool(body.get("auto_generate_quarters", True))

    if not name or not start_date or not end_date:
        raise ValueError("All fields are required to create a school year.")
    if start_date >= end_date:
        raise ValueError("End date must be after start date.")

    if is_active:
        SchoolYear.query.update({SchoolYear.is_active: False})

    new_year = SchoolYear(name=name, start_date=start_date, end_date=end_date, is_active=is_active)
    db.session.add(new_year)
    db.session.flush()

    message = f'School year "{name}" created successfully!'
    if auto_generate_quarters:
        try:
            add_academic_periods_for_year(new_year.id)
            message = f'School year "{name}" created successfully with academic periods!'
        except Exception as exc:
            message = (
                f'School year "{name}" created but there was an error generating academic periods: {exc}'
            )

    db.session.commit()
    return {"success": True, "message": message, "school_year_id": new_year.id}


def set_active_school_year(year_id: int) -> dict[str, Any]:
    year = SchoolYear.query.get(year_id)
    if not year:
        raise ValueError("School year not found.")
    SchoolYear.query.filter(SchoolYear.id != year_id).update({SchoolYear.is_active: False})
    year.is_active = True
    db.session.commit()
    return {"success": True, "message": f'School year "{year.name}" is now the active year.'}


def edit_school_year_dates(year_id: int, body: dict[str, Any]) -> dict[str, Any]:
    school_year = SchoolYear.query.get(year_id)
    if not school_year:
        raise ValueError("School year not found.")

    start_date = _parse_date(body.get("start_date"))
    end_date = _parse_date(body.get("end_date"))
    if not start_date or not end_date:
        raise ValueError("Both start and end dates are required.")
    if start_date >= end_date:
        raise ValueError("End date must be after start date.")

    school_year.start_date = start_date
    school_year.end_date = end_date
    _sync_periods_after_year_edit(school_year)
    db.session.commit()
    return {
        "success": True,
        "message": (
            f'School year "{school_year.name}" dates updated successfully with automatic academic period synchronization!'
        ),
    }


def edit_active_school_year_dates(body: dict[str, Any]) -> dict[str, Any]:
    active = SchoolYear.query.filter_by(is_active=True).first()
    if not active:
        raise ValueError("No active school year found.")
    return edit_school_year_dates(active.id, body)


def generate_academic_periods(year_id: int) -> dict[str, Any]:
    school_year = SchoolYear.query.get(year_id)
    if not school_year:
        raise ValueError("School year not found.")
    AcademicPeriod.query.filter_by(school_year_id=year_id).delete()
    add_academic_periods_for_year(year_id)
    db.session.commit()
    return {
        "success": True,
        "message": (
            f"Academic periods for {school_year.name} have been regenerated successfully with proper linking!"
        ),
    }


def add_academic_period(year_id: int, body: dict[str, Any]) -> dict[str, Any]:
    school_year = SchoolYear.query.get(year_id)
    if not school_year:
        raise ValueError("School year not found.")

    name = (body.get("name") or "").strip()
    period_type = (body.get("period_type") or "").strip()
    start_date = _parse_date(body.get("start_date"))
    end_date = _parse_date(body.get("end_date"))

    if not all([name, period_type, start_date, end_date]):
        raise ValueError("All fields are required.")
    if period_type not in ("quarter", "semester"):
        raise ValueError("Invalid period type. Must be quarter or semester.")
    if start_date >= end_date:
        raise ValueError("End date must be after start date.")
    if school_year.start_date and school_year.end_date:
        if start_date < school_year.start_date or end_date > school_year.end_date:
            raise ValueError("Academic period dates must fall within the school year.")

    overlapping = AcademicPeriod.query.filter(
        AcademicPeriod.school_year_id == year_id,
        AcademicPeriod.period_type == period_type,
        AcademicPeriod.start_date <= end_date,
        AcademicPeriod.end_date >= start_date,
    ).all()
    if overlapping:
        raise ValueError(f"A {period_type} already exists for the selected date range.")

    new_period = AcademicPeriod(
        name=name,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        school_year_id=year_id,
    )
    db.session.add(new_period)
    db.session.commit()
    return {"success": True, "message": f'Academic period "{name}" added successfully!'}


def edit_academic_period(period_id: int, body: dict[str, Any]) -> dict[str, Any]:
    period = AcademicPeriod.query.get(period_id)
    if not period:
        raise ValueError("Academic period not found.")

    start_date = _parse_date(body.get("start_date"))
    end_date = _parse_date(body.get("end_date"))
    if not start_date or not end_date:
        raise ValueError("Both start and end dates are required.")
    if start_date >= end_date:
        raise ValueError("End date must be after start date.")

    period.start_date = start_date
    period.end_date = end_date
    _sync_period_edit(period)
    db.session.commit()
    return {
        "success": True,
        "message": f"{period.name} dates updated successfully with automatic synchronization!",
    }
