"""
Dashboard routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required, permissions_required
from models import (
    db, Student, TeacherStaff, Class, Assignment, Grade, Submission, Notification, Enrollment, Attendance, AssignmentRedo, AssignmentReopening,
    User, ExtensionRequest, SchoolYear
)
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import json
from .utils import update_assignment_statuses
from utils.user_roles import user_has_management_entry_access

bp = Blueprint('dashboard', __name__)


def _serialize_feed_timestamp(value):
    if value is None:
        return None
    try:
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return str(value)


def _user_display_name(user) -> str:
    first = (getattr(user, "first_name", None) or "").strip()
    last = (getattr(user, "last_name", None) or "").strip()
    name = f"{first} {last}".strip()
    return name or (getattr(user, "username", None) or "User")


def _user_staff_id(user) -> str:
    ts = getattr(user, "teacher_staff", None)
    if ts and getattr(ts, "staff_id", None):
        return str(ts.staff_id)
    return f"STAFF-{user.id}"


def build_management_home_payload():
    """
    Build management home dashboard data for Jinja or SPA JSON.
    Returns (payload_dict, error_message).
    """
    from utils.user_roles import staff_must_choose_dashboard
    from utils.at_risk_alerts import get_at_risk_alerts_for_user

    try:
        active_school_year = SchoolYear.query.filter_by(is_active=True).first()
        empty_stats = {
            "students": 0,
            "teachers": 0,
            "classes": 0,
            "assignments": 0,
            "active_assignments": 0,
        }
        empty_monthly = {"new_students": 0, "attendance_rate": 0, "average_grade": 0}
        empty_weekly = {"due_assignments": 0}
        now = datetime.now()
        home_display_date = now.strftime("%A, %B %d, %Y")

        latest_school_year_label = None
        years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
        if not active_school_year and years:
            y = years[0]
            latest_school_year_label = y.name + (
                " (Closed)" if not getattr(y, "is_active", False) else ""
            )

        at_risk_count = 0
        try:
            alerts, _, _, _ = get_at_risk_alerts_for_user()
            at_risk_count = len(alerts or [])
        except Exception as e:
            current_app.logger.warning(f"at_risk_alerts for home API: {e}")

        profile = {
            "display_name": _user_display_name(current_user),
            "role": current_user.role,
            "email": getattr(current_user, "email", None),
            "staff_id": _user_staff_id(current_user),
        }

        base = {
            "home_display_date": home_display_date,
            "has_active_school_year": active_school_year is not None,
            "latest_school_year_label": latest_school_year_label,
            "dual_dashboard_staff": bool(staff_must_choose_dashboard(current_user)),
            "profile": profile,
            "at_risk_count": at_risk_count,
            "notification_rows": [],
            "recent_activity": [],
        }

        if not active_school_year:
            return (
                {
                    **base,
                    "stats": empty_stats,
                    "monthly_stats": empty_monthly,
                    "weekly_stats": empty_weekly,
                    "pending_extension_count": 0,
                },
                None,
            )

        year_classes = Class.query.filter_by(school_year_id=active_school_year.id).all()
        stats = {
            "students": Student.query.count(),
            "teachers": TeacherStaff.query.filter(TeacherStaff.is_deleted == False).count(),
            "classes": len(year_classes),
            "assignments": Assignment.query.filter_by(school_year_id=active_school_year.id).count(),
            "active_assignments": Assignment.query.filter(
                Assignment.status == "Active",
                Assignment.school_year_id == active_school_year.id,
            ).count(),
        }

        from utils.school_year_filters import count_pending_extension_requests

        pending_extension_count = count_pending_extension_requests()

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_enrollments = 0
        try:
            if hasattr(Enrollment, "enrolled_at"):
                new_enrollments = Enrollment.query.filter(Enrollment.enrolled_at >= month_start).count()
            else:
                new_enrollments = Enrollment.query.filter(Enrollment.is_active == True).count()
        except Exception as e:
            current_app.logger.warning(f"Error getting new enrollments: {e}")

        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        due_assignments = Assignment.query.filter(
            Assignment.school_year_id == active_school_year.id,
            Assignment.due_date >= week_start,
            Assignment.due_date < week_end,
        ).count()

        try:
            total_attendance_records = Attendance.query.count()
            present_records = Attendance.query.filter_by(status="Present").count()
            attendance_rate = (
                round((present_records / total_attendance_records * 100), 1)
                if total_attendance_records > 0
                else 0
            )
        except Exception as e:
            current_app.logger.warning(f"Error calculating attendance rate: {e}")
            attendance_rate = 0

        grades = Grade.query.all()
        average_grade = 0
        if grades:
            total_score = 0
            valid_grades = 0
            for grade in grades:
                try:
                    grade_data = json.loads(grade.grade_data)
                    if "score" in grade_data and isinstance(grade_data["score"], (int, float)):
                        total_score += grade_data["score"]
                        valid_grades += 1
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            average_grade = round(total_score / valid_grades, 1) if valid_grades > 0 else 0

        monthly_stats = {
            "new_students": new_enrollments,
            "attendance_rate": attendance_rate,
            "average_grade": average_grade,
        }
        weekly_stats = {"due_assignments": due_assignments}

        activity_cutoff = now - timedelta(days=7)
        notification_rows = list(
            Notification.query.filter(
                Notification.user_id == current_user.id,
                Notification.timestamp >= activity_cutoff,
            )
            .order_by(Notification.timestamp.desc())
            .limit(5)
            .all()
        )

        recent_activity = []
        from utils.school_year_filters import extension_requests_query

        for ext in (
            extension_requests_query()
            .filter(
                or_(
                    ExtensionRequest.requested_at >= activity_cutoff,
                    and_(
                        ExtensionRequest.reviewed_at.isnot(None),
                        ExtensionRequest.reviewed_at >= activity_cutoff,
                    ),
                )
            )
            .order_by(ExtensionRequest.requested_at.desc())
            .limit(5)
            .all()
        ):
            try:
                if ext.reviewed_at:
                    recent_activity.append(
                        {
                            "type": "extension_request",
                            "title": f"Extension {ext.status.lower()} for {ext.assignment.title}",
                            "description": f"{ext.student.first_name} {ext.student.last_name} – {ext.status}",
                            "timestamp": ext.reviewed_at,
                            "link": url_for("management.view_extension_requests"),
                        }
                    )
                else:
                    recent_activity.append(
                        {
                            "type": "extension_request",
                            "title": f"New extension request: {ext.assignment.title}",
                            "description": f"{ext.student.first_name} {ext.student.last_name} requested extension",
                            "timestamp": ext.requested_at,
                            "link": url_for("management.view_extension_requests"),
                        }
                    )
            except (AttributeError, TypeError):
                continue

        for grade in (
            Grade.query.join(Assignment)
            .filter(Grade.graded_at >= activity_cutoff)
            .order_by(Grade.graded_at.desc())
            .limit(5)
            .all()
        ):
            try:
                if not grade.assignment or not grade.student:
                    continue
                recent_activity.append(
                    {
                        "type": "grade",
                        "title": f"Grade entered for {grade.assignment.title}",
                        "description": f"{grade.student.first_name} {grade.student.last_name}",
                        "timestamp": grade.graded_at or datetime.utcnow(),
                        "link": url_for("management.grade_assignment", assignment_id=grade.assignment_id),
                    }
                )
            except (AttributeError, TypeError):
                continue

        for sub in (
            Submission.query.join(Assignment)
            .filter(Submission.submitted_at >= activity_cutoff)
            .order_by(Submission.submitted_at.desc())
            .limit(5)
            .all()
        ):
            try:
                if not sub.assignment or not sub.student:
                    continue
                recent_activity.append(
                    {
                        "type": "submission",
                        "title": f"Submission for {sub.assignment.title}",
                        "description": f"{sub.student.first_name} {sub.student.last_name} submitted",
                        "timestamp": sub.submitted_at or datetime.utcnow(),
                        "link": url_for("management.grade_assignment", assignment_id=sub.assignment_id),
                    }
                )
            except (AttributeError, TypeError):
                continue

        for assignment in (
            Assignment.query.filter(Assignment.created_at >= activity_cutoff)
            .order_by(Assignment.created_at.desc())
            .limit(5)
            .all()
        ):
            try:
                class_name = assignment.class_info.name if assignment.class_info else "Unknown"
                recent_activity.append(
                    {
                        "type": "assignment",
                        "title": f"New assignment: {assignment.title}",
                        "description": f"Created for {class_name}",
                        "timestamp": assignment.created_at or datetime.utcnow(),
                        "link": url_for("management.view_assignment", assignment_id=assignment.id),
                    }
                )
            except (AttributeError, TypeError):
                continue

        recent_activity.sort(
            key=lambda x: x.get("timestamp") or datetime.min,
            reverse=True,
        )
        recent_activity = recent_activity[:5]

        return (
            {
                **base,
                "stats": stats,
                "monthly_stats": monthly_stats,
                "weekly_stats": weekly_stats,
                "pending_extension_count": pending_extension_count,
                "notification_rows": notification_rows,
                "recent_activity": recent_activity,
            },
            None,
        )
    except Exception as e:
        current_app.logger.error(f"build_management_home_payload: {e}")
        import traceback

        current_app.logger.error(traceback.format_exc())
        return None, str(e)


# ============================================================
# Route: /dashboard
# Function: management_dashboard
# ============================================================

@bp.route('/dashboard')
@login_required
@permissions_required(
    'students:view', 'students:edit',
    'teachers_staff:manage',
    'classes:manage',
    'assignments_grades:manage',
    'attendance:manage',
    'report_cards:view', 'report_cards:generate',
)
def management_dashboard():
    from flask import current_app, flash
    from utils.spa_management_urls import management_home_redirect_target

    if user_has_management_entry_access(current_user):
        if current_app.config.get("REACT_SPA_ENABLED"):
            return redirect(management_home_redirect_target())

    try:
        payload, error = build_management_home_payload()
        if error:
            flash(f"Error loading dashboard: {error}", "danger")
            payload = {
                "home_display_date": datetime.now().strftime("%A, %B %d, %Y"),
                "stats": {
                    "students": 0,
                    "teachers": 0,
                    "classes": 0,
                    "assignments": 0,
                    "active_assignments": 0,
                },
                "monthly_stats": {},
                "weekly_stats": {},
                "pending_extension_count": 0,
                "notification_rows": [],
                "recent_activity": [],
            }

        return render_template(
            "management/role_dashboard.html",
            stats=payload.get("stats", {}),
            monthly_stats=payload.get("monthly_stats", {}),
            weekly_stats=payload.get("weekly_stats", {}),
            pending_extension_count=payload.get("pending_extension_count", 0),
            home_display_date=payload.get("home_display_date"),
            section="home",
            active_tab="home",
            notifications=payload.get("notification_rows", []),
            recent_activity=payload.get("recent_activity", []),
        )
    except Exception as e:
        current_app.logger.error(f"Error in management_dashboard: {e}")
        import traceback
        error_trace = traceback.format_exc()
        current_app.logger.error(error_trace)
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        # Return minimal dashboard with error
        return render_template('management/role_dashboard.html', 
                             stats={'students': 0, 'teachers': 0, 'classes': 0, 'assignments': 0, 'active_assignments': 0},
                             monthly_stats={},
                             weekly_stats={},
                             pending_extension_count=0,
                             home_display_date=datetime.now().strftime('%A, %B %d, %Y'),
                             section='home',
                             active_tab='home',
                             notifications=[],
                             recent_activity=[])

# Routes for managing students, teachers, classes etc.
# Example: Add Student


# ============================================================
# Route: /redo-dashboard
# Function: redo_dashboard
# ============================================================

@bp.route('/redo-dashboard')
@login_required
def redo_dashboard():
    """Dashboard showing all active redo opportunities, reopenings, and pending redo requests from students"""
    from utils.spa_management_urls import spa_redo_dashboard_redirect

    spa_redirect = spa_redo_dashboard_redirect()
    if spa_redirect is not None:
        return spa_redirect

    from datetime import datetime, timezone
    from teacher_routes.assignment_utils import _as_utc_aware
    from models import Assignment, AssignmentRedo, AssignmentReopening, TeacherStaff, RedoRequest
    from sqlalchemy.orm import joinedload
    from utils.school_year_filters import (
        assignment_redos_query,
        assignment_reopenings_query,
        classes_for_active_school_year,
        get_active_school_year,
        redo_requests_query,
        teacher_class_ids_active_school_year,
    )

    active_school_year = get_active_school_year()
    if not active_school_year:
        return render_template(
            'management/redo_dashboard.html',
            redos=[],
            reopenings=[],
            redo_requests=[],
            classes=[],
            active_redos=0,
            completed_redos=0,
            active_reopenings=0,
            improvement_rate=0,
            overdue_redos=0,
            now=datetime.now(timezone.utc),
        )
    
    # Role/visibility rules:
    # - Teachers: only students/classes they are attached to (primary, additional, or substitute teacher)
    # - School admins: see all classes in the active school year
    is_school_admin = current_user.role in ('Director', 'School Administrator')
    is_teacher_user = (not is_school_admin) and bool(getattr(current_user, 'teacher_staff_id', None))

    teacher = None
    if is_teacher_user:
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        if not teacher:
            flash('Teacher record not found.', 'danger')
            return redirect(url_for('teacher.dashboard.teacher_dashboard'))

        class_ids = teacher_class_ids_active_school_year(teacher.id)
        classes = classes_for_active_school_year(class_ids=class_ids)

        redos = assignment_redos_query(class_ids=class_ids).options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student)
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()

        reopenings = assignment_reopenings_query(class_ids=class_ids).options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student)
        ).order_by(AssignmentReopening.reopened_at.desc()).all()
    else:
        classes = classes_for_active_school_year()
        class_ids = [c.id for c in classes]

        redos = assignment_redos_query().options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student)
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()
        
        reopenings = assignment_reopenings_query().options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student)
        ).order_by(AssignmentReopening.reopened_at.desc()).all()
    
    # Filter out records with missing assignments or students (data integrity check)
    redos = [r for r in redos if r.assignment and r.student]
    reopenings = [r for r in reopenings if r.assignment and r.student]
    
    # Calculate statistics
    active_redos = len([r for r in redos if not r.is_used and not r.final_grade])
    completed_redos = len([r for r in redos if r.final_grade])
    now = datetime.now(timezone.utc)
    for redo in redos:
        redo.is_overdue = bool(
            (not redo.is_used) and
            (not redo.final_grade) and
            redo.redo_deadline and
            (_as_utc_aware(redo.redo_deadline) < now)
        )
    overdue_redos = len([r for r in redos if getattr(r, 'is_overdue', False)])
    active_reopenings = len(reopenings)
    
    # Calculate average improvement
    improvements = []
    for redo in redos:
        if redo.original_grade and redo.final_grade:
            improvement = redo.final_grade - redo.original_grade
            if improvement > 0:
                improvements.append(improvement)
    
    improvement_rate = round(sum(improvements) / len(improvements), 1) if improvements else 0
    
    # Pending redo requests from students (active school year only)
    if is_teacher_user and teacher:
        redo_requests = redo_requests_query(
            class_ids=class_ids, status='Pending'
        ).options(
            joinedload(RedoRequest.assignment).joinedload(Assignment.class_info),
            joinedload(RedoRequest.student)
        ).order_by(RedoRequest.requested_at.desc()).all()
    else:
        redo_requests = redo_requests_query(status='Pending').options(
            joinedload(RedoRequest.assignment).joinedload(Assignment.class_info),
            joinedload(RedoRequest.student)
        ).order_by(RedoRequest.requested_at.desc()).all()
    
    return render_template('management/redo_dashboard.html',
                         redos=redos,
                         reopenings=reopenings,
                         redo_requests=redo_requests,
                         classes=classes,
                         active_redos=active_redos,
                         completed_redos=completed_redos,
                         active_reopenings=active_reopenings,
                         improvement_rate=improvement_rate,
                         overdue_redos=overdue_redos,
                         now=now)


