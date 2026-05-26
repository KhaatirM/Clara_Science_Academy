"""
Academic concerns for teachers and school administrators.

Eligibility: active-roster students with GPA strictly below 2.00
- Administrators: overall GPA (all graded assignments)
- Teachers: GPA from the viewer's classes only

The modal lists one card per student; assignment details load via API.
"""

import json
import threading
import time
from datetime import datetime

from flask import current_app

# Show academic concerns only when GPA is below this value (not equal).
ACADEMIC_CONCERN_GPA_THRESHOLD = 2.0

# Per-user TTL cache. The unscoped computation is O(students * assignments) and runs
# on every page render via a context processor, so without caching every teacher/admin
# request fans out into 1k+ queries. 5 min is short enough that fresh grades show up
# quickly; callers that mutate grades can use invalidate_at_risk_alerts_cache(user_id).
_ALERTS_CACHE_TTL_SECONDS = 300
_alerts_cache_lock = threading.Lock()
_alerts_cache = {}  # user_id -> (expires_at_epoch, payload_tuple)


def invalidate_at_risk_alerts_cache(user_id=None):
    """Drop a single user's cached at-risk alerts, or the whole cache if user_id is None."""
    with _alerts_cache_lock:
        if user_id is None:
            _alerts_cache.clear()
        else:
            _alerts_cache.pop(user_id, None)


def _percentage_from_grade_data(grade_data, assignment_total_points):
    """Derive percentage from grade_data using assignment total_points."""
    if not grade_data:
        return None, None
    total_pts = float(assignment_total_points or 100.0)
    pct = grade_data.get('percentage')
    if pct is not None:
        try:
            return float(pct), float(pct)
        except (TypeError, ValueError):
            pass
    pe = grade_data.get('points_earned')
    if pe is not None:
        try:
            pct = (float(pe) / total_pts * 100) if total_pts > 0 else 0
            return pct, pct
        except (TypeError, ValueError):
            pass
    score = grade_data.get('score')
    if score is None:
        return None, None
    try:
        score_val = float(score)
    except (TypeError, ValueError):
        return None, None
    if total_pts == 100.0 and 0 <= score_val <= 100:
        return score_val, score_val
    if total_pts > 0 and score_val <= total_pts:
        pct = (score_val / total_pts * 100)
        return pct, pct
    if score_val > 100:
        return min(100, score_val), min(100, score_val)
    return score_val, score_val


def _grades_for_gpa(student_id, class_ids=None):
    """Non-voided grades used for GPA (optionally limited to class_ids)."""
    from models import Grade, Assignment

    q = (
        Grade.query.join(Assignment)
        .filter(
            Grade.student_id == student_id,
            Grade.is_voided.is_(False),
            Assignment.status != 'Voided',
        )
    )
    if class_ids is not None:
        q = q.filter(Assignment.class_id.in_(class_ids))
    return q.all()


def _compute_scoped_gpa(student_id, class_ids=None):
    from gpa_scheduler import calculate_student_gpa

    grades = _grades_for_gpa(student_id, class_ids)
    if not grades:
        return None
    return calculate_student_gpa(grades)


def _assignment_type_label(raw_type):
    if not raw_type:
        return ''
    t = str(raw_type).lower()
    if t.startswith('group_'):
        t = t.replace('group_', '', 1)
    labels = {
        'pdf': 'PDF',
        'quiz': 'Quiz',
        'discussion': 'Discussion',
        'paper': 'Paper',
    }
    return labels.get(t, t.replace('_', ' ').title())


