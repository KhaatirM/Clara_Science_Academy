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
                            at_risk_alerts.append({
                                'student_name': f"{grade.student.first_name} {grade.student.last_name}",
                                'student_user_id': grade.student.id,  # Use student ID instead of user_id
                                'class_name': grade.assignment.class_info.name,
                                'assignment_name': grade.assignment.title
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
        # print(f"Students being checked IDs: {[s.id for s in students_to_check]}") # Optional: If you need to see specific IDs
        print(f"Raw at-risk grades query result count: {len(at_risk_grades)}")
        print(f"Formatted alerts list being sent to template: {at_risk_alerts}")
        print(f"--- End Debug ---")
        # --- End Debugging ---
        
        # TEMPORARY: Force test alerts to verify template is working
        if not at_risk_alerts:
            print("FORCING TEST ALERTS FOR DEBUGGING")
            at_risk_alerts = [
                {
                    'student_name': 'Test Student 1',
                    'student_user_id': 1,
                    'class_name': 'Test Class',
                    'assignment_name': 'Test Assignment'
                },
                {
                    'student_name': 'Test Student 2', 
                    'student_user_id': 2,
                    'class_name': 'Test Class 2',
                    'assignment_name': 'Test Assignment 2'
                }
            ]
        
        return render_template('role_dashboard.html', 
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
        return render_template('role_dashboard.html', 
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



