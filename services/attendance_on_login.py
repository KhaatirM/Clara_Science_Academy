"""
Record school-day attendance when a student logs in.

Rules (in school local time):
- Login 7:00 AM – 9:59 AM: marked Present
- Login 10:00 AM – 2:59 PM: marked Late
- Outside that window: no auto-record (staff can mark manually)

When SCHOOL_TIMEZONE is not set or is 'UTC', server local time is used so
it works without configuration for single-timezone deployments.
"""

from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore


def _now_in_school_tz(app):
    """Return (date, hour) for 'now' in school timezone (or server local)."""
    date, hour, _ = _now_in_school_tz_full(app)
    return date, hour


def _now_in_school_tz_full(app):
    """Return (date, hour, minute) for 'now' in school timezone (or server local)."""
    tz_name = app.config.get('SCHOOL_TIMEZONE') or 'UTC'
    if ZoneInfo is None:
        now = datetime.now()
        return now.date(), now.hour, now.minute
    if tz_name.upper() == 'UTC':
        now = datetime.now().astimezone()
        return now.date(), now.hour, now.minute
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('UTC')
    now = datetime.now(tz)
    return now.date(), now.hour, now.minute


def is_past_end_of_day_cutoff(app):
    """True if it's the same calendar day (school tz) and time is >= 3:30 PM."""
    today, hour, minute = _now_in_school_tz_full(app)
    return hour > 15 or (hour == 15 and minute >= 30)


def apply_end_of_day_automark(app, target_date, student_ids=None):
    """
    Create SchoolDayAttendance with status 'Unexcused Absence' for any student
    who has no record for target_date. If student_ids is given, only consider
    those students; otherwise all students.
    Returns the number of new records created.
    """
    from models import db, Student, SchoolDayAttendance

    students = Student.query.filter(Student.id.in_(student_ids)) if student_ids else Student.query
    student_ids_list = [s.id for s in students]
    existing = {
        r.student_id for r in
        SchoolDayAttendance.query.filter(
            SchoolDayAttendance.date == target_date,
            SchoolDayAttendance.student_id.in_(student_ids_list)
        ).all()
    }
    to_create = [sid for sid in student_ids_list if sid not in existing]
    count = 0
    for student_id in to_create:
        record = SchoolDayAttendance(
            student_id=student_id,
            date=target_date,
            status='Unexcused Absence',
            notes='Auto-marked end of day (no attendance recorded by 3:30 PM)',
            recorded_by=None
        )
        db.session.add(record)
        count += 1
    if count:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return count


def record_school_day_attendance_on_login(user):
    """
    If the logged-in user is a student, optionally create a SchoolDayAttendance
    record for today based on login time (school timezone or server local).
    Only creates a record if one does not already exist for today.
    """
    if not user or getattr(user, 'role', None) != 'Student':
        return
    student_id = getattr(user, 'student_id', None)
    if not student_id:
        return

    from flask import current_app
    from models import db, SchoolDayAttendance

    today, hour = _now_in_school_tz(current_app)

    # 7–10 AM → Present; 10 AM–3 PM → Late; otherwise do not auto-record
    if 7 <= hour < 10:
        status = 'Present'
    elif 10 <= hour < 15:
        status = 'Late'
    else:
        return

    existing = SchoolDayAttendance.query.filter_by(
        student_id=student_id,
        date=today
    ).first()
    if existing:
        return

    record = SchoolDayAttendance(
        student_id=student_id,
        date=today,
        status=status,
        notes='Auto-recorded on login',
        recorded_by=None
    )
    db.session.add(record)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
