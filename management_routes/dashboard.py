"""
Dashboard routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import management_required
from .utils import update_assignment_statuses, get_current_quarter, calculate_student_gpa
from models import (
    db, Class, Assignment, Student, Grade, Submission, 
    Notification, TeacherStaff, SchoolYear, Enrollment, User
)
from sqlalchemy import or_, and_
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
        
        # Calculate last month's start date
        if month_start.month == 1:
            last_month_start = datetime(month_start.year - 1, 12, 1)
        else:
            last_month_start = datetime(month_start.year, month_start.month - 1, 1)
        
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        
        # Calculate month-over-month changes
        # Students: Use User model's created_at where student_id is not None
        students_this_month = User.query.filter(
            User.student_id.isnot(None),
            User.created_at >= month_start
        ).count()
        
        students_last_month = User.query.filter(
            User.student_id.isnot(None),
            User.created_at >= last_month_start,
            User.created_at < month_start
        ).count()
        
        # Calculate percentage change for students
        if students_last_month > 0:
            students_change_percent = round(((students_this_month - students_last_month) / students_last_month) * 100, 1)
        else:
            students_change_percent = 100.0 if students_this_month > 0 else 0.0
        
        # Teachers: Use User model's created_at where teacher_staff_id is not None
        teachers_this_month = User.query.filter(
            User.teacher_staff_id.isnot(None),
            User.created_at >= month_start
        ).count()
        
        teachers_last_month = User.query.filter(
            User.teacher_staff_id.isnot(None),
            User.created_at >= last_month_start,
            User.created_at < month_start
        ).count()
        
        # Calculate percentage change for teachers
        if teachers_last_month > 0:
            teachers_change_percent = round(((teachers_this_month - teachers_last_month) / teachers_last_month) * 100, 1)
        else:
            teachers_change_percent = 100.0 if teachers_this_month > 0 else 0.0
        
        # Classes: Use Class model's created_at
        classes_this_month = Class.query.filter(
            Class.created_at >= month_start
        ).count()
        
        classes_last_month = Class.query.filter(
            Class.created_at >= last_month_start,
            Class.created_at < month_start
        ).count()
        
        # Calculate percentage change for classes
        if classes_last_month > 0:
            classes_change_percent = round(((classes_this_month - classes_last_month) / classes_last_month) * 100, 1)
        else:
            classes_change_percent = 100.0 if classes_this_month > 0 else 0.0
        
        # Active Assignments: Use Assignment model's created_at for Active status
        active_assignments_this_month = Assignment.query.filter(
            Assignment.status == 'Active',
            Assignment.created_at >= month_start
        ).count()
        
        active_assignments_last_month = Assignment.query.filter(
            Assignment.status == 'Active',
            Assignment.created_at >= last_month_start,
            Assignment.created_at < month_start
        ).count()
        
        # Calculate percentage change for active assignments
        if active_assignments_last_month > 0:
            assignments_change_percent = round(((active_assignments_this_month - active_assignments_last_month) / active_assignments_last_month) * 100, 1)
        else:
            assignments_change_percent = 100.0 if active_assignments_this_month > 0 else 0.0
        
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
            'students': total_students,
            'teachers': total_teachers,
            'classes': total_classes,
            'assignments': active_assignments,  # Show active assignments count
            'total_assignments': total_assignments,
            'active_assignments': active_assignments,
            'due_assignments': due_assignments,
            'grades_entered': grades_this_month,
            'students_change_percent': students_change_percent,
            'teachers_change_percent': teachers_change_percent,
            'classes_change_percent': classes_change_percent,
            'assignments_change_percent': assignments_change_percent
        }
        
        # --- AT-RISK STUDENT ALERTS ---
        at_risk_alerts = []  # Initialize here to ensure it's always defined
        try:
            students_to_check = Student.query.all() # Management sees all students
            student_ids = [s.id for s in students_to_check]

            at_risk_grades = db.session.query(Grade).join(Assignment).join(Student)\
                .filter(Student.id.in_(student_ids))\
                .filter(Assignment.due_date < datetime.utcnow()) \
                .all()

            seen_student_ids = set()
            for grade in at_risk_grades:
                try:
                    grade_data = json.loads(grade.grade_data)
                    score = grade_data.get('score')
                    if score is None or score <= 69:
                        if grade.student.id not in seen_student_ids:
                            # Determine alert reason
                            if score is None:
                                alert_reason = 'Missing'
                            elif score <= 69:
                                alert_reason = 'Overdue And Failing'
                            else:
                                alert_reason = 'At Risk'
                            
                            at_risk_alerts.append({
                                'student_name': f"{grade.student.first_name} {grade.student.last_name}",
                                'student_user_id': grade.student.id,  # This is the student ID
                                'class_name': grade.assignment.class_info.name,
                                'assignment_name': grade.assignment.title,
                                'alert_reason': alert_reason
                            })
                            seen_student_ids.add(grade.student.id)
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error processing grade {grade.id}: {e}")
                    continue
        except Exception as e:
            print(f"Error in alert processing: {e}")
            at_risk_alerts = []  # Ensure it's still a list even if there's an error
        # --- END ALERTS ---
        
        # --- Debugging Print Statements ---
        print(f"--- Debug Dashboard Alerts ---")
        print(f"Checking alerts for user: {current_user.username}, Role: {current_user.role}")
        print(f"Raw at-risk grades query result count: {len(at_risk_grades)}")
        print(f"Number of at-risk alerts created: {len(at_risk_alerts)}")
        if at_risk_alerts:
            print(f"First alert sample: {at_risk_alerts[0]}")
        print(f"--- End Debug ---")
        # --- End Debugging ---
        
        return render_template('management/role_dashboard.html', 
                             classes=classes,
                             students=students,
                             teachers=teachers,
                             recent_assignments=recent_assignments,
                             recent_activity=recent_activity,
                             notifications=notifications,
                             stats=stats,
                             section='dashboard',
                             active_tab='dashboard',
                             at_risk_alerts=at_risk_alerts)
        
    except Exception as e:
        print(f"Error in management dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return render_template('management/role_dashboard.html', 
                             classes=[], 
                             students=[],
                             teachers=[], 
                             recent_assignments=[], 
                             recent_activity=[], 
                             notifications=[], 
                             stats={},
                             section='dashboard',
                             active_tab='dashboard',
                             at_risk_alerts=[])  # Always pass at_risk_alerts as empty list



