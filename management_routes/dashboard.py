"""
Dashboard routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import management_required
from .utils import update_assignment_statuses, get_current_quarter, calculate_student_gpa
from models import (
    db, Class, Assignment, Student, Grade, Submission, 
    Notification, TeacherStaff, SchoolYear, Enrollment
)
import json
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
@management_required
def management_dashboard():
    """Main management dashboard with overview and statistics."""
    try:
        # Update assignment statuses before displaying
        update_assignment_statuses()
        
        # Get all classes, students, and teachers for management view
        classes = Class.query.all()
        students = Student.query.all()
        teachers = TeacherStaff.query.all()
        
        # Get recent assignments
        recent_assignments = Assignment.query.order_by(Assignment.due_date.desc()).limit(5).all()
        
        # Get recent submissions
        recent_submissions = Submission.query.order_by(Submission.submitted_at.desc()).limit(5).all()
        
        # Get recent grades
        recent_grades = Grade.query.order_by(Grade.graded_at.desc()).limit(5).all()
        
        # Get notifications for the current user
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.timestamp.desc()).limit(10).all()
        
        # Calculate statistics
        total_students = len(students)
        total_teachers = len(teachers)
        total_classes = len(classes)
        total_assignments = Assignment.query.count()
        active_assignments = Assignment.query.filter_by(status='Active').count()
        
        # Calculate monthly and weekly stats
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        
        # Assignments due this week
        due_assignments = Assignment.query.filter(
            Assignment.due_date >= week_start,
            Assignment.due_date < week_end
        ).count()
        
        # Grades entered this month
        grades_this_month = Grade.query.filter(
            Grade.graded_at >= month_start
        ).count()
        
        # Recent activity
        recent_activity = []
        
        # Add recent submissions to activity
        for submission in recent_submissions:
            recent_activity.append({
                'type': 'submission',
                'title': f'New submission for {submission.assignment.title}',
                'description': f'{submission.student.first_name} {submission.student.last_name} submitted work',
                'timestamp': submission.submitted_at,
                'link': url_for('management.grade_assignment', assignment_id=submission.assignment_id)
            })
        
        # Add recent grades to activity
        for grade in recent_grades:
            try:
                grade_data = json.loads(grade.grade_data)
                recent_activity.append({
                    'type': 'grade',
                    'title': f'Grade entered for {grade.assignment.title}',
                    'description': f'Graded {grade.student.first_name} {grade.student.last_name} - Score: {grade_data.get("score", "N/A")}',
                    'timestamp': grade.graded_at,
                    'link': url_for('management.grade_assignment', assignment_id=grade.assignment_id)
                })
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Add recent assignments to activity
        for assignment in recent_assignments:
            recent_activity.append({
                'type': 'assignment',
                'title': f'New assignment: {assignment.title}',
                'description': f'Created for {assignment.class_info.name} - Due: {assignment.due_date.strftime("%b %d, %Y")}',
                'timestamp': assignment.created_at,
                'link': url_for('management.view_class', class_id=assignment.class_id)
            })
        
        # Sort recent activity by timestamp
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:10]  # Limit to 10 most recent
        
        # Create stats object for template compatibility
        stats = {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_classes': total_classes,
            'total_assignments': total_assignments,
            'active_assignments': active_assignments,
            'due_assignments': due_assignments,
            'grades_entered': grades_this_month
        }
        
        return render_template('role_dashboard.html', 
                             classes=classes,
                             students=students,
                             teachers=teachers,
                             recent_assignments=recent_assignments,
                             recent_activity=recent_activity,
                             notifications=notifications,
                             stats=stats,
                             section='dashboard',
                             active_tab='dashboard')
        
    except Exception as e:
        print(f"Error in management dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return render_template('role_dashboard.html', 
                             classes=[], 
                             students=[],
                             teachers=[],
                             recent_assignments=[], 
                             recent_activity=[], 
                             notifications=[], 
                             stats={},
                             section='dashboard',
                             active_tab='dashboard')



