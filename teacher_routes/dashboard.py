"""
Dashboard and overview routes for teachers.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, Student, Grade, Submission, 
    Notification, Announcement, Enrollment, Attendance, SchoolYear
)
import json
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

def update_assignment_statuses():
    """Update assignment statuses based on due dates."""
    try:
        assignments = Assignment.query.all()
        today = datetime.now().date()
        
        for assignment in assignments:
            if assignment.due_date.date() < today and assignment.status == 'Active':
                assignment.status = 'Overdue'
            elif assignment.due_date.date() >= today and assignment.status == 'Overdue':
                assignment.status = 'Active'
        
        db.session.commit()
    except Exception as e:
        print(f"Error updating assignment statuses: {e}")
        db.session.rollback()

@bp.route('/dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    """Main teacher dashboard with overview and recent activity."""
    try:
        # Update assignment statuses before displaying
        update_assignment_statuses()
        
        # Get teacher object or None for administrators
        teacher = get_teacher_or_admin()
        
    except Exception as e:
        print(f"Error in teacher dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return render_template('role_teacher_dashboard.html', 
                             teacher=None, 
                             classes=[], 
                             recent_activity=[], 
                             notifications=[], 
                             teacher_data={}, 
                             monthly_stats={}, 
                             weekly_stats={})
    
    # Directors and School Administrators see all classes, teachers only see their assigned classes
    if is_admin():
        classes = Class.query.all()
        class_ids = [c.id for c in classes]
        recent_assignments = Assignment.query.order_by(Assignment.due_date.desc()).limit(5).all()
        assignments = Assignment.query.all()
    else:
        # Check if teacher object exists
        if teacher is None:
            # If user is a Teacher but has no teacher_staff_id, show empty dashboard
            classes = []
            class_ids = []
            recent_assignments = []
            assignments = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            class_ids = [c.id for c in classes]
            recent_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).order_by(Assignment.due_date.desc()).limit(5).all()
            assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
    
    # Get recent grades (simplified)
    recent_grades = []
    for assignment in assignments[:5]:
        grades = Grade.query.filter_by(assignment_id=assignment.id).limit(3).all()
        for grade in grades:
            try:
                grade_data = json.loads(grade.grade_data)
                recent_grades.append({
                    'assignment': assignment,
                    'student': Student.query.get(grade.student_id),
                    'score': grade_data.get('score', 0)
                })
            except (json.JSONDecodeError, TypeError):
                continue
    
    # Get recent activity for the teacher
    recent_activity = []
    
    # Recent submissions
    recent_submissions = Submission.query.join(Assignment).filter(
        Assignment.class_id.in_(class_ids)
    ).order_by(Submission.submitted_at.desc()).limit(5).all()
    
    for submission in recent_submissions:
        recent_activity.append({
            'type': 'submission',
            'title': f'New submission for {submission.assignment.title}',
            'description': f'{submission.student.first_name} {submission.student.last_name} submitted work',
            'timestamp': submission.submitted_at,
            'link': url_for('teacher.grade_assignment', assignment_id=submission.assignment_id)
        })
    
    # Recent grades entered
    recent_grades_entered = Grade.query.join(Assignment).filter(
        Assignment.class_id.in_(class_ids)
    ).order_by(Grade.graded_at.desc()).limit(5).all()
    
    for grade in recent_grades_entered:
        try:
            grade_data = json.loads(grade.grade_data)
            recent_activity.append({
                'type': 'grade',
                'title': f'Grade entered for {grade.assignment.title}',
                'description': f'Graded {grade.student.first_name} {grade.student.last_name} - Score: {grade_data.get("score", "N/A")}',
                'timestamp': grade.graded_at,
                'link': url_for('teacher.grade_assignment', assignment_id=grade.assignment_id)
            })
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Recent assignments created
    for assignment in recent_assignments:
        recent_activity.append({
            'type': 'assignment',
            'title': f'New assignment: {assignment.title}',
            'description': f'Created for {assignment.class_info.name} - Due: {assignment.due_date.strftime("%b %d, %Y")}',
            'timestamp': assignment.created_at,
            'link': url_for('teacher.view_class', class_id=assignment.class_id)
        })
    
    # Sort recent activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:10]  # Limit to 10 most recent
    
    # Get notifications for the current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).limit(10).all()
    
    # Calculate statistics
    total_students = Student.query.count()  # Simplified - should filter by enrollment
    active_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).count()
    
    # Calculate additional teacher stats
    total_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).count()
    grades_entered = Grade.query.join(Assignment).filter(Assignment.class_id.in_(class_ids)).count()
    
    # Calculate monthly and weekly stats
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    
    # Assignments due this week
    due_assignments = Assignment.query.filter(
        Assignment.class_id.in_(class_ids),
        Assignment.due_date >= week_start,
        Assignment.due_date < week_end
    ).count()
    
    # Grades entered this month
    grades_this_month = Grade.query.join(Assignment).filter(
        Assignment.class_id.in_(class_ids),
        Grade.graded_at >= month_start
    ).count()
    
    # Create teacher_data object for template compatibility
    teacher_data = {
        'classes': classes,
        'total_students': total_students,
        'active_assignments': active_assignments,
        'total_assignments': total_assignments,
        'grades_entered': grades_entered
    }
    
    # Create monthly and weekly stats
    monthly_stats = {
        'grades_entered': grades_this_month
    }
    
    weekly_stats = {
        'due_assignments': due_assignments
    }
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher, 
                         teacher_data=teacher_data,
                         classes=classes,
                         recent_assignments=recent_assignments,
                         recent_grades=recent_grades,
                         recent_activity=recent_activity,
                         notifications=notifications,
                         total_students=total_students,
                         active_assignments=active_assignments,
                         monthly_stats=monthly_stats,
                         weekly_stats=weekly_stats,
                         section='home',
                         active_tab='home',
                         is_admin=is_admin())

@bp.route('/class/<int:class_id>')
@login_required
@teacher_required
def view_class(class_id):
    """View detailed information for a specific class."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to access this class.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get only actively enrolled students for this class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    # Debug logging
    print(f"DEBUG: Class ID: {class_id}")
    print(f"DEBUG: Found {len(enrollments)} enrollments")
    print(f"DEBUG: Enrolled students: {[f'{s.first_name} {s.last_name}' for s in enrolled_students]}")

    # Get recent assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).limit(5).all()

    # Get recent attendance records for this class (last 7 days)
    recent_attendance = Attendance.query.filter(
        Attendance.class_id == class_id,
        Attendance.date >= datetime.now().date() - timedelta(days=7)
    ).order_by(Attendance.date.desc()).all()

    # Get recent announcements for this class
    announcements = Announcement.query.filter_by(class_id=class_id).order_by(Announcement.timestamp.desc()).limit(5).all()

    return render_template(
        'teacher_class_roster_view.html',
        class_item=class_obj,
        enrolled_students=enrolled_students,
        assignments=assignments,
        recent_attendance=recent_attendance,
        announcements=announcements
    )