def _count_assignment_issues(student_id, class_ids, is_admin_user):
    """
    Count failing / overdue assignments in scope for summary chips.
    Returns (failing_count, overdue_count, classes_with_issues set).
    """
    from models import (
        db,
        Grade,
        Assignment,
        Enrollment,
        GroupAssignment,
        GroupGrade,
        StudentGroup,
        StudentGroupMember,
    )

    failing = 0
    overdue = 0
    classes_with_issues = set()
    total_pts_default = 100.0
    now = datetime.utcnow()

    grade_q = (
        db.session.query(Grade)
        .join(Assignment)
        .filter(
            Grade.student_id == student_id,
            Grade.is_voided.is_(False),
            Assignment.status != 'Voided',
            Assignment.due_date.isnot(None),
        )
    )
    if class_ids is not None:
        grade_q = grade_q.filter(Assignment.class_id.in_(class_ids))
    for grade in grade_q.all():
        if not grade.assignment:
            continue
        try:
            grade_data = (
                json.loads(grade.grade_data)
                if isinstance(grade.grade_data, str)
                else (grade.grade_data or {})
            )
        except (json.JSONDecodeError, TypeError):
            grade_data = {}
        total_pts = getattr(grade.assignment, 'total_points', None) or total_pts_default
        percentage, _ = _percentage_from_grade_data(grade_data, total_pts)
        is_past_due = grade.assignment.due_date < now
        class_name = (
            grade.assignment.class_info.name
            if grade.assignment.class_info
            else None
        )
        if percentage is None and is_past_due:
            overdue += 1
            if class_name:
                classes_with_issues.add(class_name)
        elif percentage is not None and percentage <= 69:
            # A graded assignment is not "past due" anymore even when its due
            # date is in the past; it's just failing. Past-due is reserved for
            # the no-grade case so badges don't double-count the same item.
            failing += 1
            if class_name:
                classes_with_issues.add(class_name)

    if is_admin_user:
        ga_list = GroupAssignment.query.filter(GroupAssignment.status != 'Voided').all()
    elif class_ids:
        ga_list = GroupAssignment.query.filter(
            GroupAssignment.class_id.in_(class_ids),
            GroupAssignment.status != 'Voided',
        ).all()
    else:
        ga_list = []

    if ga_list:
        ga_ids = [ga.id for ga in ga_list]
        member_rows = StudentGroupMember.query.join(StudentGroup).filter(
            StudentGroupMember.student_id == student_id,
            StudentGroup.class_id.in_([ga.class_id for ga in ga_list]),
        ).all()
        member_group_ids = {m.group_id for m in member_rows}
        if member_group_ids:
            for gg in GroupGrade.query.filter(
                GroupGrade.group_assignment_id.in_(ga_ids),
                GroupGrade.is_voided.is_(False),
            ).all():
                if gg.group_id not in member_group_ids:
                    continue
                ga = gg.group_assignment
                if not ga or not ga.due_date:
                    continue
                try:
                    grade_data = (
                        json.loads(gg.grade_data)
                        if isinstance(gg.grade_data, str)
                        else (gg.grade_data or {})
                    )
                except (json.JSONDecodeError, TypeError):
                    grade_data = {}
                total_pts = getattr(ga, 'total_points', None) or total_pts_default
                percentage, _ = _percentage_from_grade_data(grade_data, total_pts)
                is_past_due = ga.due_date < now
                class_name = ga.class_info.name if ga.class_info else None
                if percentage is None and is_past_due:
                    overdue += 1
                    if class_name:
                        classes_with_issues.add(class_name)
                elif percentage is not None and percentage <= 69:
                    # Failing-and-graded should not also count as past-due.
                    failing += 1
                    if class_name:
                        classes_with_issues.add(class_name)

    assign_q = Assignment.query.filter(
        Assignment.status == 'Active',
        Assignment.due_date.isnot(None),
        Assignment.due_date < now,
    )
    if class_ids is not None:
        assign_q = assign_q.filter(Assignment.class_id.in_(class_ids))
    for assignment in assign_q.all():
        enrolled = Enrollment.query.filter_by(
            student_id=student_id,
            class_id=assignment.class_id,
            is_active=True,
        ).first()
        if not enrolled:
            continue
        if Grade.query.filter_by(
            student_id=student_id, assignment_id=assignment.id
        ).first():
            continue
        overdue += 1
        if assignment.class_info:
            classes_with_issues.add(assignment.class_info.name)

    return failing, overdue, classes_with_issues


