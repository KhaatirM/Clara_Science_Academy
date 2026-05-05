"""
Shared utility for computing at-risk student alerts for teachers and administrators.
Handles custom assignment point values (e.g., 25 vs 100) by converting to percentage.
"""

import json
from datetime import datetime

from flask import current_app


def _percentage_from_grade_data(grade_data, assignment_total_points):
    """
    Derive percentage from grade_data, using assignment total_points for correctness.
    grade_data may have: percentage, points_earned, score (legacy).
    assignment_total_points comes from Assignment.total_points or GroupAssignment.total_points.
    Returns (percentage, display_score) or (None, None) if ungraded.
    """
    if not grade_data:
        return None, None
    total_pts = float(assignment_total_points or 100.0)
    # Prefer explicit percentage (already normalized 0-100)
    pct = grade_data.get('percentage')
    if pct is not None:
        try:
            return float(pct), float(pct)
        except (TypeError, ValueError):
            pass
    # Use points_earned / total_points
    pe = grade_data.get('points_earned')
    if pe is not None:
        try:
            pct = (float(pe) / total_pts * 100) if total_pts > 0 else 0
            return pct, pct
        except (TypeError, ValueError):
            pass
    # Legacy: score might be percentage (0-100) or raw points
    score = grade_data.get('score')
    if score is None:
        return None, None
    try:
        score_val = float(score)
    except (TypeError, ValueError):
        return None, None
    # If score looks like percentage (0-100 and total is 100), use it
    if total_pts == 100.0 and 0 <= score_val <= 100:
        return score_val, score_val
    # Otherwise treat as points
    if total_pts > 0 and score_val <= total_pts:
        pct = (score_val / total_pts * 100)
        return pct, pct
    # Score > total? Might be a percentage entered by mistake; cap at 100
    if score_val > 100:
        return min(100, score_val), min(100, score_val)
    return score_val, score_val


