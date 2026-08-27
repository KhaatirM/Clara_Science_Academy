"""School-wide bell schedule: seed, serialize, and place classes by time overlap."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from extensions import db
from models import BellPeriod, BellSchedule, Class, ClassSchedule
from utils.school_timezone import get_school_now
from utils.school_year_filters import get_active_school_year

DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
WEEKDAYS = [0, 1, 2, 3, 4]


def grade_label(grade: int) -> str:
    if grade == 0:
        return 'Kindergarten'
    if grade == 1:
        return '1st Grade'
    if grade == 2:
        return '2nd Grade'
    if grade == 3:
        return '3rd Grade'
    return f'{grade}th Grade'


# Default Clara-style block schedule (admin can edit).
# Odd days Mon/Wed: 1,3,5,7; Even Tue/Thu: 2,4,6,8; Friday: all periods shorter.
_ODD = [0, 2]
_EVEN = [1, 3]
_FRI = [4]


def _t(h: int, m: int) -> time:
    return time(hour=h, minute=m)


def _default_period_specs() -> list[dict[str, Any]]:
    """Return seed period definitions (name, kind, start, end, color, days, sort)."""
    specs: list[dict[str, Any]] = []
    order = 0

    def add(name, kind, start, end, color, days):
        nonlocal order
        specs.append(
            {
                'name': name,
                'kind': kind,
                'start_time': start,
                'end_time': end,
                'color_hex': color,
                'days': list(days),
                'sort_order': order,
            }
        )
        order += 1

    # Mon/Wed (odd periods)
    add('Period 1', 'class', _t(8, 0), _t(9, 20), '#5B8DEE', _ODD)
    add('Break', 'break', _t(9, 20), _t(9, 35), '#A8D08D', _ODD)
    add('Period 3', 'class', _t(9, 35), _t(10, 55), '#F4A261', _ODD)
    add('Lunch', 'lunch', _t(10, 55), _t(11, 40), '#E9C46A', _ODD)
    add('Period 5', 'class', _t(11, 40), _t(13, 0), '#E76F51', _ODD)
    add('Tutorial', 'tutorial', _t(13, 0), _t(13, 30), '#9B6B9E', _ODD)
    add('Period 7', 'class', _t(13, 30), _t(14, 50), '#2A9D8F', _ODD)

    # Tue/Thu (even periods)
    add('Period 2', 'class', _t(8, 0), _t(9, 20), '#457B9D', _EVEN)
    add('Break', 'break', _t(9, 20), _t(9, 35), '#A8D08D', _EVEN)
    add('Period 4', 'class', _t(9, 35), _t(10, 55), '#E07A5F', _EVEN)
    add('Lunch', 'lunch', _t(10, 55), _t(11, 40), '#E9C46A', _EVEN)
    add('Period 6', 'class', _t(11, 40), _t(13, 0), '#3D5A80', _EVEN)
    add('Tutorial', 'tutorial', _t(13, 0), _t(13, 30), '#9B6B9E', _EVEN)
    add('Period 8', 'class', _t(13, 30), _t(14, 50), '#81B29A', _EVEN)

    # Friday — all periods shorter
    add('Period 1', 'class', _t(8, 0), _t(8, 35), '#5B8DEE', _FRI)
    add('Period 2', 'class', _t(8, 40), _t(9, 15), '#457B9D', _FRI)
    add('Period 3', 'class', _t(9, 20), _t(9, 55), '#F4A261', _FRI)
    add('Break', 'break', _t(9, 55), _t(10, 10), '#A8D08D', _FRI)
    add('Period 4', 'class', _t(10, 10), _t(10, 45), '#E07A5F', _FRI)
    add('Period 5', 'class', _t(10, 50), _t(11, 25), '#E76F51', _FRI)
    add('Lunch', 'lunch', _t(11, 25), _t(12, 5), '#E9C46A', _FRI)
    add('Period 6', 'class', _t(12, 5), _t(12, 40), '#3D5A80', _FRI)
    add('Period 7', 'class', _t(12, 45), _t(13, 20), '#2A9D8F', _FRI)
    add('Period 8', 'class', _t(13, 25), _t(14, 0), '#81B29A', _FRI)
    add('Tutorial', 'tutorial', _t(14, 0), _t(14, 30), '#9B6B9E', _FRI)

    return specs


def _times_overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return a_start < b_end and b_start < a_end


def _fmt_time(t: time | None) -> str:
    if not t:
        return ''
    return t.strftime('%I:%M %p').lstrip('0')


def _fmt_range(start: time, end: time) -> str:
    return f'{_fmt_time(start)} – {_fmt_time(end)}'


def _title_for_year(school_year, grade_level: int | None = None) -> str:
    name = (getattr(school_year, 'name', None) or '').strip()
    base = f'{name} Bell Schedule' if name else 'Bell Schedule'
    if grade_level is None:
        return base
    return f'{base} · {grade_label(grade_level)}'


def _ensure_bell_schedule_grade_column() -> None:
    """Add bell_schedule.grade_level if missing (SQLite / Postgres)."""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(db.engine)
        if 'bell_schedule' not in inspector.get_table_names():
            return
        cols = {c['name'] for c in inspector.get_columns('bell_schedule')}
        if 'grade_level' in cols:
            return
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE bell_schedule ADD COLUMN grade_level INTEGER'))
    except Exception:
        pass


def ensure_active_bell_schedule(
    school_year=None,
    *,
    grade_level: int | None = None,
) -> BellSchedule | None:
    """
    Return the active bell schedule for the year (and optional grade).

    Preference order when grade_level is set:
      1) exact grade match
      2) school-wide (grade_level NULL) — copy-seeded into a new grade schedule
      3) create fresh seeded schedule for that grade
    """
    _ensure_bell_schedule_grade_column()
    school_year = school_year or get_active_school_year()
    if not school_year:
        return None

    q = BellSchedule.query.filter_by(school_year_id=school_year.id, is_active=True)
    if grade_level is None:
        existing = (
            q.filter(BellSchedule.grade_level.is_(None))
            .order_by(BellSchedule.id.desc())
            .first()
        )
        if not existing:
            # Legacy rows may lack grade_level; prefer any active then pin as school-wide
            existing = q.order_by(BellSchedule.id.asc()).first()
            if existing and existing.grade_level is None:
                pass
            elif existing is None:
                existing = (
                    BellSchedule.query.filter_by(school_year_id=school_year.id)
                    .order_by(BellSchedule.id.asc())
                    .first()
                )
                if existing:
                    existing.is_active = True
        if existing:
            if not existing.periods:
                _seed_default_periods(existing)
                db.session.commit()
            return existing
        schedule = BellSchedule(
            school_year_id=school_year.id,
            grade_level=None,
            title=_title_for_year(school_year),
            is_active=True,
        )
        db.session.add(schedule)
        db.session.flush()
        _seed_default_periods(schedule)
        db.session.commit()
        return schedule

    # Specific grade
    existing = (
        q.filter_by(grade_level=grade_level)
        .order_by(BellSchedule.id.desc())
        .first()
    )
    if existing:
        if not existing.periods:
            _seed_default_periods(existing)
            db.session.commit()
        return existing

    # Seed from school-wide template if present
    template = ensure_active_bell_schedule(school_year, grade_level=None)
    schedule = BellSchedule(
        school_year_id=school_year.id,
        grade_level=grade_level,
        title=_title_for_year(school_year, grade_level),
        is_active=True,
    )
    db.session.add(schedule)
    db.session.flush()
    if template and template.periods:
        for src in sorted(template.periods, key=lambda p: (p.sort_order or 0, p.id or 0)):
            period = BellPeriod(
                bell_schedule_id=schedule.id,
                name=src.name,
                kind=src.kind,
                start_time=src.start_time,
                end_time=src.end_time,
                color_hex=src.color_hex,
                sort_order=src.sort_order,
                days_of_week_json=src.days_of_week_json,
            )
            db.session.add(period)
    else:
        _seed_default_periods(schedule)
    db.session.commit()
    return schedule


def _seed_default_periods(schedule: BellSchedule) -> None:
    for spec in _default_period_specs():
        period = BellPeriod(
            bell_schedule_id=schedule.id,
            name=spec['name'],
            kind=spec['kind'],
            start_time=spec['start_time'],
            end_time=spec['end_time'],
            color_hex=spec['color_hex'],
            sort_order=spec['sort_order'],
        )
        period.set_days_of_week(spec['days'])
        db.session.add(period)


def serialize_period(period: BellPeriod) -> dict[str, Any]:
    days = period.get_days_of_week()
    return {
        'id': period.id,
        'name': period.name or '',
        'kind': period.kind or 'class',
        'start_time': period.start_time.strftime('%H:%M') if period.start_time else '',
        'end_time': period.end_time.strftime('%H:%M') if period.end_time else '',
        'time_str': _fmt_range(period.start_time, period.end_time)
        if period.start_time and period.end_time
        else '',
        'color_hex': period.color_hex or '#4A90D9',
        'sort_order': int(period.sort_order or 0),
        'days_of_week': days,
        'day_labels': [DAY_SHORT[d] for d in days if 0 <= d < len(DAY_SHORT)],
    }


def serialize_bell_schedule(schedule: BellSchedule | None) -> dict[str, Any] | None:
    if not schedule:
        return None
    periods = sorted(schedule.periods or [], key=lambda p: (p.sort_order or 0, p.id or 0))
    gl = schedule.grade_level
    return {
        'id': schedule.id,
        'school_year_id': schedule.school_year_id,
        'grade_level': gl,
        'grade_label': grade_label(gl) if gl is not None else 'All grades',
        'title': schedule.title or 'Bell Schedule',
        'is_active': bool(schedule.is_active),
        'periods': [serialize_period(p) for p in periods],
    }


def _parse_hhmm(value: str) -> time:
    raw = (value or '').strip()
    if not raw:
        raise ValueError('Time is required')
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%p'):
        try:
            return datetime.strptime(raw, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    raise ValueError(f'Invalid time: {value}')


def replace_bell_schedule_periods(
    schedule: BellSchedule,
    *,
    title: str | None,
    periods_payload: list[dict[str, Any]],
) -> BellSchedule:
    """Replace all periods on the schedule from a SPA editor payload."""
    if title is not None:
        cleaned = (title or '').strip()
        if cleaned:
            schedule.title = cleaned[:120]

    # Clear existing
    for existing in list(schedule.periods or []):
        db.session.delete(existing)
    db.session.flush()

    if not periods_payload:
        raise ValueError('At least one period is required')

    for idx, raw in enumerate(periods_payload):
        name = (raw.get('name') or '').strip()
        if not name:
            raise ValueError(f'Period {idx + 1}: name is required')
        kind = (raw.get('kind') or 'class').strip().lower()
        if kind not in ('class', 'break', 'lunch', 'tutorial', 'other'):
            kind = 'other'
        start = _parse_hhmm(str(raw.get('start_time') or ''))
        end = _parse_hhmm(str(raw.get('end_time') or ''))
        if end <= start:
            raise ValueError(f'{name}: end time must be after start time')
        color = (raw.get('color_hex') or '#4A90D9').strip()
        if not color.startswith('#'):
            color = f'#{color}'
        color = color[:7]
        days_raw = raw.get('days_of_week')
        if not isinstance(days_raw, list) or not days_raw:
            raise ValueError(f'{name}: select at least one weekday')
        days = sorted({int(d) for d in days_raw if 0 <= int(d) <= 4})
        if not days:
            raise ValueError(f'{name}: select at least one weekday (Mon–Fri)')
        sort_order = int(raw.get('sort_order') if raw.get('sort_order') is not None else idx)
        period = BellPeriod(
            bell_schedule_id=schedule.id,
            name=name[:80],
            kind=kind,
            start_time=start,
            end_time=end,
            color_hex=color,
            sort_order=sort_order,
        )
        period.set_days_of_week(days)
        db.session.add(period)

    schedule.updated_at = datetime.utcnow()
    db.session.commit()
    return schedule


def _class_meeting_on_day(class_obj: Class, day_of_week: int) -> ClassSchedule | None:
    return ClassSchedule.query.filter_by(class_id=class_obj.id, day_of_week=day_of_week).first()


def _serialize_placed_class(
    class_obj: Class,
    schedule_row: ClassSchedule,
    *,
    role: str,
    now_time: time | None,
    today_weekday: int,
    day_index: int,
) -> dict[str, Any]:
    teacher = getattr(class_obj, 'teacher', None)
    teacher_name = (
        f'{teacher.first_name} {teacher.last_name}'.strip() if teacher else 'TBD'
    )
    room = schedule_row.room or getattr(class_obj, 'room_number', None) or 'TBD'
    start = schedule_row.start_time
    end = schedule_row.end_time
    is_now = False
    is_upcoming = False
    if now_time is not None and day_index == today_weekday and start and end:
        is_now = start <= now_time <= end
        is_upcoming = now_time < start
    item = {
        'class_id': class_obj.id,
        'class_name': class_obj.name or '',
        'subject': (class_obj.subject or '').strip() or 'General',
        'time_str': _fmt_range(start, end) if start and end else '',
        'room': room,
        'teacher_name': teacher_name,
        'is_now': is_now,
        'is_upcoming': is_upcoming,
    }
    if role == 'teacher':
        from models import Enrollment

        item['student_count'] = Enrollment.query.filter_by(
            class_id=class_obj.id,
            is_active=True,
        ).count()
    return item


def build_bell_grid_for_classes(
    classes: list[Class],
    *,
    role: str = 'student',
    schedule: BellSchedule | None = None,
    grade_level: int | None = None,
) -> dict[str, Any]:
    """
    Place classes onto the active bell schedule by weekday + time overlap.

    Returns:
      {
        bell_schedule: {...} | null,
        day_columns: [{day_index, day_name, day_short, is_today, cells: [...]}],
        unmapped: [...],
      }
    """
    if schedule is None:
        schedule = ensure_active_bell_schedule(grade_level=grade_level)
        # Fall back to school-wide if grade-specific missing unexpectedly
        if schedule is None and grade_level is not None:
            schedule = ensure_active_bell_schedule(grade_level=None)
    now = get_school_now()
    today_weekday = now.weekday()  # Mon=0
    now_time = now.time()

    periods = (
        sorted(schedule.periods or [], key=lambda p: (p.sort_order or 0, p.id or 0))
        if schedule
        else []
    )

    # Track which (class_id, day) meetings were placed into at least one period cell
    placed_keys: set[tuple[int, int]] = set()
    day_columns: list[dict[str, Any]] = []

    for day_index in WEEKDAYS:
        day_periods = [p for p in periods if day_index in p.get_days_of_week()]
        cells: list[dict[str, Any]] = []
        for period in day_periods:
            cell_classes: list[dict[str, Any]] = []
            if (period.kind or 'class') == 'class':
                for class_obj in classes:
                    meeting = _class_meeting_on_day(class_obj, day_index)
                    if not meeting or not meeting.start_time or not meeting.end_time:
                        continue
                    if not _times_overlap(
                        meeting.start_time,
                        meeting.end_time,
                        period.start_time,
                        period.end_time,
                    ):
                        continue
                    placed_keys.add((class_obj.id, day_index))
                    cell_classes.append(
                        _serialize_placed_class(
                            class_obj,
                            meeting,
                            role=role,
                            now_time=now_time,
                            today_weekday=today_weekday,
                            day_index=day_index,
                        )
                    )
            cell_classes.sort(key=lambda c: c.get('class_name') or '')
            cells.append(
                {
                    'period_id': period.id,
                    'name': period.name or '',
                    'kind': period.kind or 'class',
                    'time_str': _fmt_range(period.start_time, period.end_time),
                    'start_time': period.start_time.strftime('%H:%M') if period.start_time else '',
                    'end_time': period.end_time.strftime('%H:%M') if period.end_time else '',
                    'color_hex': period.color_hex or '#4A90D9',
                    'classes': cell_classes,
                    'is_now': bool(
                        day_index == today_weekday
                        and period.start_time
                        and period.end_time
                        and period.start_time <= now_time <= period.end_time
                    ),
                }
            )

        day_columns.append(
            {
                'day_index': day_index,
                'day_name': DAY_NAMES[day_index],
                'day_short': DAY_SHORT[day_index],
                'is_today': day_index == today_weekday,
                'cells': cells,
            }
        )

    unmapped: list[dict[str, Any]] = []
    for class_obj in classes:
        for day_index in range(7):
            meeting = _class_meeting_on_day(class_obj, day_index)
            if not meeting:
                continue
            if (class_obj.id, day_index) in placed_keys:
                continue
            # Weekend or no overlapping period
            if day_index > 4 or not periods:
                # Always report weekend / no-schedule meetings
                pass
            unmapped.append(
                {
                    'class_id': class_obj.id,
                    'class_name': class_obj.name or '',
                    'subject': (class_obj.subject or '').strip() or 'General',
                    'day_index': day_index,
                    'day_name': DAY_NAMES[day_index] if day_index < 7 else '',
                    'time_str': _fmt_range(meeting.start_time, meeting.end_time)
                    if meeting.start_time and meeting.end_time
                    else '',
                    'room': meeting.room or getattr(class_obj, 'room_number', None) or 'TBD',
                }
            )

    return {
        'bell_schedule': serialize_bell_schedule(schedule),
        'day_columns': day_columns,
        'unmapped': unmapped,
        'today_weekday': today_weekday,
    }


def classes_for_grade_level(grade: int, *, school_year=None) -> list[Class]:
    """Active-year classes whose grade_levels include ``grade``."""
    school_year = school_year or get_active_school_year()
    if not school_year:
        return []
    classes = (
        Class.query.filter_by(school_year_id=school_year.id, is_active=True)
        .order_by(Class.name.asc())
        .all()
    )
    matched: list[Class] = []
    for class_obj in classes:
        levels = class_obj.get_grade_levels() or []
        if grade in levels:
            matched.append(class_obj)
    return matched


def available_grade_levels(*, school_year=None) -> list[int]:
    school_year = school_year or get_active_school_year()
    if not school_year:
        return list(range(0, 13))
    grades: set[int] = set(range(0, 13))  # always offer K–12 for schedule editing
    classes = Class.query.filter_by(school_year_id=school_year.id, is_active=True).all()
    for class_obj in classes:
        for g in class_obj.get_grade_levels() or []:
            try:
                grades.add(int(g))
            except (TypeError, ValueError):
                continue
    return sorted(grades)

