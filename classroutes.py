# Core Flask imports
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user

# Database and model imports
from models import (
    db, Class, TeacherStaff, Student, StudentGroup, StudentGroupMember,
    GroupAssignment, DeadlineReminder, Feedback360, ReflectionJournal,
    GroupConflict, SchoolYear, AcademicPeriod
)

# Authentication
from decorators import teacher_required
from datetime import datetime

# Create blueprint
class_blueprint = Blueprint('class', __name__, url_prefix='/class')

def get_teacher_or_admin():
    """Helper function to get teacher object or None for administrators."""
    if current_user.role in ['Director', 'School Administrator']:
        return None
    elif hasattr(current_user, 'teacher_staff_id') and current_user.teacher_staff_id:
        return TeacherStaff.query.get(current_user.teacher_staff_id)
    return None

def is_admin():
    """Check if current user is an administrator"""
    return current_user.role in ['Director', 'School Administrator']


@class_blueprint.route('/<int:class_id>/group-assignments')
@login_required
@teacher_required
def class_group_assignments(class_id):
    """View all group assignments for a specific class - Universal route for all roles."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true' or is_admin()
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all group assignments for this class
    try:
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).order_by(GroupAssignment.due_date.desc()).all()
    except Exception as e:
        flash('Group assignments feature is not yet available. Please run the database migration first.', 'warning')
        group_assignments = []
    
    return render_template('shared/class_group_assignments.html',
                         class_obj=class_obj,
                         group_assignments=group_assignments,
                         moment=datetime.utcnow(),
                         admin_view=admin_view)


@class_blueprint.route('/<int:class_id>/deadline-reminders')
@login_required
@teacher_required
def class_deadline_reminders(class_id):
    """View deadline reminders for a specific class - Universal route for all roles."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true' or is_admin()
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all deadline reminders for this class
    try:
        from datetime import timedelta
        reminders = DeadlineReminder.query.filter_by(class_id=class_id).order_by(DeadlineReminder.reminder_date.asc()).all()
        
        # Get upcoming reminders (next 7 days)
        now = datetime.now()
        upcoming_date = now + timedelta(days=7)
        upcoming_reminders = [r for r in reminders if r.reminder_date and now <= r.reminder_date <= upcoming_date]
    except Exception as e:
        flash('Deadline reminders feature is not yet available.', 'warning')
        reminders = []
        upcoming_reminders = []
    
    return render_template('shared/class_deadline_reminders.html',
                         class_obj=class_obj,
                         reminders=reminders,
                         upcoming_reminders=upcoming_reminders,
                         admin_view=admin_view)


@class_blueprint.route('/<int:class_id>/analytics')
@login_required
@teacher_required
def class_analytics(class_id):
    """View analytics for a specific class - Universal route for all roles."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true' or is_admin()
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get analytics data
    try:
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
        collaboration_metrics = []
        benchmarks = []
    except Exception as e:
        groups = []
        group_assignments = []
        collaboration_metrics = []
        benchmarks = []
    
    return render_template('shared/class_analytics.html',
                         class_obj=class_obj,
                         groups=groups,
                         group_assignments=group_assignments,
                         collaboration_metrics=collaboration_metrics,
                         benchmarks=benchmarks,
                         admin_view=admin_view)


@class_blueprint.route('/<int:class_id>/360-feedback')
@login_required
@teacher_required
def class_360_feedback(class_id):
    """View 360 feedback for a specific class - Universal route for all roles."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true' or is_admin()
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get feedback sessions
    try:
        feedback_sessions = Feedback360.query.filter_by(class_id=class_id).order_by(Feedback360.created_at.desc()).all()
    except Exception as e:
        feedback_sessions = []
    
    return render_template('shared/class_360_feedback.html',
                         class_obj=class_obj,
                         feedback_sessions=feedback_sessions,
                         admin_view=admin_view)


@class_blueprint.route('/<int:class_id>/reflection-journals')
@login_required
@teacher_required
def class_reflection_journals(class_id):
    """View reflection journals for a specific class - Universal route for all roles."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true' or is_admin()
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get reflection journals
    try:
        journals = ReflectionJournal.query.filter_by(class_id=class_id).order_by(ReflectionJournal.created_at.desc()).all()
    except Exception as e:
        journals = []
    
    return render_template('shared/class_reflection_journals.html',
                         class_obj=class_obj,
                         journals=journals,
                         admin_view=admin_view)


@class_blueprint.route('/<int:class_id>/conflicts')
@login_required
@teacher_required
def class_conflicts(class_id):
    """View conflicts for a specific class - Universal route for all roles."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true' or is_admin()
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get conflicts
    try:
        conflicts = GroupConflict.query.filter_by(class_id=class_id).order_by(GroupConflict.reported_at.desc()).all()
    except Exception as e:
        conflicts = []
    
    return render_template('shared/class_conflicts.html',
                         class_obj=class_obj,
                         conflicts=conflicts,
                         admin_view=admin_view)