def get_at_risk_alerts_for_user():
    """
    Compute at-risk student alerts for the current user (teacher or admin).
    Uses assignment total_points when determining failing (< 70%).
    Returns (at_risk_alerts, failing_count, overdue_count).
    """
    from flask_login import current_user
    from models import (
        db, Student, Grade, Assignment, Enrollment,
        GroupAssignment, GroupGrade, StudentGroup, StudentGroupMember, Class
    )

    at_risk_alerts = []
    if not current_user.is_authenticated:
        return at_risk_alerts, 0, 0

    from utils.user_roles import all_role_strings, user_has_management_entry_access
    from decorators import is_teacher_role

    # Primary role can be Tech with School Administrator in secondary_roles — treat as admin.
    is_admin_user = user_has_management_entry_access(current_user)
    is_teacher = any(is_teacher_role(r) for r in all_role_strings(current_user))
    if not (is_teacher or is_admin_user):
        return at_risk_alerts, 0, 0

    try:
        # Determine student scope
        if is_admin_user:
            student_ids = [s.id for s in Student.query.all()]
            class_ids = None
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
                            db.session.query(class_additional_teachers.c.class_id)
                            .filter(class_additional_teachers.c.teacher_id == teacher.id)
                        ),
                        Class.id.in_(
                            db.session.query(class_substitute_teachers.c.class_id)
                            .filter(class_substitute_teachers.c.teacher_id == teacher.id)
                        )
                    )
                ).all()
                class_ids = [c.id for c in classes]
            else:
                class_ids = []
            if class_ids:
                enrollments = Enrollment.query.filter(
                    Enrollment.class_id.in_(class_ids),
                    Enrollment.is_active == True
                ).all()
                student_ids = list({e.student_id for e in enrollments if e.student_id})
            else:
                student_ids = []

        if not student_ids:
            return at_risk_alerts, 0, 0

        at_risk_grades = db.session.query(Grade).join(Assignment).join(Student).filter(
            Student.id.in_(student_ids),
            Grade.is_voided == False,
            Assignment.status != 'Voided',
        ).all()

        group_assignments = []
        group_grades = []
        if is_admin_user:
            group_assignments = GroupAssignment.query.all()
        elif class_ids:
            group_assignments = GroupAssignment.query.filter(
                GroupAssignment.class_id.in_(class_ids)
            ).all()

        if group_assignments:
            ga_ids = [ga.id for ga in group_assignments]
            groups = []
            if is_admin_user:
                groups = StudentGroup.query.all()
            elif class_ids:
                groups = StudentGroup.query.filter(
                    StudentGroup.class_id.in_(class_ids)
                ).all()
            group_ids = [g.id for g in groups]
            if group_ids and student_ids:
                members = StudentGroupMember.query.filter(
                    StudentGroupMember.group_id.in_(group_ids),
                    StudentGroupMember.student_id.in_(student_ids)
                ).all()
                member_group_ids = {gm.group_id for gm in members}
                group_grades = GroupGrade.query.filter(
                    GroupGrade.group_assignment_id.in_(ga_ids),
                    GroupGrade.is_voided == False,
                ).join(StudentGroup).filter(
                    StudentGroup.id.in_(member_group_ids)
                ).all()

        missing_assignments = []
        if is_admin_user:
            all_assignments = Assignment.query.filter(
                Assignment.status == 'Active',
                Assignment.due_date.isnot(None)
            ).all()
        elif class_ids:
            all_assignments = Assignment.query.filter(
                Assignment.class_id.in_(class_ids),
                Assignment.status == 'Active',
                Assignment.due_date.isnot(None)
            ).all()
        else:
            all_assignments = []

        for assignment in all_assignments:
            if assignment.due_date and assignment.due_date < datetime.utcnow():
                enrollments = Enrollment.query.filter_by(
                    class_id=assignment.class_id,
                    is_active=True
                ).all()
                class_student_ids = [e.student_id for e in enrollments if e.student_id in student_ids]
                for student_id in class_student_ids:
                    if Grade.query.filter_by(
                        student_id=student_id,
                        assignment_id=assignment.id
                    ).first():
                        continue
                    student = Student.query.get(student_id)
                    if student:
                        missing_assignments.append({
                            'student_id': student_id,
                            'student_name': f"{student.first_name} {student.last_name}",
                            'assignment': assignment,
                            'class_name': assignment.class_info.name if assignment.class_info else 'Unknown Class',
                            'assignment_name': assignment.title,
                            'assignment_type': assignment.assignment_type,
                            'due_date': assignment.due_date
                        })

        seen_student_ids = set()
        total_pts_default = 100.0
        from utils.academic_concern_submission import academic_concern_effective_submitted

        for grade in at_risk_grades:
            try:
                if not grade.assignment or not grade.student or not grade.assignment.due_date:
                    continue
                grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else (grade.grade_data or {})
                total_pts = getattr(grade.assignment, 'total_points', None) or total_pts_default
                percentage, display_score = _percentage_from_grade_data(grade_data, total_pts)
                is_overdue = grade.assignment.due_date < datetime.utcnow()
                is_at_risk = False
                alert_reason = None
                if percentage is None and is_overdue:
                    is_at_risk = True
                    alert_reason = "overdue"
                elif percentage is not None and percentage <= 69:
                    is_at_risk = True
                    alert_reason = "overdue and failing" if is_overdue else "failing"
                if is_at_risk and grade.student.id not in seen_student_ids:
                    at_risk_alerts.append({
                        'student_name': f"{grade.student.first_name} {grade.student.last_name}",
                        'student_user_id': grade.student.id,
                        'class_name': grade.assignment.class_info.name if grade.assignment.class_info else 'Unknown Class',
                        'assignment_name': grade.assignment.title,
                        'assignment_type': grade.assignment.assignment_type or 'pdf',
                        'alert_reason': alert_reason,
                        'score': display_score,
                        'due_date': grade.assignment.due_date,
                        'effective_submitted': academic_concern_effective_submitted(
                            grade.student.id, grade.assignment_id, grade
                        ),
                    })
                    seen_student_ids.add(grade.student.id)
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        for group_grade in group_grades:
            try:
                if not group_grade.group_assignment or not group_grade.group:
                    continue
                grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else (group_grade.grade_data or {})
                ga = group_grade.group_assignment
                total_pts = getattr(ga, 'total_points', None) or total_pts_default
                percentage, display_score = _percentage_from_grade_data(grade_data, total_pts)
                is_overdue = ga.due_date < datetime.utcnow() if ga.due_date else False
                is_at_risk = False
                alert_reason = None
                if percentage is None and is_overdue:
                    is_at_risk = True
                    alert_reason = "overdue"
                elif percentage is not None and percentage <= 69:
                    is_at_risk = True
                    alert_reason = "overdue and failing" if is_overdue else "failing"
                if is_at_risk:
                    for member in StudentGroupMember.query.filter_by(group_id=group_grade.group_id).all():
                        if member.student_id not in seen_student_ids:
                            student = Student.query.get(member.student_id)
                            if student:
                                grp_eff_sub = (
                                    isinstance(grade_data, dict)
                                    and grade_data.get('submission_type') in ('online', 'in_person')
                                )
                                at_risk_alerts.append({
                                    'student_name': f"{student.first_name} {student.last_name}",
                                    'student_user_id': student.id,
                                    'class_name': ga.class_info.name if ga.class_info else 'Unknown Class',
                                    'assignment_name': ga.title,
                                    'assignment_type': f"group_{ga.assignment_type}",
                                    'alert_reason': alert_reason,
                                    'score': display_score,
                                    'due_date': ga.due_date,
                                    'effective_submitted': bool(grp_eff_sub),
                                })
                                seen_student_ids.add(student.id)
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        for missing in missing_assignments:
            if missing['student_id'] not in seen_student_ids:
                at_risk_alerts.append({
                    'student_name': missing['student_name'],
                    'student_user_id': missing['student_id'],
                    'class_name': missing['class_name'],
                    'assignment_name': missing['assignment_name'],
                    'assignment_type': missing['assignment_type'],
                    'alert_reason': 'overdue',
                    'score': None,
                    'due_date': missing['due_date'],
                    'effective_submitted': False,
                })
                seen_student_ids.add(missing['student_id'])

        failing_count = sum(1 for a in at_risk_alerts if 'failing' in (a.get('alert_reason') or '').lower())
        overdue_count = sum(1 for a in at_risk_alerts if 'overdue' in (a.get('alert_reason') or '').lower())
        return at_risk_alerts, failing_count, overdue_count

    except Exception as e:
        current_app.logger.warning(f"Error computing at_risk_alerts: {e}")
        return [], 0, 0
