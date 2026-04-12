"""
Dashboard routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Student, TeacherStaff, Class, Assignment, Grade, Submission, Notification, Enrollment, Attendance, AssignmentRedo, AssignmentReopening,
    User, ExtensionRequest
)
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import json
from .utils import update_assignment_statuses

bp = Blueprint('dashboard', __name__)


# ============================================================
# Route: /dashboard
# Function: management_dashboard
# ============================================================

@bp.route('/dashboard')
@login_required
@management_required
def management_dashboard():
    from datetime import datetime, timedelta
    from sqlalchemy import or_, and_
    import json
    from flask import current_app, flash
    
    try:
        # Basic stats
        stats = {
            'students': Student.query.count(),
            'teachers': TeacherStaff.query.count(),
            'classes': Class.query.count(),
            'assignments': Assignment.query.count()
        }
        
        # Calculate monthly stats
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # New students this month (using ID as proxy since no created_at field)
        # This is a simplified approach - in a real system, you'd want a created_at field
        total_students = Student.query.count()
        # For now, we'll use a placeholder since we can't track creation dates
        # In a real implementation, you'd add a created_at field to the Student model
        new_students = 0
        
        # Alternative: Track new enrollments this month
        # Check if enrolled_at column exists before using it
        new_enrollments = 0
        try:
            # Check if Enrollment model has enrolled_at attribute
            if hasattr(Enrollment, 'enrolled_at'):
                new_enrollments = Enrollment.query.filter(Enrollment.enrolled_at >= month_start).count()
            else:
                # Fallback: count all active enrollments if enrolled_at doesn't exist
                new_enrollments = Enrollment.query.filter(Enrollment.is_active == True).count()
        except Exception as e:
            # Handle any database errors gracefully
            current_app.logger.warning(f"Error getting new enrollments: {e}")
            new_enrollments = 0
    
        # Assignments due this week
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        due_assignments = Assignment.query.filter(
            Assignment.due_date >= week_start,
            Assignment.due_date < week_end
        ).count()
        
        # Calculate attendance rate (simplified)
        try:
            total_attendance_records = Attendance.query.count()
            present_records = Attendance.query.filter_by(status='Present').count()
            attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
        except Exception as e:
            current_app.logger.warning(f"Error calculating attendance rate: {e}")
            attendance_rate = 0
        
        # Calculate average grade (simplified)
        grades = Grade.query.all()
        if grades:
            total_score = 0
            valid_grades = 0
            for grade in grades:
                try:
                    grade_data = json.loads(grade.grade_data)
                    if 'score' in grade_data and isinstance(grade_data['score'], (int, float)):
                        total_score += grade_data['score']
                        valid_grades += 1
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            
            average_grade = round(total_score / valid_grades, 1) if valid_grades > 0 else 0
        else:
            average_grade = 0
        
        monthly_stats = {
            'new_students': new_enrollments,  # Using new enrollments as proxy for new students
            'attendance_rate': attendance_rate,
            'average_grade': average_grade
        }
        
        weekly_stats = {
            'due_assignments': due_assignments
        }
        
        # at_risk_alerts, failing_count, overdue_count: injected by context processor (utils.at_risk_alerts)
        
        # --- Notifications & Recent Activity (only last 7 days, limited count) ---
        activity_cutoff = now - timedelta(days=7)
        notifications = Notification.query.filter(
            Notification.user_id == current_user.id,
            Notification.timestamp >= activity_cutoff
        ).order_by(Notification.timestamp.desc()).limit(5).all()

        recent_activity = []
        # Extension requests (requested or reviewed in last 7 days)
        for ext in ExtensionRequest.query.filter(
            or_(ExtensionRequest.requested_at >= activity_cutoff, and_(ExtensionRequest.reviewed_at.isnot(None), ExtensionRequest.reviewed_at >= activity_cutoff))
        ).order_by(ExtensionRequest.requested_at.desc()).limit(5).all():
            try:
                if ext.reviewed_at:
                    recent_activity.append({
                        'type': 'extension_request',
                        'title': f'Extension {ext.status.lower()} for {ext.assignment.title}',
                        'description': f'{ext.student.first_name} {ext.student.last_name} – {ext.status}',
                        'timestamp': ext.reviewed_at,
                        'link': url_for('management.view_extension_requests')
                    })
                else:
                    recent_activity.append({
                        'type': 'extension_request',
                        'title': f'New extension request: {ext.assignment.title}',
                        'description': f'{ext.student.first_name} {ext.student.last_name} requested extension',
                        'timestamp': ext.requested_at,
                        'link': url_for('management.view_extension_requests')
                    })
            except (AttributeError, TypeError):
                continue
        # Recent grades (school-wide, last 7 days)
        for grade in Grade.query.join(Assignment).filter(Grade.graded_at >= activity_cutoff).order_by(Grade.graded_at.desc()).limit(5).all():
            try:
                if not grade.assignment or not grade.student:
                    continue
                recent_activity.append({
                    'type': 'grade',
                    'title': f'Grade entered for {grade.assignment.title}',
                    'description': f'{grade.student.first_name} {grade.student.last_name}',
                    'timestamp': grade.graded_at or datetime.utcnow(),
                    'link': url_for('management.grade_assignment', assignment_id=grade.assignment_id)
                })
            except (AttributeError, TypeError):
                continue
        # Recent submissions (last 7 days)
        for sub in Submission.query.join(Assignment).filter(Submission.submitted_at >= activity_cutoff).order_by(Submission.submitted_at.desc()).limit(5).all():
            try:
                if not sub.assignment or not sub.student:
                    continue
                recent_activity.append({
                    'type': 'submission',
                    'title': f'Submission for {sub.assignment.title}',
                    'description': f'{sub.student.first_name} {sub.student.last_name} submitted',
                    'timestamp': sub.submitted_at or datetime.utcnow(),
                    'link': url_for('management.grade_assignment', assignment_id=sub.assignment_id)
                })
            except (AttributeError, TypeError):
                continue
        # Recent assignments created (last 7 days)
        for assignment in Assignment.query.filter(Assignment.created_at >= activity_cutoff).order_by(Assignment.created_at.desc()).limit(5).all():
            try:
                class_name = assignment.class_info.name if assignment.class_info else 'Unknown'
                recent_activity.append({
                    'type': 'assignment',
                    'title': f'New assignment: {assignment.title}',
                    'description': f'Created for {class_name}',
                    'timestamp': assignment.created_at or datetime.utcnow(),
                    'link': url_for('management.view_assignment', assignment_id=assignment.id)
                })
            except (AttributeError, TypeError):
                continue
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:5]

        return render_template('management/role_dashboard.html', 
                             stats=stats,
                             monthly_stats=monthly_stats,
                             weekly_stats=weekly_stats,
                             section='home',
                             active_tab='home',
                             notifications=notifications,
                             recent_activity=recent_activity)
    except Exception as e:
        current_app.logger.error(f"Error in management_dashboard: {e}")
        import traceback
        error_trace = traceback.format_exc()
        current_app.logger.error(error_trace)
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        # Return minimal dashboard with error
        return render_template('management/role_dashboard.html', 
                             stats={'students': 0, 'teachers': 0, 'classes': 0, 'assignments': 0},
                             monthly_stats={},
                             weekly_stats={},
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
    from datetime import datetime, timezone
    from teacher_routes.assignment_utils import _as_utc_aware
    from models import AssignmentRedo, AssignmentReopening, Assignment, Class, TeacherStaff, RedoRequest
    from sqlalchemy.orm import joinedload
    
    # Authorization check
    if current_user.role == 'Teacher':
        if not current_user.teacher_staff_id:
            flash('Teacher record not found.', 'danger')
            return redirect(url_for('teacher.dashboard.teacher_dashboard'))
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        # Get redos for teacher's classes only
        redos = AssignmentRedo.query.join(Assignment).join(Class).filter(
            Class.teacher_id == teacher.id
        ).options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student)
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()
        
        # Get reopenings for teacher's classes only
        reopenings = AssignmentReopening.query.join(Assignment).join(Class).filter(
            Class.teacher_id == teacher.id,
            AssignmentReopening.is_active == True
        ).options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student)
        ).order_by(AssignmentReopening.reopened_at.desc()).all()
        
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Directors and School Administrators see all redos and reopenings
        redos = AssignmentRedo.query.options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student)
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()
        
        reopenings = AssignmentReopening.query.filter(
            AssignmentReopening.is_active == True
        ).options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student)
        ).order_by(AssignmentReopening.reopened_at.desc()).all()
        
        classes = Class.query.all()
    
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
    
    # Pending redo requests from students (for inactive assignments)
    if current_user.role == 'Teacher' and teacher:
        class_ids = [c.id for c in classes]
        assignment_ids = Assignment.query.filter(Assignment.class_id.in_(class_ids)).with_entities(Assignment.id).all()
        assignment_ids = [a[0] for a in assignment_ids]
        redo_requests = RedoRequest.query.filter(
            RedoRequest.status == 'Pending',
            RedoRequest.assignment_id.in_(assignment_ids)
        ).options(
            joinedload(RedoRequest.assignment).joinedload(Assignment.class_info),
            joinedload(RedoRequest.student)
        ).order_by(RedoRequest.requested_at.desc()).all()
    else:
        redo_requests = RedoRequest.query.filter(
            RedoRequest.status == 'Pending'
        ).options(
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