def get_at_risk_alerts_for_user():
    """
    Students with GPA below ACADEMIC_CONCERN_GPA_THRESHOLD (scoped by role).

    Returns (student_concerns, failing_assignment_count, overdue_assignment_count).
    Each concern dict is one row per student (not per assignment).

    Cached per-user for _ALERTS_CACHE_TTL_SECONDS to keep page renders fast.
    """
    from flask_login import current_user
    from models import db, Class
    from utils.student_roster import (
        active_roster_student_ids,
        filter_student_ids_on_roster,
    )

    empty = ([], 0, 0)
    if not current_user.is_authenticated:
        return empty

    from utils.user_roles import all_role_strings, user_has_management_entry_access
    from decorators import is_teacher_role

    is_admin_user = user_has_management_entry_access(current_user)
    is_teacher = any(is_teacher_role(r) for r in all_role_strings(current_user))
    if not (is_teacher or is_admin_user):
        return empty

    # Per-user short TTL cache: the underlying queries are heavy and this runs on
    # every authenticated page render via inject_at_risk_alerts (context processor).
    cache_key = getattr(current_user, 'id', None)
    if cache_key is not None:
        now_ts = time.time()
        with _alerts_cache_lock:
            entry = _alerts_cache.get(cache_key)
            if entry and entry[0] > now_ts:
                return entry[1]

    try:
        class_ids = None
        if is_admin_user:
            student_ids = active_roster_student_ids(require_active_enrollment=True)
        else:
            from teacher_routes.utils import get_teacher_or_admin
            from sqlalchemy import or_
            from models import class_additional_teachers, class_substitute_teachers

            teacher = get_teacher_or_admin()
            if teacher:
                classes = Class.query.filter(
                    or_(
                        Class.teacher_id == teacher.id,
                        Class.id.in_(
                            db.session.query(class_additional_teachers.c.class_id).filter(
                                class_additional_teachers.c.teacher_id == teacher.id
                            )
                        ),
                        Class.id.in_(
                            db.session.query(class_substitute_teachers.c.class_id).filter(
                                class_substitute_teachers.c.teacher_id == teacher.id
                            )
                        ),
                    )
                ).all()
                class_ids = [c.id for c in classes]
            else:
                class_ids = []
            if class_ids:
                from models import Enrollment

                enrollments = Enrollment.query.filter(
                    Enrollment.class_id.in_(class_ids),
                    Enrollment.is_active.is_(True),
                ).all()
                student_ids = list({e.student_id for e in enrollments if e.student_id})
                student_ids = filter_student_ids_on_roster(
                    student_ids, require_active_enrollment=True
                )
            else:
                student_ids = []

        if not student_ids:
            return empty

        gpa_class_ids = None if is_admin_user else class_ids
        concerns = []
        total_failing = 0
        total_overdue = 0

        from models import Student, Enrollment

        for sid in student_ids:
            student = Student.query.get(sid)
            if not student:
                continue

            gpa = _compute_scoped_gpa(sid, gpa_class_ids)
            if gpa is None or gpa >= ACADEMIC_CONCERN_GPA_THRESHOLD:
                continue

            fail_n, od_n, classes_set = _count_assignment_issues(
                sid, gpa_class_ids, is_admin_user
            )
            total_failing += fail_n
            total_overdue += od_n

            if gpa_class_ids is None:
                enrollments = Enrollment.query.filter_by(
                    student_id=sid, is_active=True
                ).all()
            else:
                enrollments = Enrollment.query.filter(
                    Enrollment.student_id == sid,
                    Enrollment.class_id.in_(gpa_class_ids),
                    Enrollment.is_active.is_(True),
                ).all()
            enrolled_names = []
            for e in enrollments:
                if e.class_info and e.class_info.name:
                    enrolled_names.append(e.class_info.name)
            enrolled_names = sorted(set(enrolled_names))

            if classes_set:
                classes_label = ', '.join(sorted(classes_set))
            elif enrolled_names:
                classes_label = ', '.join(enrolled_names)
            else:
                classes_label = ''

            issues_total = fail_n + od_n
            concerns.append(
                {
                    'student_name': f'{student.first_name} {student.last_name}',
                    'student_user_id': sid,
                    'current_gpa': gpa,
                    'grade_level': student.grade_level,
                    'class_count': len(enrolled_names) or len(classes_set),
                    'classes_label': classes_label,
                    'enrolled_class_names': enrolled_names,
                    'failing_count': fail_n,
                    'overdue_count': od_n,
                    'issues_total': issues_total,
                    'alert_reason': 'critical',
                }
            )

        concerns.sort(key=lambda c: (c['current_gpa'], c['student_name'].lower()))
        result = (concerns, total_failing, total_overdue)
        if cache_key is not None:
            with _alerts_cache_lock:
                _alerts_cache[cache_key] = (
                    time.time() + _ALERTS_CACHE_TTL_SECONDS,
                    result,
                )
        return result

    except Exception as e:
        current_app.logger.warning('Error computing at_risk_alerts: %s', e)
        return empty
