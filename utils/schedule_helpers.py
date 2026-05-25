"""Build weekly class schedule data for teacher and student schedule pages."""

from __future__ import annotations

from datetime import datetime

from models import ClassSchedule, Enrollment

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def build_weekly_schedule(classes, *, role: str = 'student') -> dict:
    """Return weekly_schedule dict keyed by day_of_week 0–6 (Monday=0)."""
    weekly_schedule = {}
    for day_num in range(7):
        day_schedules = []
        for class_obj in classes:
            schedule = ClassSchedule.query.filter_by(
                class_id=class_obj.id,
                day_of_week=day_num,
            ).first()
            if not schedule:
                continue

            room = schedule.room or 'TBD'
            if role == 'student' and room == 'TBD':
                room = getattr(class_obj, 'room_number', None) or 'TBD'

            item = {
                'class': class_obj,
                'start_time': schedule.start_time,
                'end_time': schedule.end_time,
                'time_str': (
                    f"{schedule.start_time.strftime('%I:%M %p')} – "
                    f"{schedule.end_time.strftime('%I:%M %p')}"
                ),
                'room': room,
            }
            if role == 'teacher':
                item['student_count'] = Enrollment.query.filter_by(
                    class_id=class_obj.id,
                    is_active=True,
                ).count()
            else:
                teacher = getattr(class_obj, 'teacher', None)
                item['teacher_name'] = (
                    f'{teacher.first_name} {teacher.last_name}'.strip()
                    if teacher
                    else 'TBD'
                )
            day_schedules.append(item)

        day_schedules.sort(key=lambda x: x['start_time'])
        weekly_schedule[day_num] = {
            'day_name': DAY_NAMES[day_num],
            'schedules': day_schedules,
        }
    return weekly_schedule


def compute_schedule_insights(weekly_schedule: dict, today_weekday: int) -> dict:
    total_blocks = 0
    active_days = 0
    unique_class_ids = set()
    for day_num, day_data in weekly_schedule.items():
        blocks = day_data.get('schedules') or []
        total_blocks += len(blocks)
        if blocks:
            active_days += 1
        for item in blocks:
            unique_class_ids.add(item['class'].id)
    today_blocks = len((weekly_schedule.get(today_weekday) or {}).get('schedules') or [])
    return {
        'today_blocks': today_blocks,
        'total_blocks': total_blocks,
        'active_days': active_days,
        'unique_classes': len(unique_class_ids),
    }


def mark_schedule_timing(weekly_schedule: dict, today_weekday: int) -> None:
    """Set is_now / is_upcoming on today's blocks for UI highlighting."""
    now = datetime.now().time()
    for day_num, day_data in weekly_schedule.items():
        for item in day_data.get('schedules') or []:
            if day_num != today_weekday:
                item['is_now'] = False
                item['is_upcoming'] = False
                continue
            start = item['start_time']
            end = item['end_time']
            item['is_now'] = start <= now <= end
            item['is_upcoming'] = now < start


def build_schedule_grid(weekly_schedule: dict) -> list:
    """
    Spreadsheet-style grid: one row per unique time block, columns = days (0–6).
    Each cell is a list of schedule items for that day/time.
    """
    slot_map: dict[tuple, dict[int, list]] = {}
    for day_num in range(7):
        day_data = weekly_schedule.get(day_num) or {}
        for item in day_data.get('schedules') or []:
            key = (item['start_time'], item['end_time'])
            if key not in slot_map:
                slot_map[key] = {d: [] for d in range(7)}
            slot_map[key][day_num].append(item)

    rows = []
    for (start, end), cells in sorted(slot_map.items(), key=lambda pair: pair[0][0]):
        rows.append({
            'time_label': (
                f"{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}"
            ),
            'start_time': start,
            'end_time': end,
            'cells': cells,
        })
    return rows


def finalize_schedule_view(weekly_schedule: dict) -> tuple[dict, int, dict, list]:
    today_weekday = datetime.now().weekday()
    insights = compute_schedule_insights(weekly_schedule, today_weekday)
    mark_schedule_timing(weekly_schedule, today_weekday)
    schedule_grid = build_schedule_grid(weekly_schedule)
    return weekly_schedule, today_weekday, insights, schedule_grid
