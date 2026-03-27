"""
Automated reminders: 2 weeks before each quarter/semester end date (school timezone).

- Students (enrolled in active school year): turn in outstanding work before the period ends.
- Staff (teachers, School Administrators, Directors): finalize grades before the period ends.

Idempotency: AcademicPeriodReminderSent rows (unique per period + audience).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytz
from flask import current_app
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import (
    AcademicPeriod,
    AcademicPeriodReminderSent,
    Class,
    Enrollment,
    SchoolYear,
    Student,
    User,
)
from services.notifications import create_notifications_for_users
from decorators import is_teacher_role

AUDIENCE_STUDENTS = 'student_assignments'
AUDIENCE_STAFF = 'staff_finalize_grades'
REMINDER_DAYS_BEFORE_END = 14


def _school_today():
    tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
    tz = pytz.timezone(tz_name)
    return datetime.now(tz).date()


def _absolute_url(path: str) -> str:
    path = path if path.startswith('/') else f'/{path}'
    base = current_app.config.get('PUBLIC_BASE_URL') or ''
    return f'{base}{path}' if base else path


def _student_user_ids_active_year(school_year_id: int) -> list[int]:
    rows = (
        db.session.query(Student.user_id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .join(Class, Class.id == Enrollment.class_id)
        .filter(
            Enrollment.is_active.is_(True),
            Class.school_year_id == school_year_id,
            Student.user_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0]]


def _staff_user_ids_for_reminders() -> list[int]:
    """Teachers, School Administrators, Directors — not students, Tech, or IT Support."""
    out: list[int] = []
    for user in User.query.all():
        r = (user.role or '').strip()
        if r in ('Student', 'Tech', 'IT Support'):
            continue
        if r in ('Director', 'School Administrator') or is_teacher_role(r):
            out.append(user.id)
    return out


def _was_sent(academic_period_id: int, audience: str) -> bool:
    return (
        AcademicPeriodReminderSent.query.filter_by(
            academic_period_id=academic_period_id,
            audience=audience,
        ).first()
        is not None
    )


def _record_sent(academic_period_id: int, audience: str) -> None:
    db.session.add(
        AcademicPeriodReminderSent(
            academic_period_id=academic_period_id,
            audience=audience,
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def run_academic_period_reminders() -> dict:
    """
    Run once per day (cron or in-process scheduler). Sends reminders when
    school-local date == period.end_date - REMINDER_DAYS_BEFORE_END.
    """
    today = _school_today()
    sy = SchoolYear.query.filter_by(is_active=True).first()
    if not sy:
        current_app.logger.info('academic_period_reminders: no active school year')
        return {'ok': True, 'skipped': 'no_active_school_year'}

    periods = AcademicPeriod.query.filter_by(
        school_year_id=sy.id,
        is_active=True,
    ).order_by(AcademicPeriod.start_date).all()

    stats = {
        'ok': True,
        'school_date': today.isoformat(),
        'periods': [],
    }

    for period in periods:
        if period.end_date < today:
            continue

        reminder_day = period.end_date - timedelta(days=REMINDER_DAYS_BEFORE_END)
        if today != reminder_day:
            continue

        period_label = f'{period.name} ({period.period_type})'
        end_fmt = period.end_date.strftime('%B %d, %Y')

        # --- Students ---
        if not _was_sent(period.id, AUDIENCE_STUDENTS):
            user_ids = _student_user_ids_active_year(sy.id)
            title = f'Reminder: {period.name} ends {end_fmt}'
            message = (
                f'School leadership reminds you that {period_label} ends on {end_fmt}. '
                f'Please submit any outstanding assignments on time so your work can be graded before the period closes.'
            )
            link = _absolute_url('/student/assignments')
            create_notifications_for_users(
                user_ids,
                'academic_period_reminder',
                title,
                message,
                link=link,
            )
            _record_sent(period.id, AUDIENCE_STUDENTS)
            stats['periods'].append({
                'period': period.name,
                'audience': AUDIENCE_STUDENTS,
                'recipients': len(user_ids),
            })
            current_app.logger.info(
                'academic_period_reminders: sent %s to %d students',
                period.name,
                len(user_ids),
            )

        # --- Teachers & admins ---
        if not _was_sent(period.id, AUDIENCE_STAFF):
            staff_ids = _staff_user_ids_for_reminders()
            title = f'Finalize grades: {period.name} ends {end_fmt}'
            message = (
                f'{period_label} ends on {end_fmt}. Please finalize grades for this period '
                f'and ensure all relevant assignments are graded so report cards and GPAs stay accurate.'
            )
            link = _absolute_url('/teacher/dashboard')
            create_notifications_for_users(
                staff_ids,
                'academic_period_reminder',
                title,
                message,
                link=link,
            )
            _record_sent(period.id, AUDIENCE_STAFF)
            stats['periods'].append({
                'period': period.name,
                'audience': AUDIENCE_STAFF,
                'recipients': len(staff_ids),
            })
            current_app.logger.info(
                'academic_period_reminders: sent %s to %d staff',
                period.name,
                len(staff_ids),
            )

    return stats
