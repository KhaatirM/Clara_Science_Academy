"""School-wide bell schedule: seed, serialize, and place classes by time overlap."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from extensions import db
from models import BellPeriod, BellPeriodClassAssignment, BellSchedule, Class, ClassSchedule
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


# Default weekly bell slots (one row per period; class days chosen at assignment time).
_WEEK = [0, 1, 2, 3, 4]


def _t(h: int, m: int) -> time:
    return time(hour=h, minute=m)


def _default_period_specs() -> list[dict[str, Any]]:
    """Return seed period definitions for the full week."""
    specs: list[dict[str, Any]] = []
    order = 0

    def add(name, kind, start, end, color):
        nonlocal order
        specs.append(
            {
                'name': name,
                'kind': kind,
                'start_time': start,
                'end_time': end,
                'color_hex': color,
                'days': list(_WEEK),
                'sort_order': order,
            }
        )
        order += 1

    add('Period 1', 'class', _t(8, 0), _t(9, 20), '#5B8DEE')
    add('Period 2', 'class', _t(8, 0), _t(9, 20), '#457B9D')
    add('Break', 'break', _t(9, 20), _t(9, 35), '#A8D08D')
    add('Period 3', 'class', _t(9, 35), _t(10, 55), '#F4A261')
    add('Period 4', 'class', _t(9, 35), _t(10, 55), '#E07A5F')
    add('Lunch', 'lunch', _t(10, 55), _t(11, 40), '#E9C46A')
    add('Period 5', 'class', _t(11, 40), _t(13, 0), '#E76F51')
    add('Period 6', 'class', _t(11, 40), _t(13, 0), '#3D5A80')
    add('Tutorial', 'tutorial', _t(13, 0), _t(13, 30), '#9B6B9E')
    add('Period 7', 'class', _t(13, 30), _t(14, 50), '#2A9D8F')
    add('Period 8', 'class', _t(13, 30), _t(14, 50), '#81B29A')
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


def _ensure_period_usage_label_column() -> None:
    """Add bell_period.usage_label if missing."""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(db.engine)
        if 'bell_period' not in inspector.get_table_names():
            return
        cols = {c['name'] for c in inspector.get_columns('bell_period')}
        if 'usage_label' in cols:
            return
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE bell_period ADD COLUMN usage_label VARCHAR(120)'))
    except Exception:
        pass


def _ensure_assignment_days_column() -> None:
    """Add bell_period_class_assignment.days_of_week_json if missing."""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(db.engine)
        if 'bell_period_class_assignment' not in inspector.get_table_names():
            return
        cols = {c['name'] for c in inspector.get_columns('bell_period_class_assignment')}
        if 'days_of_week_json' in cols:
            return
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE bell_period_class_assignment "
                    "ADD COLUMN days_of_week_json VARCHAR(80) DEFAULT '[0,1,2,3,4]'"
                )
            )
    except Exception:
        pass


def _ensure_class_schedule_int_days() -> None:
    """Older SQLite databases declared class_schedule.day_of_week as VARCHAR.

    Text weekdays break integer comparisons and day lookups, so rebuild the
    column as INTEGER once and coerce the stored values.
    """
    from sqlalchemy import inspect, text

    try:
        if db.engine.dialect.name != 'sqlite':
            return
        inspector = inspect(db.engine)
        if 'class_schedule' not in inspector.get_table_names():
            return
        column = next(
            (c for c in inspector.get_columns('class_schedule') if c['name'] == 'day_of_week'),
            None,
        )
        if column is None or 'CHAR' not in str(column['type']).upper():
            return

        with db.engine.begin() as conn:
            conn.execute(text('PRAGMA foreign_keys=OFF'))
            conn.execute(
                text(
                    'CREATE TABLE class_schedule_migrated ('
                    ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
                    ' class_id INTEGER NOT NULL,'
                    ' day_of_week INTEGER NOT NULL,'
                    ' start_time TIME NOT NULL,'
                    ' end_time TIME NOT NULL,'
                    ' room VARCHAR(50),'
                    ' FOREIGN KEY (class_id) REFERENCES class (id))'
                )
            )
            conn.execute(
                text(
                    'INSERT INTO class_schedule_migrated'
                    ' (id, class_id, day_of_week, start_time, end_time, room)'
                    ' SELECT id, class_id, CAST(day_of_week AS INTEGER),'
                    ' start_time, end_time, room FROM class_schedule'
                )
            )
            conn.execute(text('DROP TABLE class_schedule'))
            conn.execute(text('ALTER TABLE class_schedule_migrated RENAME TO class_schedule'))
            conn.execute(text('PRAGMA foreign_keys=ON'))
    except Exception:
        pass


def _weekday_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_weekdays(days: list | None) -> list[int]:
    if not days:
        return []
    return sorted({int(d) for d in days if 0 <= int(d) <= 4})


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
    _ensure_period_usage_label_column()
    _ensure_assignment_days_column()
    _ensure_class_schedule_int_days()
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
                usage_label=src.usage_label,
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
        'usage_label': (period.usage_label or '').strip() or None,
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
    """Save the periods on a schedule from a SPA editor payload.

    Periods are matched on id and updated in place so that editing the bell
    schedule does not throw away the classes already assigned to its periods.
    """
    if title is not None:
        cleaned = (title or '').strip()
        if cleaned:
            schedule.title = cleaned[:120]

    if not periods_payload:
        raise ValueError('At least one period is required')

    existing = {period.id: period for period in list(schedule.periods or [])}
    kept: list[BellPeriod] = []
    seen_ids: set[int] = set()

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
        days = _normalize_weekdays(days_raw)
        if not days:
            raise ValueError(f'{name}: select at least one weekday (Mon–Fri)')
        sort_order = int(raw.get('sort_order') if raw.get('sort_order') is not None else idx)
        usage_label = (raw.get('usage_label') or '').strip()[:120] or None

        raw_id = raw.get('id')
        period = existing.get(int(raw_id)) if str(raw_id or '').isdigit() else None
        if period is None:
            period = BellPeriod(bell_schedule_id=schedule.id)
            db.session.add(period)
        else:
            seen_ids.add(period.id)

        period.name = name[:80]
        period.kind = kind
        period.usage_label = usage_label
        period.start_time = start
        period.end_time = end
        period.color_hex = color
        period.sort_order = sort_order
        period.set_days_of_week(days)
        kept.append(period)

    removed = [period for pid, period in existing.items() if pid not in seen_ids]
    # Classes on a removed period lose their meeting times, so remember them.
    affected_class_ids = _assigned_class_ids([period.id for period in removed])
    for period in removed:
        db.session.delete(period)
    db.session.flush()

    affected_class_ids |= _prune_assignments_outside_periods(kept)

    schedule.updated_at = datetime.utcnow()
    db.session.flush()
    db.session.expire(schedule, ['periods'])
    for class_id in affected_class_ids:
        class_obj = Class.query.get(class_id)
        if class_obj:
            _sync_class_from_bell_assignments(class_obj, schedule)

    db.session.commit()
    return schedule


def _assigned_class_ids(period_ids: list[int]) -> set[int]:
    if not period_ids:
        return set()
    rows = BellPeriodClassAssignment.query.filter(
        BellPeriodClassAssignment.bell_period_id.in_(period_ids)
    ).all()
    return {row.class_id for row in rows}


def _prune_assignments_outside_periods(periods: list[BellPeriod]) -> set[int]:
    """Drop or clamp assignments a period edit has invalidated.

    Reserving a period with a usage label, changing its kind, or removing a
    weekday all mean the classes sitting there can no longer meet then.
    """
    affected: set[int] = set()
    for period in periods:
        if not period.id:
            continue
        assignments = BellPeriodClassAssignment.query.filter_by(bell_period_id=period.id).all()
        if not assignments:
            continue

        reserved = bool((period.usage_label or '').strip()) or (period.kind or 'class') != 'class'
        period_days = _normalize_weekdays(period.get_days_of_week())
        for assignment in assignments:
            affected.add(assignment.class_id)
            if reserved:
                db.session.delete(assignment)
                continue
            allowed = [day for day in assignment.get_days_of_week() if day in period_days]
            if allowed:
                assignment.set_days_of_week(allowed)
            else:
                db.session.delete(assignment)

    db.session.flush()
    return affected


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

    class_by_id = {c.id: c for c in classes}
    assignments_by_period_day: dict[tuple[int, int], list[Class]] = {}
    assigned_class_ids: set[int] = set()
    if schedule:
        period_ids = {p.id for p in periods}
        rows = (
            BellPeriodClassAssignment.query.filter(
                BellPeriodClassAssignment.bell_period_id.in_(period_ids)
            ).all()
            if period_ids
            else []
        )
        for row in rows:
            class_obj = class_by_id.get(row.class_id)
            if not class_obj:
                continue
            assigned_class_ids.add(class_obj.id)
            for day_index in row.get_days_of_week():
                assignments_by_period_day.setdefault((row.bell_period_id, day_index), []).append(
                    class_obj
                )

    # Track which (class_id, day) meetings were placed into at least one period cell
    placed_keys: set[tuple[int, int]] = set()
    day_columns: list[dict[str, Any]] = []

    for day_index in WEEKDAYS:
        cells: list[dict[str, Any]] = []
        for period in periods:
            if day_index not in period.get_days_of_week():
                continue
            cell_classes: list[dict[str, Any]] = []
            usage_label = (period.usage_label or '').strip()
            if (period.kind or 'class') == 'class' and not usage_label:
                explicit = assignments_by_period_day.get((period.id, day_index)) or []
                if explicit:
                    for class_obj in explicit:
                        meeting = _class_meeting_on_day(class_obj, day_index)
                        if not meeting:
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
                else:
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
                    'usage_label': usage_label or None,
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
        if class_obj.id in assigned_class_ids:
            continue
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


def _sync_class_from_bell_assignments(class_obj: Class, schedule: BellSchedule) -> None:
    """Rebuild Mon–Fri ClassSchedule rows from bell assignments on this schedule."""
    period_ids = [p.id for p in (schedule.periods or [])]
    assignments = (
        BellPeriodClassAssignment.query.filter(
            BellPeriodClassAssignment.class_id == class_obj.id,
            BellPeriodClassAssignment.bell_period_id.in_(period_ids),
        ).all()
        if period_ids
        else []
    )

    for day_index in WEEKDAYS:
        row = ClassSchedule.query.filter_by(class_id=class_obj.id, day_of_week=day_index).first()
        if row:
            db.session.delete(row)

    room = getattr(class_obj, 'room_number', None) or None
    for assignment in assignments:
        period = assignment.bell_period
        if not period:
            continue
        for day_index in assignment.get_days_of_week():
            db.session.add(
                ClassSchedule(
                    class_id=class_obj.id,
                    day_of_week=day_index,
                    start_time=period.start_time,
                    end_time=period.end_time,
                    room=room,
                )
            )
    rebuild_class_schedule_text(class_obj)


def rebuild_class_schedule_text(class_obj: Class) -> None:
    """Rebuild Class.schedule display string from ClassSchedule rows."""
    rows = (
        ClassSchedule.query.filter_by(class_id=class_obj.id)
        .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
        .all()
    )
    parts: list[str] = []
    for row in rows:
        day = _weekday_int(row.day_of_week)
        if day is None or day < 0 or day >= len(DAY_SHORT):
            continue
        if not row.start_time or not row.end_time:
            continue
        parts.append(f'{DAY_SHORT[day]} {_fmt_time(row.start_time)}-{_fmt_time(row.end_time)}')
    class_obj.schedule = ', '.join(parts) if parts else None


def _days_within_period(period: BellPeriod, days_of_week: list[int] | None) -> list[int]:
    """Clamp requested weekdays to the days the period actually runs."""
    period_days = _normalize_weekdays(period.get_days_of_week()) or list(_WEEK)
    if days_of_week is None:
        return period_days
    requested = _normalize_weekdays(days_of_week)
    if not requested:
        raise ValueError('Select at least one weekday (Mon–Fri)')
    allowed = [d for d in requested if d in period_days]
    if not allowed:
        labels = ', '.join(DAY_SHORT[d] for d in period_days)
        raise ValueError(f'{period.name} only runs on {labels}. Pick one of those days.')
    return allowed


def assign_class_to_bell_period(
    *,
    class_id: int,
    period_id: int,
    days_of_week: list[int] | None = None,
) -> dict[str, Any]:
    """Assign a class to a bell period and sync meeting times on selected weekdays."""
    period = BellPeriod.query.get(period_id)
    if not period:
        raise ValueError('Period not found')
    if (period.kind or 'class') != 'class':
        raise ValueError('Only class periods accept class assignments')
    if (period.usage_label or '').strip():
        raise ValueError(
            f'{period.name} is reserved for "{period.usage_label.strip()}". '
            'Clear its label to assign classes.'
        )
    class_obj = Class.query.get(class_id)
    if not class_obj:
        raise ValueError('Class not found')
    schedule = period.bell_schedule
    if not schedule:
        raise ValueError('Bell period has no parent schedule')

    days = _days_within_period(period, days_of_week)

    sibling_period_ids = [p.id for p in (schedule.periods or [])]
    existing = (
        BellPeriodClassAssignment.query.filter(
            BellPeriodClassAssignment.class_id == class_id,
            BellPeriodClassAssignment.bell_period_id.in_(sibling_period_ids),
        ).all()
        if sibling_period_ids
        else []
    )
    for row in existing:
        db.session.delete(row)

    assignment = BellPeriodClassAssignment(bell_period_id=period_id, class_id=class_id)
    assignment.set_days_of_week(days)
    db.session.add(assignment)
    _sync_class_from_bell_assignments(class_obj, schedule)
    db.session.commit()
    return {
        'success': True,
        'class_id': class_id,
        'period_id': period_id,
        'days_of_week': days,
        'schedule_text': class_obj.schedule,
    }


def update_bell_period_assignment_days(
    *,
    class_id: int,
    period_id: int,
    days_of_week: list[int],
) -> dict[str, Any]:
    """Change which weekdays a class meets during its assigned period."""
    period = BellPeriod.query.get(period_id)
    if not period:
        raise ValueError('Period not found')
    class_obj = Class.query.get(class_id)
    if not class_obj:
        raise ValueError('Class not found')
    schedule = period.bell_schedule
    if not schedule:
        raise ValueError('Bell period has no parent schedule')

    days = _days_within_period(period, days_of_week)

    assignment = BellPeriodClassAssignment.query.filter_by(
        bell_period_id=period_id,
        class_id=class_id,
    ).first()
    if not assignment:
        raise ValueError('Class is not assigned to this period')

    assignment.set_days_of_week(days)
    _sync_class_from_bell_assignments(class_obj, schedule)
    db.session.commit()
    return {
        'success': True,
        'class_id': class_id,
        'period_id': period_id,
        'days_of_week': days,
        'schedule_text': class_obj.schedule,
    }


def unassign_class_from_bell_schedule(*, class_id: int, grade_level: int) -> dict[str, Any]:
    """Remove a class from all period slots on the grade bell schedule."""
    schedule = ensure_active_bell_schedule(grade_level=grade_level)
    if not schedule:
        raise ValueError('No bell schedule for this grade')
    class_obj = Class.query.get(class_id)
    if not class_obj:
        raise ValueError('Class not found')
    period_ids = [p.id for p in (schedule.periods or [])]
    rows = (
        BellPeriodClassAssignment.query.filter(
            BellPeriodClassAssignment.class_id == class_id,
            BellPeriodClassAssignment.bell_period_id.in_(period_ids),
        ).all()
        if period_ids
        else []
    )
    for row in rows:
        db.session.delete(row)
    if rows:
        _sync_class_from_bell_assignments(class_obj, schedule)
    else:
        rebuild_class_schedule_text(class_obj)
    db.session.commit()
    return {'success': True, 'class_id': class_id}


def reset_bell_schedule_periods(schedule: BellSchedule) -> BellSchedule:
    """Replace all periods with the simplified weekly template (clears class assignments)."""
    for period in list(schedule.periods or []):
        db.session.delete(period)
    db.session.flush()
    _seed_default_periods(schedule)
    schedule.updated_at = datetime.utcnow()
    db.session.commit()
    return schedule


def _serialize_class_planner_card(class_obj: Class) -> dict[str, Any]:
    teacher = getattr(class_obj, 'teacher', None)
    teacher_name = (
        f'{teacher.first_name} {teacher.last_name}'.strip() if teacher else 'TBD'
    )
    return {
        'class_id': class_obj.id,
        'class_name': class_obj.name or '',
        'subject': (class_obj.subject or '').strip() or 'General',
        'room': getattr(class_obj, 'room_number', None) or 'TBD',
        'teacher_name': teacher_name,
        'schedule_text': (class_obj.schedule or '').strip() or None,
        'grade_levels': class_obj.get_grade_levels() or [],
    }


def build_schedule_planner_payload(grade_level: int) -> dict[str, Any]:
    """Payload for drag-and-drop period planner (management)."""
    schedule = ensure_active_bell_schedule(grade_level=grade_level)
    if not schedule:
        raise ValueError('No bell schedule for this grade')
    classes = classes_for_grade_level(grade_level)
    class_by_id = {c.id: c for c in classes}
    periods = sorted(schedule.periods or [], key=lambda p: (p.sort_order or 0, p.id or 0))

    assignments_by_period: dict[int, list[dict[str, Any]]] = {}
    assigned_ids: set[int] = set()
    for period in periods:
        if (period.kind or 'class') != 'class' or (period.usage_label or '').strip():
            continue
        cards = []
        for row in period.class_assignments or []:
            class_obj = class_by_id.get(row.class_id)
            if not class_obj:
                continue
            days = row.get_days_of_week()
            cards.append(
                {
                    **_serialize_class_planner_card(class_obj),
                    'assignment_id': row.id,
                    'days_of_week': days,
                    'day_labels': [DAY_SHORT[d] for d in days if 0 <= d < len(DAY_SHORT)],
                }
            )
            assigned_ids.add(class_obj.id)
        assignments_by_period[period.id] = cards

    period_rows = []
    for period in periods:
        period_rows.append(
            {
                **serialize_period(period),
                'assigned_classes': assignments_by_period.get(period.id, []),
            }
        )

    return {
        'bell_schedule': serialize_bell_schedule(schedule),
        'grade_level': grade_level,
        'grade_label': grade_label(grade_level),
        'periods': period_rows,
        'classes': [_serialize_class_planner_card(c) for c in classes],
        'unassigned_classes': [
            _serialize_class_planner_card(c) for c in classes if c.id not in assigned_ids
        ],
    }