@bp.route('/classes')
@login_required
@teacher_required
def my_classes():
    """Display all classes for the current teacher."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Directors and School Administrators see all classes, teachers only see their assigned classes
    if is_admin():
        classes = Class.query.all()
    else:
        # Check if teacher object exists
        if teacher is None:
            # If user is a Teacher but has no teacher_staff_id, show empty classes list
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('role_classes.html', classes=classes, teacher=teacher)

@bp.route('/assignments')
@login_required
@teacher_required
def my_assignments():
    """Display all assignments for the current teacher."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Directors and School Administrators see all assignments, teachers only see their assigned classes
    if is_admin():
        assignments = Assignment.query.order_by(Assignment.due_date.desc()).all()
    else:
        # Check if teacher object exists
        if teacher is None:
            # If user is a Teacher but has no teacher_staff_id, show empty assignments list
            assignments = []
        else:
            # Get classes for this teacher
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            class_ids = [c.id for c in classes]
            assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).order_by(Assignment.due_date.desc()).all()
    
    return render_template('teacher_assignments.html', assignments=assignments, teacher=teacher)

@bp.route('/students')
@login_required
@teacher_required
def my_students():
    """Display all students for the current teacher's classes."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Directors and School Administrators see all students, teachers only see students in their classes
    if is_admin():
        students = Student.query.all()
    else:
        # Check if teacher object exists
        if teacher is None:
            # If user is a Teacher but has no teacher_staff_id, show empty students list
            students = []
        else:
            # Get classes for this teacher
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            class_ids = [c.id for c in classes]
            
            # Get students enrolled in these classes
            enrollments = Enrollment.query.filter(
                Enrollment.class_id.in_(class_ids),
                Enrollment.is_active == True
            ).all()
            students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    return render_template('role_students.html', students=students, teacher=teacher)

@bp.route('/teachers-staff')
@login_required
@teacher_required
def teachers_staff():
    """Display all teachers and staff members."""
    teachers = TeacherStaff.query.all()
    return render_template('role_teachers_staff.html', teachers=teachers)

@bp.route('/calendar')
@login_required
@teacher_required
def calendar():
    """Display the calendar view."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Get classes for the current teacher/admin
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Get assignments for calendar display
    class_ids = [c.id for c in classes]
    assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
    
    return render_template('role_calendar.html', 
                         assignments=assignments, 
                         classes=classes, 
                         teacher=teacher)

