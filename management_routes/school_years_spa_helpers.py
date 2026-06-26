"""SPA helpers for the school years management page."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models import AcademicPeriod, CalendarEvent, SchoolYear, db
from management_routes.utils import (
    add_academic_periods_for_year,
    backfill_missing_semesters,
    sync_academic_periods_for_school_year,
    sync_semesters_from_quarters,
)


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
    for year in school_years:
        backfill_missing_semesters(year.id, commit=False)
    db.session.commit()
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
    """Redistribute Q1–Q4/S1–S2 when the school year span changes."""
    sync_academic_periods_for_school_year(school_year.id, commit=False)


def _sync_period_edit(period: AcademicPeriod) -> None:
    """When a linked quarter/semester is edited, keep related periods aligned."""
    academic_periods = AcademicPeriod.query.filter_by(school_year_id=period.school_year_id).all()
    period_map = {p.name: p for p in academic_periods}
    start_date = period.start_date
    end_date = period.end_date
    school_year = SchoolYear.query.get(period.school_year_id)

    if period.name == 'Q1':
        if 'S1' in period_map:
            period_map['S1'].start_date = start_date
        if school_year and school_year.start_date != start_date:
            school_year.start_date = start_date
    elif period.name == 'Q2':
        if 'S1' in period_map:
            period_map['S1'].end_date = end_date
    elif period.name == 'Q3':
        if 'S2' in period_map:
            period_map['S2'].start_date = start_date
    elif period.name == 'Q4':
        if 'S2' in period_map:
            period_map['S2'].end_date = end_date
        if school_year and school_year.end_date != end_date:
            school_year.end_date = end_date
    elif period.name == 'S1':
        if 'Q1' in period_map:
            period_map['Q1'].start_date = start_date
        if school_year and school_year.start_date != start_date:
            school_year.start_date = start_date
        if 'Q2' in period_map:
            period_map['Q2'].end_date = end_date
    elif period.name == 'S2':
        if 'Q3' in period_map:
            period_map['Q3'].start_date = start_date
        if 'Q4' in period_map:
            period_map['Q4'].end_date = end_date
        if school_year and school_year.end_date != end_date:
            school_year.end_date = end_date

    sync_semesters_from_quarters(period.school_year_id)


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
            backfill_missing_semesters(new_year.id, commit=False)
            message = (
                f'School year "{name}" created with quarters, semesters, and calendar dates synced!'
            )
        except Exception as exc:
            message = (
                f'School year "{name}" created but there was an error generating academic periods: {exc}'
            )

    db.session.commit()
    calendar_note = (
        ' Calendar quarter/semester dates are live when this year is active.'
        if is_active and auto_generate_quarters
        else ''
    )
    return {
        "success": True,
        "message": message + calendar_note,
        "school_year_id": new_year.id,
    }


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
            f'School year "{school_year.name}" dates updated — quarters, semesters, and calendar synced!'
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
    db.session.flush()
    sync_academic_periods_for_school_year(year_id, commit=False)
    backfill_missing_semesters(year_id, commit=False)
    db.session.commit()
    return {
        "success": True,
        "message": (
            f"Academic periods for {school_year.name} regenerated — calendar quarter/semester dates updated!"
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
    if period_type == 'quarter':
        sync_semesters_from_quarters(year_id)
    db.session.commit()
    return {
        "success": True,
        "message": f'Academic period "{name}" added — calendar will show its start/end dates when this year is active.',
    }


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
        "message": f"{period.name} updated — related periods and calendar dates synced.",
    }


def upload_calendar_pdf_from_request() -> dict[str, Any]:
    """
    Handle calendar PDF upload from multipart form (SPA or legacy).

    PDF extraction is not wired yet; validates input and returns a clear message.
    """
    from flask import request

    school_year_raw = request.form.get("school_year", "").strip()
    if not school_year_raw:
        raise ValueError("Select a school year for this calendar.")

    school_year = SchoolYear.query.get(int(school_year_raw))
    if not school_year:
        raise ValueError("School year not found.")

    upload = request.files.get("calendar_pdf")
    if not upload or not upload.filename:
        raise ValueError("A calendar PDF file is required.")

    if not upload.filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    # calendar_name = (request.form.get("calendar_name") or "").strip()
    raise ValueError(
        "PDF processing is temporarily unavailable. "
        "Add dates manually via School Years or the calendar until this feature is re-enabled."
    )
