"""
Dashboard and overview routes for teachers.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, Student, Grade, Submission, 
    Notification, Announcement, Enrollment, Attendance, SchoolYear, User, TeacherStaff,
    class_additional_teachers, class_substitute_teachers, GroupAssignment, GroupGrade, ClassSchedule
)
from sqlalchemy import or_, and_
import json
import calendar as cal
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))
from google_classroom_service import get_google_service
from googleapiclient.errors import HttpError

bp = Blueprint('dashboard', __name__)

def update_assignment_statuses():
    """Update assignment statuses based on due dates."""
    try:
        assignments = Assignment.query.all()
        today = datetime.now().date()
        
        for assignment in assignments:
            # Check if due_date exists and is not None
            if assignment.due_date:
                try:
                    # Handle both datetime and date objects
                    due_date = assignment.due_date.date() if hasattr(assignment.due_date, 'date') else assignment.due_date
                    if due_date < today and assignment.status == 'Active':
                        assignment.status = 'Overdue'
                    elif due_date >= today and assignment.status == 'Overdue':
                        assignment.status = 'Active'
                except (AttributeError, TypeError) as e:
                    # Skip assignments with invalid due_date
                    print(f"Error updating assignment {assignment.id}: {e}")
                    continue
        
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
        return render_template('management/role_teacher_dashboard.html', 
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
    if class_ids:
        recent_submissions = Submission.query.join(Assignment).filter(
            Assignment.class_id.in_(class_ids)
        ).order_by(Submission.submitted_at.desc()).limit(5).all()
    else:
        recent_submissions = []
    
    for submission in recent_submissions:
        try:
            # Check if submission has required relationships
            if not submission.assignment or not submission.student:
                continue
                
            recent_activity.append({
                'type': 'submission',
                'title': f'New submission for {submission.assignment.title}',
                'description': f'{submission.student.first_name} {submission.student.last_name} submitted work',
                'timestamp': submission.submitted_at or datetime.utcnow(),
                'link': url_for('teacher.grading.grade_assignment', assignment_id=submission.assignment_id)
            })
        except (AttributeError, TypeError) as e:
            print(f"Error processing submission {submission.id}: {e}")
            continue
    
    # Recent grades entered
    if class_ids:
        recent_grades_entered = Grade.query.join(Assignment).filter(
            Assignment.class_id.in_(class_ids)
        ).order_by(Grade.graded_at.desc()).limit(5).all()
    else:
        recent_grades_entered = []
    
    for grade in recent_grades_entered:
        try:
            # Check if grade has required relationships
            if not grade.assignment or not grade.student:
                continue
                
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            recent_activity.append({
                'type': 'grade',
                'title': f'Grade entered for {grade.assignment.title}',
                'description': f'Graded {grade.student.first_name} {grade.student.last_name} - Score: {grade_data.get("score", "N/A") if isinstance(grade_data, dict) else "N/A"}',
                'timestamp': grade.graded_at or datetime.utcnow(),
                'link': url_for('teacher.grading.grade_assignment', assignment_id=grade.assignment_id)
            })
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            print(f"Error processing grade {grade.id}: {e}")
            continue
    
    # Recent assignments created
    for assignment in recent_assignments:
        try:
            # Check if assignment has required relationships
            if not assignment.class_info:
                continue
                
            due_date_str = assignment.due_date.strftime("%b %d, %Y") if assignment.due_date else "No due date"
            recent_activity.append({
                'type': 'assignment',
                'title': f'New assignment: {assignment.title}',
                'description': f'Created for {assignment.class_info.name} - Due: {due_date_str}',
                'timestamp': assignment.created_at or datetime.utcnow(),
                'link': url_for('teacher.dashboard.view_class', class_id=assignment.class_id)
            })
        except (AttributeError, TypeError) as e:
            print(f"Error processing assignment {assignment.id}: {e}")
            continue
    
    # Sort recent activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:10]  # Limit to 10 most recent
    
    # Get notifications for the current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).limit(10).all()
    
    # Calculate statistics
    total_students = Student.query.count()  # Simplified - should filter by enrollment
    if class_ids:
        active_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).count()
        total_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).count()
        grades_entered = Grade.query.join(Assignment).filter(Assignment.class_id.in_(class_ids)).count()
    else:
        active_assignments = 0
        total_assignments = 0
        grades_entered = 0
    
    # Calculate monthly and weekly stats
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    
    # Assignments due this week - safely handle None due_date
    try:
        if class_ids:
            due_assignments = Assignment.query.filter(
                Assignment.class_id.in_(class_ids),
                Assignment.due_date.isnot(None),
                Assignment.due_date >= week_start,
                Assignment.due_date < week_end
            ).count()
        else:
            due_assignments = 0
    except Exception as e:
        print(f"Error counting due assignments: {e}")
        due_assignments = 0
    
    # Grades entered this month
    if class_ids:
        grades_this_month = Grade.query.join(Assignment).filter(
            Assignment.class_id.in_(class_ids),
            Grade.graded_at >= month_start
        ).count()
    else:
        grades_this_month = 0
    
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
    
    # --- AT-RISK STUDENT ALERTS ---
    at_risk_alerts = []
    
    # Get students through teacher's classes
    if is_admin():
        # Admins see all students
        student_ids = [s.id for s in Student.query.all()]
    elif class_ids:
        # Get students enrolled in teacher's classes
        from models import Enrollment
        enrollments = Enrollment.query.filter(
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active == True
        ).all()
        student_ids = [e.student_id for e in enrollments]
    else:
        # No classes, no students to check
        student_ids = []
    
    if student_ids:
        # Get ALL non-voided grades for our students (not just overdue ones)
        at_risk_grades = db.session.query(Grade).join(Assignment).join(Student)\
            .filter(Student.id.in_(student_ids))\
            .filter(Grade.is_voided == False)\
            .all()
    else:
        at_risk_grades = []

    seen_student_ids = set()
    for grade in at_risk_grades:
        try:
            grade_data = json.loads(grade.grade_data)
            score = grade_data.get('score')
            is_overdue = grade.assignment.due_date < datetime.utcnow()
            
            # Only alert for truly at-risk: missing (overdue with no score) OR failing (score <= 69)
            # Don't include passing overdue assignments (70+) - they're not at-risk
            is_at_risk = False
            alert_reason = None
            
            if score is None and is_overdue:
                # Missing assignment that's overdue
                is_at_risk = True
                alert_reason = "overdue"
            elif score is not None and score <= 69:
                # Failing assignment
                is_at_risk = True
                if is_overdue:
                    alert_reason = "overdue and failing"
                else:
                    alert_reason = "failing"
            
            if is_at_risk:
                if grade.student.id not in seen_student_ids:
                    at_risk_alerts.append({
                        'student_name': f"{grade.student.first_name} {grade.student.last_name}",
                        'student_user_id': grade.student.id,  # Use student ID instead of user_id
                        'class_name': grade.assignment.class_info.name,
                        'assignment_name': grade.assignment.title,
                        'alert_reason': alert_reason,
                        'score': score,
                        'due_date': grade.assignment.due_date
                    })
                    seen_student_ids.add(grade.student.id)
        except (json.JSONDecodeError, TypeError):
            continue
    # --- END ALERTS ---
    
    # --- Debugging Print Statements ---
    print(f"--- Debug Dashboard Alerts ---")
    print(f"Checking alerts for user: {current_user.username}, Role: {current_user.role}")
    print(f"Teacher classes: {len(classes)}")
    print(f"Class IDs: {class_ids}")
    print(f"Students being checked IDs: {student_ids[:10] if len(student_ids) > 10 else student_ids} (showing first 10 of {len(student_ids)})")
    print(f"Raw at-risk grades query result count: {len(at_risk_grades)}")
    print(f"Formatted alerts list being sent to template: {at_risk_alerts}")
    print(f"Number of alerts: {len(at_risk_alerts)}")
    print(f"--- End Debug ---")
    # --- End Debugging ---
    
    # Convert classes to JSON-serializable format for JavaScript
    classes_json = [{'id': c.id, 'name': c.name, 'subject': c.subject or 'N/A'} for c in classes]
    
    return render_template('management/role_teacher_dashboard.html', 
                         teacher=teacher, 
                         teacher_data=teacher_data,
                         classes=classes,
                         classes_json=classes_json,
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
                         is_admin=is_admin(),
                         at_risk_alerts=at_risk_alerts)

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
        return redirect(url_for('teacher.dashboard.teacher_dashboard'))

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
        'teachers/teacher_class_roster_view.html',
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
    try:
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
                # Query classes where teacher is:
                # 1. Primary teacher (teacher_id == teacher.id)
                # 2. Additional teacher (in class_additional_teachers table)
                # 3. Substitute teacher (in class_substitute_teachers table)
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
    
        # Calculate active enrollment count for each class
        # Use a direct query to avoid lazy loading issues
        for class_obj in classes:
            try:
                # Query enrollments directly to avoid lazy loading issues
                active_count = Enrollment.query.filter_by(
                    class_id=class_obj.id,
                    is_active=True
                ).count()
                class_obj.active_student_count = active_count
            except Exception as e:
                # If there's an error, set count to 0
                current_app.logger.error(f"Error calculating enrollment count for class {class_obj.id}: {e}")
                class_obj.active_student_count = 0
    
        return render_template('management/role_classes.html', classes=classes, teacher=teacher)
    
    except Exception as e:
        current_app.logger.error(f"Error in my_classes route: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash("An error occurred while loading your classes.", "danger")
        return render_template('management/role_classes.html', classes=[], teacher=None)

@bp.route('/deadline-reminders')
@login_required
@teacher_required
def deadline_reminders():
    """View deadline reminders for all assignments"""
    from datetime import datetime, timedelta
    
    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Get all assignments for teacher's classes
    class_ids = [c.id for c in classes]
    all_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).order_by(Assignment.due_date.asc()).all()
    
    # Categorize assignments by deadline
    # New logic: Only show assignments that are due today, this week, or later
    # AND assignments where students haven't turned them in
    now = datetime.now()
    overdue = []  # Keep for backwards compatibility but will be empty or filtered
    today = []
    this_week = []
    next_week = []
    later = []
    
    for assignment in all_assignments:
        if assignment.due_date:
            days_until = (assignment.due_date - now).days
            
            # Get enrolled students
            enrolled_students = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
            enrolled_student_ids = [e.student_id for e in enrolled_students]
            
            # Get all submissions and grades
            submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
            graded_students = Grade.query.filter_by(assignment_id=assignment.id).all()
            
            # Get students who are voided for this assignment
            voided_student_ids = set()
            for grade in graded_students:
                if grade.is_voided:
                    voided_student_ids.add(grade.student_id)
                elif grade.grade_data:
                    try:
                        grade_data = json.loads(grade.grade_data)
                        if grade_data.get('is_voided'):
                            voided_student_ids.add(grade.student_id)
                    except:
                        pass
            
            # Track students who have actually submitted (not marked as "not_submitted")
            actually_submitted_student_ids = set()
            for sub in submissions:
                if sub.student_id not in voided_student_ids:
                    # Only count as submitted if submission_type is NOT 'not_submitted'
                    if sub.submission_type and sub.submission_type != 'not_submitted':
                        actually_submitted_student_ids.add(sub.student_id)
            
            # Track students who have been graded with a score > 5
            # (exclude "not_submitted" grades with score <= 5)
            graded_student_ids = set()
            not_submitted_low_score_students = set()  # Students with score <= 5 marked as not_submitted
            
            for grade in graded_students:
                if grade.student_id not in voided_student_ids and not grade.is_voided:
                    if grade.grade_data:
                        try:
                            grade_data = json.loads(grade.grade_data)
                            score = grade_data.get('score')
                            
                            if score is not None:
                                # Check if this grade is for a "not_submitted" submission
                                submission = Submission.query.filter_by(
                                    assignment_id=assignment.id,
                                    student_id=grade.student_id
                                ).first()
                                
                                if submission and submission.submission_type == 'not_submitted':
                                    # This is marked as "not_submitted" by teacher
                                    if score <= 5:
                                        # Score 5 or below marked as not submitted - needs reminder
                                        not_submitted_low_score_students.add(grade.student_id)
                                    else:
                                        # Score > 5, count as graded
                                        graded_student_ids.add(grade.student_id)
                                else:
                                    # Normal grade, count as graded
                                    graded_student_ids.add(grade.student_id)
                        except:
                            pass
            
            # Students who haven't submitted (excluding voided)
            students_not_submitted = set()
            for student_id in enrolled_student_ids:
                if student_id not in voided_student_ids:
                    # Check if student has actually submitted
                    if student_id not in actually_submitted_student_ids:
                        students_not_submitted.add(student_id)
            
            # Total students minus voided students
            total_counted = len([sid for sid in enrolled_student_ids if sid not in voided_student_ids])
            
            # Count submissions for display (actual submissions, not "not_submitted")
            assignment.submission_count = len(actually_submitted_student_ids)
            assignment.total_students = total_counted
            assignment.completion_rate = (len(actually_submitted_student_ids) / total_counted * 100) if total_counted > 0 else 0
            assignment.days_until = days_until
            assignment.students_not_submitted = students_not_submitted
            assignment.not_submitted_low_score_students = not_submitted_low_score_students
            assignment.has_students_needing_reminder = len(students_not_submitted) > 0 or len(not_submitted_low_score_students) > 0
            
            # Only show assignments that:
            # 1. Are due today, this week, or later (not past due unless students haven't submitted)
            # 2. Have students who haven't submitted
            # 3. OR have "not_submitted" grades with score <= 5
            
            should_show = assignment.has_students_needing_reminder
            
            if days_until < 0:
                # Past due - only show if students haven't submitted
                if should_show:
                    overdue.append(assignment)
            elif days_until == 0:
                # Due today - show if students haven't submitted
                if should_show:
                    today.append(assignment)
            elif days_until <= 14:
                # Due this week or next week - show if students haven't submitted
                if should_show:
                    this_week.append(assignment)
            else:
                # Due later - show if students haven't submitted
                if should_show:
                    later.append(assignment)
    
    return render_template('teachers/teacher_deadline_reminders.html',
                         overdue=overdue,
                         today=today,
                         this_week=this_week,
                         next_week=[],  # Empty for backwards compatibility
                         later=later,
                         classes=classes)

@bp.route('/send-reminder/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def send_reminder(assignment_id):
    """Send deadline reminder notification to students"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to send reminders for this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.deadline_reminders'))
    
    reminder_type = request.form.get('reminder_type')
    student_ids = request.form.getlist('student_ids')
    custom_message = request.form.get('custom_message', '').strip()
    
    try:
        if reminder_type == 'all':
            # Send to all enrolled students
            enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
            student_ids = [str(e.student_id) for e in enrollments if e.student_id]
        
        if not student_ids:
            flash("No students selected to send reminder to.", "warning")
            return redirect(url_for('teacher.dashboard.deadline_reminders'))
        
        # Create notifications for each student
        for student_id in student_ids:
            notification = Notification(
                user_id=int(student_id),
                title=f"Reminder: {assignment.title}",
                message=custom_message or f"Don't forget! Assignment '{assignment.title}' is due on {assignment.due_date.strftime('%b %d, %Y at %I:%M %p')}.",
                notification_type='deadline_reminder',
                is_read=False,
                created_at=datetime.now()
            )
            db.session.add(notification)
        
        db.session.commit()
        flash(f"Reminder sent to {len(student_ids)} student(s) successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error sending reminder: {str(e)}")
        flash(f"Error sending reminder: {str(e)}", "danger")
    
    return redirect(url_for('teacher.dashboard.deadline_reminders'))

@bp.route('/assignments')
@login_required
@teacher_required
def my_assignments():
    """Redirect to assignments and grades page."""
    # Preserve query parameters when redirecting
    query_string = request.query_string.decode('utf-8')
    if query_string:
        return redirect(url_for('teacher.dashboard.assignments_and_grades') + '?' + query_string)
    return redirect(url_for('teacher.dashboard.assignments_and_grades'))

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
    
    return render_template('students/role_students.html', students=students, teacher=teacher)

@bp.route('/teachers-staff')
@login_required
@teacher_required
def teachers_staff():
    """Display all teachers and staff members."""
    teachers_staff = TeacherStaff.query.all()
    
    return render_template('management/role_teachers_staff.html', 
                         teachers_staff=teachers_staff,
                         search_query=None,
                         total_teachers_staff=len(teachers_staff))

@bp.route('/assignments-and-grades')
@login_required
@teacher_required  
def assignments_and_grades():
    """Combined view of assignments and grades for teachers"""
    import json
    try:
        # Get teacher object or None for administrators
        teacher = get_teacher_or_admin()
        
        # Get classes for the current teacher/admin
        if is_admin():
            accessible_classes = Class.query.all()
        else:
            if teacher is None:
                accessible_classes = []
            else:
                # Query classes where teacher is:
                # 1. Primary teacher (teacher_id == teacher.id)
                # 2. Additional teacher (in class_additional_teachers table)
                # 3. Substitute teacher (in class_substitute_teachers table)
                accessible_classes = Class.query.filter(
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
        
        # Filter out any invalid class objects
        accessible_classes = [c for c in accessible_classes if c and hasattr(c, 'id') and c.id is not None]
        
        # Get filter and sort parameters
        class_filter = request.args.get('class_id', '') or ''
        sort_by = request.args.get('sort', 'due_date') or 'due_date'
        sort_order = request.args.get('order', 'desc') or 'desc'
        view_mode = request.args.get('view', 'assignments') or 'assignments'
        
        # If no class is selected, show the class selection interface
        if not class_filter or not class_filter.strip():
            # Get assignment counts for each class
            class_assignments = {}
            for class_obj in accessible_classes:
                if class_obj and hasattr(class_obj, 'id') and class_obj.id is not None:
                    regular_count = Assignment.query.filter_by(class_id=class_obj.id).count()
                    try:
                        from models import GroupAssignment
                        group_count = GroupAssignment.query.filter_by(class_id=class_obj.id).count()
                    except:
                        group_count = 0
                    class_assignments[class_obj.id] = regular_count + group_count
            
            # Calculate unique student count
            unique_student_ids = set()
            for class_obj in accessible_classes:
                if class_obj and hasattr(class_obj, 'id'):
                    enrollments = Enrollment.query.filter_by(class_id=class_obj.id, is_active=True).all()
                    for enrollment in enrollments:
                        if enrollment.student_id:
                            unique_student_ids.add(enrollment.student_id)
            unique_student_count = len(unique_student_ids)
            
            # Get pending extension request count for teacher's classes
            from models import ExtensionRequest
            if is_admin():
                pending_extension_count = ExtensionRequest.query.filter_by(status='Pending').count()
            else:
                if teacher is None:
                    pending_extension_count = 0
                else:
                    class_ids = [c.id for c in accessible_classes]
                    assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
                    assignment_ids = [a.id for a in assignments]
                    pending_extension_count = ExtensionRequest.query.filter(
                        ExtensionRequest.assignment_id.in_(assignment_ids),
                        ExtensionRequest.status == 'Pending'
                    ).count()
            
            return render_template('management/assignments_and_grades.html',
                                 accessible_classes=accessible_classes,
                                 class_assignments=class_assignments,
                                 unique_student_count=unique_student_count,
                                 selected_class=None,
                                 class_assignments_data=None,
                                 assignment_grades=None,
                                 sort_by=sort_by,
                                 sort_order=sort_order,
                                 view_mode=view_mode,
                                 user_role=current_user.role if hasattr(current_user, 'role') else 'Teacher',
                                 show_class_selection=True,
                                 extension_request_count=pending_extension_count)
        
        # Handle class filter
        selected_class = None
        class_assignments = []
        group_assignments = []
        assignment_grades = {}
        
        if class_filter and isinstance(class_filter, str) and class_filter.strip():
            try:
                clean_filter = class_filter.strip()
                current_app.logger.info(f"[DEBUG assignments_and_grades] Class filter: '{clean_filter}'")
                current_app.logger.info(f"[DEBUG assignments_and_grades] Current user: {current_user.username if hasattr(current_user, 'username') else 'Unknown'}, Role: '{current_user.role}'")
                current_app.logger.info(f"[DEBUG assignments_and_grades] Accessible classes count: {len(accessible_classes)}")
                current_app.logger.info(f"[DEBUG assignments_and_grades] Accessible class IDs: {[c.id for c in accessible_classes if hasattr(c, 'id')]}")
                
                if clean_filter.isdigit():
                    selected_class_id = int(clean_filter)
                    current_app.logger.info(f"[DEBUG assignments_and_grades] Looking for class ID: {selected_class_id}")
                    # First try to find in accessible_classes
                    selected_class = next((c for c in accessible_classes if hasattr(c, 'id') and c.id == selected_class_id), None)
                    
                    if selected_class:
                        current_app.logger.info(f"[DEBUG assignments_and_grades] Found class in accessible_classes: {selected_class.name}")
                    else:
                        current_app.logger.info(f"[DEBUG assignments_and_grades] Class not in accessible_classes, querying directly...")
                        # If not found, query directly and check authorization
                        selected_class = Class.query.get(selected_class_id)
                        if selected_class:
                            current_app.logger.info(f"[DEBUG assignments_and_grades] Queried class: {selected_class.name}, checking authorization...")
                            if not is_authorized_for_class(selected_class):
                                current_app.logger.error(f"[DEBUG assignments_and_grades] ✗ Authorization FAILED for class {selected_class_id}")
                                flash("You do not have permission to access this page.", "danger")
                                return redirect(url_for('teacher.dashboard.assignments_and_grades'))
                            else:
                                current_app.logger.info(f"[DEBUG assignments_and_grades] ✓ Authorization PASSED for class {selected_class_id}")
                        else:
                            current_app.logger.error(f"[DEBUG assignments_and_grades] Class {selected_class_id} not found in database")
                else:
                    selected_class = None
                    current_app.logger.warning(f"[DEBUG assignments_and_grades] Invalid class filter (not a digit): '{clean_filter}'")
                
                if selected_class:
                    # Double-check authorization
                    current_app.logger.info(f"[DEBUG assignments_and_grades] Double-checking authorization for class {selected_class.id}...")
                    current_app.logger.info(f"[DEBUG assignments_and_grades] Current user role: '{current_user.role}'")
                    current_app.logger.info(f"[DEBUG assignments_and_grades] Is admin check: {is_admin()}")
                    auth_result = is_authorized_for_class(selected_class)
                    current_app.logger.info(f"[DEBUG assignments_and_grades] Authorization result: {auth_result}")
                    if not auth_result:
                        current_app.logger.error(f"[DEBUG assignments_and_grades] ✗ Double-check authorization FAILED for class {selected_class.id}")
                        current_app.logger.error(f"[DEBUG assignments_and_grades] User role was: '{current_user.role}'")
                        flash("You do not have permission to access this page.", "danger")
                        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
                    else:
                        current_app.logger.info(f"[DEBUG assignments_and_grades] ✓ Double-check authorization PASSED for class {selected_class.id}")
                    # Get regular assignments for the selected class
                    selected_class_id = selected_class.id  # Ensure we have the ID
                    assignments_query = Assignment.query.filter_by(class_id=selected_class_id)
                    
                    # Apply sorting
                    if sort_by == 'title':
                        if sort_order == 'asc':
                            assignments_query = assignments_query.order_by(Assignment.title.asc())
                        else:
                            assignments_query = assignments_query.order_by(Assignment.title.desc())
                    else:  # due_date
                        if sort_order == 'asc':
                            assignments_query = assignments_query.order_by(Assignment.due_date.asc())
                        else:
                            assignments_query = assignments_query.order_by(Assignment.due_date.desc())
                    
                    class_assignments = assignments_query.all()
                    
                    # Get group assignments if available
                    try:
                        from models import GroupAssignment
                        group_assignments_query = GroupAssignment.query.filter_by(class_id=selected_class_id)
                        
                        if sort_by == 'title':
                            if sort_order == 'asc':
                                group_assignments_query = group_assignments_query.order_by(GroupAssignment.title.asc())
                            else:
                                group_assignments_query = group_assignments_query.order_by(GroupAssignment.title.desc())
                        else:  # due_date
                            if sort_order == 'asc':
                                group_assignments_query = group_assignments_query.order_by(GroupAssignment.due_date.asc())
                            else:
                                group_assignments_query = group_assignments_query.order_by(GroupAssignment.due_date.desc())
                        
                        group_assignments = group_assignments_query.all()
                    except:
                        group_assignments = []
                    
                    # Get grade data for each assignment
                    for assignment in class_assignments:
                        grades = Grade.query.filter_by(assignment_id=assignment.id).all()
                        graded_count = sum(1 for g in grades if g.grade_data)
                        
                        # Check if quiz is auto-gradeable (all questions are multiple_choice or true_false)
                        is_autogradeable = False
                        if assignment.assignment_type == 'quiz':
                            from models import QuizQuestion
                            quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment.id).all()
                            if quiz_questions:
                                # Check if all questions are auto-gradeable
                                auto_gradeable_types = ['multiple_choice', 'true_false']
                                is_autogradeable = all(q.question_type in auto_gradeable_types for q in quiz_questions)
                        
                        # Calculate average
                        total_score = 0
                        graded_with_score = 0
                        for grade in grades:
                            if grade.grade_data:
                                try:
                                    if isinstance(grade.grade_data, dict):
                                        grade_dict = grade.grade_data
                                    else:
                                        grade_dict = json.loads(grade.grade_data)
                                    
                                    if 'score' in grade_dict and grade_dict['score'] is not None:
                                        total_score += grade_dict['score']
                                        graded_with_score += 1
                                except (json.JSONDecodeError, TypeError):
                                    continue
                        
                        average_score = 0
                        if graded_with_score > 0:
                            average_score = round(total_score / graded_with_score, 1)
                        
                        assignment_grades[assignment.id] = {
                            'total_submissions': len(grades),
                            'graded_count': graded_count,
                            'average_score': average_score,
                            'is_autogradeable': is_autogradeable
                        }
                    
                    # Get grade data for group assignments
                    for group_assignment in group_assignments:
                        from models import GroupGrade
                        group_grades = GroupGrade.query.filter_by(group_assignment_id=group_assignment.id).all()
                        graded_count = sum(1 for g in group_grades if g.grade_data)
                        
                        # Calculate average for group assignments
                        total_score = 0
                        graded_with_score = 0
                        for grade in group_grades:
                            if grade.grade_data:
                                try:
                                    if isinstance(grade.grade_data, dict):
                                        grade_dict = grade.grade_data
                                    else:
                                        grade_dict = json.loads(grade.grade_data)
                                    
                                    if 'score' in grade_dict and grade_dict['score'] is not None:
                                        total_score += grade_dict['score']
                                        graded_with_score += 1
                                except (json.JSONDecodeError, TypeError):
                                    continue
                        
                        average_score = 0
                        if graded_with_score > 0:
                            average_score = round(total_score / graded_with_score, 1)
                        
                        assignment_grades[f'group_{group_assignment.id}'] = {
                            'total_submissions': len(group_grades),
                            'graded_count': graded_count,
                            'average_score': average_score
                        }
            
            except Exception as e:
                current_app.logger.error(f"Error processing class filter: {e}")
                import traceback
                current_app.logger.error(traceback.format_exc())
                flash("Error loading class data.", "danger")
                return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
        # Get assignment counts for all classes (for class selection view)
        class_assignments_count = {}
        for class_obj in accessible_classes:
            if class_obj and hasattr(class_obj, 'id') and class_obj.id is not None:
                regular_count = Assignment.query.filter_by(class_id=class_obj.id).count()
                try:
                    from models import GroupAssignment
                    group_count = GroupAssignment.query.filter_by(class_id=class_obj.id).count()
                except:
                    group_count = 0
                class_assignments_count[class_obj.id] = regular_count + group_count
        
        # Calculate unique student count
        unique_student_ids = set()
        for class_obj in accessible_classes:
            if class_obj and hasattr(class_obj, 'id'):
                enrollments = Enrollment.query.filter_by(class_id=class_obj.id, is_active=True).all()
                for enrollment in enrollments:
                    if enrollment.student_id:
                        unique_student_ids.add(enrollment.student_id)
        unique_student_count = len(unique_student_ids)
        
        # Get today's date for template
        from datetime import date
        today = date.today()
        
        # For table view, calculate student grades and averages
        table_student_grades = {}
        table_student_averages = {}
        enrolled_students = []
        all_assignments_list = []
        
        if selected_class and view_mode == 'table':
            # Get enrolled students
            enrollments = Enrollment.query.filter_by(class_id=selected_class.id, is_active=True).all()
            enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student]
            
            # Get all assignments for the table
            all_assignments_list = list(class_assignments) + list(group_assignments)
            
            # Get grades for enrolled students (individual assignments)
            for student in enrolled_students:
                table_student_grades[student.id] = {}
                for assignment in class_assignments:
                    grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
                    if grade:
                        try:
                            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                            table_student_grades[student.id][assignment.id] = {
                                'grade': grade_data.get('score', 'N/A'),
                                'comments': grade_data.get('comments', ''),
                                'graded_at': grade.graded_at,
                                'type': 'individual',
                                'is_voided': grade.is_voided if hasattr(grade, 'is_voided') else False
                            }
                        except (json.JSONDecodeError, TypeError):
                            table_student_grades[student.id][assignment.id] = {
                                'grade': 'N/A',
                                'comments': 'Error parsing grade data',
                                'graded_at': grade.graded_at,
                                'type': 'individual',
                                'is_voided': grade.is_voided if hasattr(grade, 'is_voided') else False
                            }
                    else:
                        table_student_grades[student.id][assignment.id] = {
                            'grade': 'Not Graded',
                            'comments': '',
                            'graded_at': None,
                            'is_voided': False,
                            'type': 'individual'
                        }
                
                # Get group assignment grades
                from models import GroupGrade, StudentGroupMember, StudentGroup
                for group_assignment in group_assignments:
                    # Check if this group assignment is for specific groups
                    assignment_group_ids = []
                    if group_assignment.selected_group_ids:
                        try:
                            raw_group_ids = json.loads(group_assignment.selected_group_ids)
                            assignment_group_ids = [int(gid) for gid in raw_group_ids]
                        except (json.JSONDecodeError, TypeError, ValueError):
                            assignment_group_ids = []
                    
                    # Find what group this student is in for this class
                    should_show_assignment = False
                    student_group_id = None
                    student_group_name = 'N/A'
                    
                    if not assignment_group_ids:
                        student_group_member = StudentGroupMember.query.join(StudentGroup).filter(
                            StudentGroup.class_id == selected_class.id,
                            StudentGroupMember.student_id == student.id
                        ).order_by(StudentGroupMember.id.desc()).first()
                        
                        if student_group_member and student_group_member.group:
                            student_group_id = student_group_member.group.id
                            student_group_name = student_group_member.group.name
                            should_show_assignment = True
                    else:
                        student_group_member = StudentGroupMember.query.join(StudentGroup).filter(
                            StudentGroup.class_id == selected_class.id,
                            StudentGroupMember.student_id == student.id,
                            StudentGroup.id.in_(assignment_group_ids)
                        ).order_by(StudentGroupMember.id.desc()).first()
                        
                        if student_group_member and student_group_member.group:
                            student_group_id = student_group_member.group.id
                            student_group_name = student_group_member.group.name
                            should_show_assignment = True
                    
                    if should_show_assignment:
                        if student_group_id:
                            group_grade = GroupGrade.query.filter_by(
                                student_id=student.id,
                                group_assignment_id=group_assignment.id
                            ).first()
                            
                            if group_grade:
                                try:
                                    grade_data = json.loads(group_grade.grade_data) if group_grade.grade_data else {}
                                    table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                        'grade': grade_data.get('score', 'N/A'),
                                        'comments': grade_data.get('comments', ''),
                                        'graded_at': group_grade.graded_at,
                                        'type': 'group',
                                        'group_name': student_group_name,
                                        'is_voided': group_grade.is_voided if hasattr(group_grade, 'is_voided') else False
                                    }
                                except (json.JSONDecodeError, TypeError, AttributeError):
                                    table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                        'grade': 'N/A',
                                        'comments': 'Error parsing grade data',
                                        'graded_at': None,
                                        'type': 'group',
                                        'group_name': student_group_name,
                                        'is_voided': group_grade.is_voided if hasattr(group_grade, 'is_voided') else False
                                    }
                            else:
                                table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                    'grade': 'Not Graded',
                                    'comments': '',
                                    'graded_at': None,
                                    'type': 'group',
                                    'group_name': student_group_name,
                                    'is_voided': False
                                }
                        else:
                            table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                'grade': 'No Group',
                                'comments': 'Student not assigned to a group',
                                'graded_at': None,
                                'type': 'group',
                                'group_name': 'N/A',
                                'is_voided': False
                            }
                    else:
                        if not assignment_group_ids:
                            table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                'grade': 'No Group',
                                'comments': 'Student not assigned to a group',
                                'graded_at': None,
                                'is_voided': False,
                                'type': 'group',
                                'group_name': 'N/A'
                            }
                        else:
                            table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                'grade': 'Not Assigned',
                                'comments': 'Not assigned to this group',
                                'graded_at': None,
                                'type': 'group',
                                'group_name': 'N/A',
                                'is_voided': False
                            }
            
            # Calculate averages for each student
            for student_id, grades in table_student_grades.items():
                valid_grades = []
                for g in grades.values():
                    grade_val = g['grade']
                    # Skip voided grades
                    if g.get('is_voided', False):
                        continue
                    # Skip if the comment indicates the student isn't part of this assignment
                    if 'Not assigned to this group' in g.get('comments', ''):
                        continue
                    # Only include numeric grades
                    if grade_val not in ['N/A', 'Not Assigned', 'Not Graded', 'No Group']:
                        try:
                            valid_grades.append(float(grade_val))
                        except (ValueError, TypeError):
                            pass
                
                if valid_grades:
                    table_student_averages[student_id] = round(sum(valid_grades) / len(valid_grades), 2)
                else:
                    table_student_averages[student_id] = 'N/A'
        
        # Get pending extension request count for teacher's classes
        from models import ExtensionRequest
        if is_admin():
            pending_extension_count = ExtensionRequest.query.filter_by(status='Pending').count()
        else:
            if teacher is None:
                pending_extension_count = 0
            else:
                class_ids = [c.id for c in accessible_classes]
                assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
                assignment_ids = [a.id for a in assignments]
                pending_extension_count = ExtensionRequest.query.filter(
                    ExtensionRequest.assignment_id.in_(assignment_ids),
                    ExtensionRequest.status == 'Pending'
                ).count()
        
        return render_template('management/assignments_and_grades.html',
                             accessible_classes=accessible_classes,
                             classes=accessible_classes,  # For dropdown filter
                             class_assignments=class_assignments_count if not selected_class else class_assignments,
                             unique_student_count=unique_student_count,
                             selected_class=selected_class,
                             class_assignments_data=class_assignments if selected_class else None,
                             group_assignments=group_assignments if selected_class else [],
                             assignment_grades=assignment_grades if selected_class else {},
                             sort_by=sort_by,
                             sort_order=sort_order,
                             view_mode=view_mode,
                             user_role=current_user.role if hasattr(current_user, 'role') else 'Teacher',
                             show_class_selection=not selected_class,
                             class_filter=class_filter if selected_class else '',
                             today=today,
                             extension_request_count=pending_extension_count,
                             # Table view data
                             enrolled_students=enrolled_students if view_mode == 'table' else [],
                             student_grades=table_student_grades if view_mode == 'table' else {},
                             student_averages=table_student_averages if view_mode == 'table' else {},
                             all_assignments=all_assignments_list if view_mode == 'table' else [])
    
    except Exception as e:
        current_app.logger.error(f"Error in assignments_and_grades route: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash("An error occurred while loading assignments and grades.", "danger")
        return redirect(url_for('teacher.dashboard.teacher_dashboard'))

@bp.route('/resources')
@login_required
@teacher_required
def resources():
    """Resources page - placeholder that redirects to dashboard"""
    flash("Resources page is being updated. Please check back later.", "info")
    return redirect(url_for('teacher.dashboard.teacher_dashboard'))

@bp.route('/calendar')
@login_required
@teacher_required
def calendar():
    """Display the calendar view."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Get month and year from request or use current
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Calculate previous and next month
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    
    # Create calendar data
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')
    
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
    
    # Simple calendar data structure
    calendar_data = {
        'month_name': month_name,
        'year': year,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'weeks': []
    }
    
    # Convert calendar to our format
    for week in cal_obj:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day_num': '', 'is_current_month': False, 'is_today': False, 'events': []})
            else:
                is_today = (day == datetime.now().day and month == datetime.now().month and year == datetime.now().year)
                
                # Get assignments for this day
                day_events = []
                for assignment in assignments:
                    if assignment.due_date and assignment.due_date.day == day and assignment.due_date.month == month and assignment.due_date.year == year:
                        day_events.append({
                            'title': assignment.title,
                            'class_name': assignment.class_info.name if assignment.class_info else 'Unknown'
                        })
                
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': day_events})
        calendar_data['weeks'].append(week_data)
    
    return render_template('management/role_calendar.html', 
                         calendar_data=calendar_data,
                         prev_month=prev_month,
                         next_month=next_month,
                         month_name=month_name,
                         year=year,
                         assignments=assignments, 
                         classes=classes, 
                         teacher=teacher)

@bp.route('/schedule')
@login_required
@teacher_required
def teacher_schedule():
    """Display teacher's weekly class schedule."""
    from models import ClassSchedule
    
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Get classes assigned to teacher
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            # Get classes where teacher is primary, additional, or substitute
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            # Also get classes where teacher is additional or substitute
            from models import class_additional_teachers, class_substitute_teachers
            additional_classes = db.session.query(Class).join(
                class_additional_teachers
            ).filter(class_additional_teachers.c.teacher_id == teacher.id).all()
            substitute_classes = db.session.query(Class).join(
                class_substitute_teachers
            ).filter(class_substitute_teachers.c.teacher_id == teacher.id).all()
            # Combine all classes
            all_class_ids = {c.id for c in classes}
            for c in additional_classes + substitute_classes:
                if c.id not in all_class_ids:
                    classes.append(c)
                    all_class_ids.add(c.id)
    
    # Get full weekly schedule (Monday=0 to Sunday=6)
    weekly_schedule = {}
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day_num in range(7):
        day_schedules = []
        for class_obj in classes:
            schedule = ClassSchedule.query.filter_by(
                class_id=class_obj.id,
                day_of_week=day_num
            ).first()
            
            if schedule:
                # Count enrolled students
                from models import Enrollment
                student_count = Enrollment.query.filter_by(
                    class_id=class_obj.id,
                    is_active=True
                ).count()
                
                day_schedules.append({
                    'class': class_obj,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time,
                    'time_str': f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}",
                    'room': schedule.room or 'TBD',
                    'student_count': student_count
                })
        
        # Sort by start time
        day_schedules.sort(key=lambda x: x['start_time'])
        weekly_schedule[day_num] = {
            'day_name': day_names[day_num],
            'schedules': day_schedules
        }
    
    # Get today's weekday for highlighting
    today = datetime.now()
    today_weekday = today.weekday()
    
    return render_template('teachers/teacher_schedule.html',
                         weekly_schedule=weekly_schedule,
                         today_weekday=today_weekday,
                         classes=classes,
                         teacher=teacher)


@bp.route('/schedule')
@login_required
@teacher_required
def schedule():
    """View teacher's weekly class schedule"""
    try:
        teacher = get_teacher_or_admin()
        
        # Initialize default values
        schedules_by_day = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday
        today_schedule = []
        classes = []
        time_slots = []
        
        # Get current school year
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            # Convert classes to JSON-serializable format for JavaScript (if needed)
            classes_json = []
            
            return render_template('management/role_teacher_dashboard.html',
                                 teacher=teacher,
                                 schedules_by_day=schedules_by_day,
                                 today_schedule=today_schedule,
                                 classes=classes,
                                 classes_json=classes_json,
                                 time_slots=time_slots,
                                 section='schedule',
                                 active_tab='schedule',
                                 is_admin=is_admin(),
                                 show_schedule=True)
        
        # Get teacher's classes
        if is_admin():
            classes = Class.query.filter(Class.school_year_id == current_school_year.id).all()
        else:
            if teacher is None:
                classes = []
            else:
                classes = Class.query.filter_by(
                    teacher_id=teacher.id,
                    school_year_id=current_school_year.id
                ).all()
        
        # Get schedules for all teacher's classes
        class_ids = [c.id for c in classes]
        all_schedules = []
        if class_ids:  # Only query if there are classes
            all_schedules = ClassSchedule.query.filter(
                ClassSchedule.class_id.in_(class_ids)
            ).order_by(ClassSchedule.day_of_week, ClassSchedule.start_time).all()
        
        # Organize schedules by day of week
        time_slots_set = set()  # Track unique time slots
        
        for schedule_item in all_schedules:
            try:
                if not schedule_item or not schedule_item.class_id:
                    continue
                    
                class_obj = next((c for c in classes if c.id == schedule_item.class_id), None)
                if not class_obj:
                    continue
                    
                if not schedule_item.start_time or not schedule_item.end_time:
                    continue
                
                # Ensure day_of_week is an integer (0-6)
                day_of_week = int(schedule_item.day_of_week) if schedule_item.day_of_week is not None else 0
                if day_of_week < 0 or day_of_week > 6:
                    continue  # Skip invalid day_of_week values
                
                # Get enrollment count
                try:
                    enrollment_count = Enrollment.query.filter_by(
                        class_id=class_obj.id,
                        is_active=True
                    ).count()
                except:
                    enrollment_count = 0
                
                time_key = f"{schedule_item.start_time.strftime('%H:%M')}-{schedule_item.end_time.strftime('%H:%M')}"
                time_slots_set.add(time_key)
                
                schedules_by_day[day_of_week].append({
                    'class': class_obj,
                    'start_time': schedule_item.start_time,
                    'end_time': schedule_item.end_time,
                    'room': schedule_item.room or (class_obj.room_number if class_obj.room_number else 'TBD'),
                    'enrollment_count': enrollment_count
                })
            except Exception as e:
                print(f"Error processing schedule item {schedule_item.id if schedule_item else 'unknown'}: {e}")
                continue
        
        # Sort time slots
        time_slots = sorted(time_slots_set) if time_slots_set else []
        
        # Get today's schedule
        today = datetime.now()
        today_weekday = today.weekday()  # 0=Monday, 1=Tuesday, etc.
        today_schedule = schedules_by_day.get(today_weekday, [])
        
        # Sort today's schedule by start time
        if today_schedule:
            today_schedule.sort(key=lambda x: x['start_time'])
        
        # Convert classes to JSON-serializable format for JavaScript (if needed)
        classes_json = [{'id': c.id, 'name': c.name, 'subject': c.subject or 'N/A'} for c in classes]
        
        return render_template('management/role_teacher_dashboard.html',
                             teacher=teacher,
                             schedules_by_day=schedules_by_day,
                             today_schedule=today_schedule,
                             classes=classes,
                             classes_json=classes_json,
                             time_slots=time_slots,
                             section='schedule',
                             active_tab='schedule',
                             is_admin=is_admin(),
                             show_schedule=True)
    except Exception as e:
        import traceback
        print(f"Error in teacher schedule route: {e}")
        print(traceback.format_exc())
        flash(f"An error occurred while loading your schedule: {str(e)}", "danger")
        try:
            teacher_obj = get_teacher_or_admin()
            admin_status = is_admin()
        except:
            teacher_obj = None
            admin_status = False
        return render_template('management/role_teacher_dashboard.html',
                             teacher=teacher_obj,
                             schedules_by_day={i: [] for i in range(7)},
                             today_schedule=[],
                             classes=[],
                             classes_json=[],
                             time_slots=[],
                             section='schedule',
                             active_tab='schedule',
                             is_admin=admin_status,
                             show_schedule=True)


# ===== GOOGLE CLASSROOM LINKING ROUTES =====

@bp.route('/class/<int:class_id>/create-and-link')
@login_required
@teacher_required
def create_and_link_classroom(class_id):
    """
    OPTION 1: CREATE A NEW GOOGLE CLASSROOM AND LINK IT
    Creates a brand new Google Classroom and links it to the existing class in the system.
    """
    class_to_link = Class.query.get_or_404(class_id)
    
    # Check authorization for this class
    if not is_authorized_for_class(class_to_link):
        flash("You are not authorized to modify this class.", "danger")
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    # Check if teacher has connected their account
    if not current_user.google_refresh_token:
        flash("You must connect your Google account first.", "warning")
        return redirect(url_for('teacher.google_connect_account'))

    try:
        service = get_google_service(current_user)
        if not service:
            flash("Could not connect to Google. Please try reconnecting your account.", "danger")
            return redirect(url_for('teacher.dashboard.my_classes'))

        # Create the new course
        course_body = {
            'name': class_to_link.name,
            'ownerId': 'me'
        }
        if class_to_link.description:
            course_body['description'] = class_to_link.description
        if class_to_link.subject:
            course_body['section'] = class_to_link.subject
        
        course = service.courses().create(body=course_body).execute()
        google_id = course.get('id')
        
        # Save the new ID to our database
        class_to_link.google_classroom_id = google_id
        db.session.commit()
        
        flash(f"Successfully created and linked new Google Classroom: '{course.get('name')}'", "success")
        current_app.logger.info(f"Teacher {current_user.id} created and linked Google Classroom {google_id} for class {class_id}")

    except HttpError as e:
        flash(f"Google API error: {e._get_reason()}", "danger")
        current_app.logger.error(f"Google API error creating classroom: {e}")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        current_app.logger.error(f"Unexpected error creating classroom: {e}")
        
    return redirect(url_for('teacher.dashboard.my_classes'))


@bp.route('/class/<int:class_id>/link-existing')
@login_required
@teacher_required
def link_existing_classroom(class_id):
    """
    OPTION 2, Route A: SHOW THE LIST OF EXISTING GOOGLE CLASSROOMS
    Displays a list of the teacher's existing Google Classrooms that can be linked.
    """
    class_to_link = Class.query.get_or_404(class_id)
    
    # Check authorization for this class
    if not is_authorized_for_class(class_to_link):
        flash("You are not authorized to modify this class.", "danger")
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    # Check if teacher has connected their account
    if not current_user.google_refresh_token:
        flash("You must connect your Google account first to see your existing classes.", "warning")
        return redirect(url_for('teacher.google_connect_account'))
    
    try:
        service = get_google_service(current_user)
        if not service:
            flash("Could not connect to Google. Please try reconnecting your account.", "danger")
            return redirect(url_for('teacher.dashboard.my_classes'))

        # Fetch the list of the teacher's active courses
        results = service.courses().list(teacherId='me', courseStates=['ACTIVE']).execute()
        courses = results.get('courses', [])
        
        # Filter out any courses that are *already* linked to another class in your system
        linked_ids = {c.google_classroom_id for c in Class.query.filter(Class.google_classroom_id.isnot(None)).all()}
        available_courses = [c for c in courses if c.get('id') not in linked_ids]
        
        if not available_courses:
            flash("You have no available Google Classrooms to link. All your classes are either already linked or you have no active classes.", "info")
            return redirect(url_for('teacher.dashboard.my_classes'))

        return render_template(
            'teachers/link_existing_classroom.html',
            class_to_link=class_to_link,
            courses=available_courses
        )

    except HttpError as e:
        flash(f"Google API error: {e._get_reason()}", "danger")
        current_app.logger.error(f"Google API error fetching classrooms: {e}")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        current_app.logger.error(f"Unexpected error fetching classrooms: {e}")

    return redirect(url_for('teacher.dashboard.my_classes'))


@bp.route('/class/<int:class_id>/save-link', methods=['POST'])
@login_required
@teacher_required
def save_google_classroom_link(class_id):
    """
    OPTION 2, Route B: SAVE THE LINK FROM THE FORM
    Saves the selected Google Classroom ID to the class in the database.
    """
    class_to_link = Class.query.get_or_404(class_id)
    
    # Check authorization for this class
    if not is_authorized_for_class(class_to_link):
        flash("You are not authorized to modify this class.", "danger")
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    google_course_id = request.form.get('google_course_id')
    
    if not google_course_id:
        flash("You did not select a class.", "danger")
        return redirect(url_for('teacher.dashboard.link_existing_classroom', class_id=class_id))
    
    # Verify this classroom ID isn't already linked to another class
    existing_link = Class.query.filter(
        Class.google_classroom_id == google_course_id,
        Class.id != class_id
    ).first()
    
    if existing_link:
        flash(f"This Google Classroom is already linked to another class: {existing_link.name}", "danger")
        return redirect(url_for('teacher.dashboard.link_existing_classroom', class_id=class_id))
    
    # Save the ID
    class_to_link.google_classroom_id = google_course_id
    db.session.commit()
    
    flash("Successfully linked to your existing Google Classroom!", "success")
    current_app.logger.info(f"Teacher {current_user.id} linked Google Classroom {google_course_id} to class {class_id}")
    
    return redirect(url_for('teacher.dashboard.my_classes'))


@bp.route('/class/<int:class_id>/unlink')
@login_required
@teacher_required
def unlink_classroom(class_id):
    """
    UNLINK ROUTE: Remove the Google Classroom link from the class.
    Note: This doesn't delete the Google Classroom, just removes the link in our system.
    """
    class_to_unlink = Class.query.get_or_404(class_id)
    
    # Check authorization for this class
    if not is_authorized_for_class(class_to_unlink):
        flash("You are not authorized to modify this class.", "danger")
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    if not class_to_unlink.google_classroom_id:
        flash("This class is not linked to a Google Classroom.", "info")
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    old_id = class_to_unlink.google_classroom_id
    class_to_unlink.google_classroom_id = None
    db.session.commit()
    
    flash("Successfully unlinked from Google Classroom. The course still exists in your Google account.", "info")
    current_app.logger.info(f"Teacher {current_user.id} unlinked Google Classroom {old_id} from class {class_id}")
    
    return redirect(url_for('teacher.dashboard.my_classes'))


@bp.route('/student/<int:student_id>/details/data')
@login_required
@teacher_required
def view_student_details_data(student_id):
    """API endpoint to get detailed student information as JSON for academic alerts (Teacher Version)."""
    from flask import jsonify
    from copy import copy
    from gpa_scheduler import calculate_student_gpa
    
    try:
        print(f"[Teacher Details] Fetching details for student ID: {student_id}")
        
        student = Student.query.get(student_id)
        if not student:
            print(f"[Teacher Details] Student {student_id} not found")
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        print(f"[Teacher Details] Found student: {student.first_name} {student.last_name}")
        
        # Verify teacher has access to this student (student must be in one of their classes)
        if not current_user.teacher_staff_id:
            print(f"[Teacher Details] No teacher_staff_id for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Teacher profile not found'}), 403
        
        teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
        if not teacher_staff:
            print(f"[Teacher Details] Teacher profile not found for teacher_staff_id {current_user.teacher_staff_id}")
            return jsonify({'success': False, 'error': 'Teacher profile not found'}), 403
        
        print(f"[Teacher Details] Teacher found: {teacher_staff.first_name} {teacher_staff.last_name}")
        
        # Get teacher's classes
        teacher_classes = Class.query.filter_by(teacher_id=teacher_staff.id).all()
        teacher_class_ids = [c.id for c in teacher_classes]
        
        # Check if student is enrolled in any of teacher's classes
        student_enrollments = Enrollment.query.filter_by(student_id=student_id, is_active=True).all()
        student_class_ids = [e.class_id for e in student_enrollments]
        
        # Check if there's overlap
        if not any(class_id in teacher_class_ids for class_id in student_class_ids):
            return jsonify({'success': False, 'error': 'You do not have access to this student'}), 403
        
        # --- GPA IMPACT ANALYSIS ---
        current_gpa = None
        hypothetical_gpa = None
        at_risk_grades_list = []
        missing_assignments_by_class = {}
        class_gpa_breakdown = {}

        # Get all non-voided grades for the student (only from teacher's classes)
        all_grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student.id,
            Assignment.class_id.in_(teacher_class_ids),
            db.or_(Grade.is_voided.is_(False), Grade.is_voided.is_(None))
        ).all()
        
        # Get student's classes (only teacher's classes)
        enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).filter(
            Enrollment.class_id.in_(teacher_class_ids)
        ).all()
        student_classes = {enrollment.class_id: enrollment.class_info for enrollment in enrollments if enrollment.class_info}
        
        # Separate grades by class and find missing/at-risk assignments
        grades_by_class = {}
        
        for g in all_grades:
            try:
                # Ensure assignment relationship is loaded
                if not g.assignment:
                    continue
                
                if not g.assignment.class_info:
                    continue
                
                class_id = g.assignment.class_id
                if class_id not in grades_by_class:
                    grades_by_class[class_id] = []
                grades_by_class[class_id].append(g)
                
                # Parse grade data
                if not g.grade_data:
                    score = None
                else:
                    try:
                        grade_data = json.loads(g.grade_data)
                        score = grade_data.get('score')
                    except (json.JSONDecodeError, TypeError):
                        score = None
                
                # Check if assignment is past due or failing
                is_overdue = g.assignment.due_date and g.assignment.due_date < datetime.utcnow()
                
                # Determine if this is truly at-risk
                is_at_risk = False
                status = None
                
                if score is None:
                    if is_overdue:
                        is_at_risk = True
                        status = 'missing'
                elif score <= 69:
                    is_at_risk = True
                    status = 'failing'
                    at_risk_grades_list.append(g)
                
                if is_at_risk:
                    class_name = g.assignment.class_info.name
                    
                    if class_name not in missing_assignments_by_class:
                        missing_assignments_by_class[class_name] = []
                    
                    missing_assignments_by_class[class_name].append({
                        'title': g.assignment.title,
                        'due_date': g.assignment.due_date.strftime('%Y-%m-%d') if g.assignment.due_date else 'No due date',
                        'status': status,
                        'score': score if score is not None else 'N/A'
                    })
                        
            except Exception as e:
                print(f"Error processing grade {g.id}: {e}")
                continue

        # Calculate Current Overall GPA
        if all_grades:
            try:
                current_gpa = calculate_student_gpa(all_grades)
                print(f"[Teacher Details] Calculated current GPA: {current_gpa}")
            except Exception as e:
                print(f"[Teacher Details] Error calculating current GPA: {e}")
                current_gpa = None

        # Calculate Hypothetical Overall GPA
        hypothetical_grades = []
        for g in all_grades:
            if g in at_risk_grades_list:
                hypothetical_grade = copy(g)
                try:
                    grade_data = json.loads(g.grade_data)
                    grade_data['score'] = 70
                    hypothetical_grade.grade_data = json.dumps(grade_data)
                    hypothetical_grades.append(hypothetical_grade)
                except (json.JSONDecodeError, TypeError):
                    hypothetical_grades.append(g)
            else:
                hypothetical_grades.append(g)
        
        if hypothetical_grades:
            try:
                hypothetical_gpa = calculate_student_gpa(hypothetical_grades)
                print(f"[Teacher Details] Calculated hypothetical GPA: {hypothetical_gpa}")
            except Exception as e:
                print(f"[Teacher Details] Error calculating hypothetical GPA: {e}")
                hypothetical_gpa = None

        # Calculate GPA per class
        class_gpa_data = {}
        for class_id, class_grades in grades_by_class.items():
            if class_id in student_classes:
                class_obj = student_classes[class_id]
                class_name = class_obj.name
                
                try:
                    class_current_gpa = calculate_student_gpa(class_grades) if class_grades else None
                except Exception as e:
                    print(f"[Teacher Details] Error calculating GPA for class {class_name}: {e}")
                    class_current_gpa = None
                
                # Calculate hypothetical GPA for this class
                class_at_risk = [g for g in class_grades if g in at_risk_grades_list]
                class_hypothetical_grades = []
                for g in class_grades:
                    if g in class_at_risk:
                        hypothetical_grade = copy(g)
                        try:
                            grade_data = json.loads(g.grade_data)
                            grade_data['score'] = 70
                            hypothetical_grade.grade_data = json.dumps(grade_data)
                            class_hypothetical_grades.append(hypothetical_grade)
                        except (json.JSONDecodeError, TypeError):
                            class_hypothetical_grades.append(g)
                    else:
                        class_hypothetical_grades.append(g)
                
                try:
                    class_hypothetical_gpa = calculate_student_gpa(class_hypothetical_grades) if class_hypothetical_grades else None
                except Exception as e:
                    print(f"[Teacher Details] Error calculating hypothetical GPA for class {class_name}: {e}")
                    class_hypothetical_gpa = None
                
                class_gpa_data[class_name] = {
                    'current': class_current_gpa,
                    'hypothetical': class_hypothetical_gpa
                }

        # Ensure we always return valid data
        response_data = {
            'success': True,
            'student': {
                'name': f"{student.first_name} {student.last_name}",
                'student_id': student.id,
                'current_gpa': current_gpa if current_gpa is not None else 0.0,
                'hypothetical_gpa': hypothetical_gpa if hypothetical_gpa is not None else 0.0,
                'missing_assignments': missing_assignments_by_class if missing_assignments_by_class else {},
                'class_gpa': class_gpa_data if class_gpa_data else {}
            }
        }
        
        print(f"[Teacher Details] Returning success response for {student.first_name} {student.last_name}")
        print(f"[Teacher Details] Missing assignments: {len(missing_assignments_by_class)} classes")
        print(f"[Teacher Details] Current GPA: {current_gpa}, Hypothetical: {hypothetical_gpa}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in teacher view_student_details_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'details': traceback.format_exc()
        }), 500


@bp.route('/student/<int:student_id>/grades')
@login_required
@teacher_required
def student_grades_report(student_id):
    """View printable student grades report."""
    from models import GroupAssignment, GroupGrade, AcademicPeriod, QuarterGrade
    from utils.quarter_grade_calculator import get_quarter_grades_for_report
    
    student = Student.query.get_or_404(student_id)
    teacher = get_teacher_or_admin()
    
    # Verify teacher has access to this student
    if not is_admin():
        if teacher is None:
            flash("You are not authorized to view this student's grades.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
        
        # Check if student is enrolled in any of teacher's classes
        teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in teacher_classes]
        
        student_enrollments = Enrollment.query.filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active == True
        ).all()
        
        if not student_enrollments:
            flash("You are not authorized to view this student's grades.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get active school year
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        flash('No active school year found.', 'error')
        return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get student's enrolled classes
    enrollments = Enrollment.query.filter_by(
        student_id=student_id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == school_year.id
    ).all()
    
    # Get quarter grades for report
    class_ids = [e.class_id for e in enrollments]
    grades_by_quarter = get_quarter_grades_for_report(
        student_id=student_id,
        school_year_id=school_year.id,
        class_ids=class_ids if class_ids else None
    )
    
    # Get class objects
    class_objects = [e.class_info for e in enrollments if e.class_info]
    
    # Format student data
    student_data = {
        'id': student.id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'grade_level': student.grade_level,
        'student_id': student.student_id or 'N/A',
        'date_of_birth': student.dob or 'N/A',
        'address': student.address or (f"{student.street or ''}, {student.city or ''}, {student.state or ''} {student.zip_code or ''}").strip(' ,') if (student.street or student.city) else 'N/A' or (f"{student.street or ''}, {student.city or ''}, {student.state or ''} {student.zip_code or ''}").strip(' ,') if (student.street or student.city) else 'N/A'
    }
    
    return render_template('teachers/student_grades_report.html',
                         student=student_data,
                         grades_by_quarter=grades_by_quarter,
                         class_objects=class_objects,
                         school_year=school_year,
                         generated_date=datetime.utcnow())


@bp.route('/student/<int:student_id>/grades/pdf')
@login_required
@teacher_required
def student_grades_report_pdf(student_id):
    """Generate PDF of student grades report."""
    from weasyprint import HTML
    from io import BytesIO
    from flask import make_response
    from models import GroupAssignment, GroupGrade, AcademicPeriod
    from utils.quarter_grade_calculator import get_quarter_grades_for_report
    import os
    
    student = Student.query.get_or_404(student_id)
    teacher = get_teacher_or_admin()
    
    # Verify teacher has access
    if not is_admin():
        if teacher is None:
            flash("You are not authorized to view this student's grades.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
        
        teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in teacher_classes]
        
        student_enrollments = Enrollment.query.filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active == True
        ).all()
        
        if not student_enrollments:
            flash("You are not authorized to view this student's grades.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get active school year
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        flash('No active school year found.', 'error')
        return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get enrollments
    enrollments = Enrollment.query.filter_by(
        student_id=student_id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == school_year.id
    ).all()
    
    class_ids = [e.class_id for e in enrollments]
    grades_by_quarter = get_quarter_grades_for_report(
        student_id=student_id,
        school_year_id=school_year.id,
        class_ids=class_ids if class_ids else None
    )
    
    class_objects = [e.class_info for e in enrollments if e.class_info]
    
    student_data = {
        'id': student.id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'grade_level': student.grade_level,
        'student_id': student.student_id or 'N/A',
        'date_of_birth': student.dob or 'N/A',
        'address': student.address or (f"{student.street or ''}, {student.city or ''}, {student.state or ''} {student.zip_code or ''}").strip(' ,') if (student.street or student.city) else 'N/A'
    }
    
    # Render HTML template
    html_content = render_template('teachers/student_grades_report_pdf.html',
                                  student=student_data,
                                  grades_by_quarter=grades_by_quarter,
                                  class_objects=class_objects,
                                  school_year=school_year,
                                  generated_date=datetime.utcnow())
    
    # Inject CSS
    css_path = os.path.join(current_app.root_path, 'static', 'report_card_styles.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        html_content = html_content.replace('</head>', f'<style>{css_content}</style></head>')
    except Exception as e:
        current_app.logger.warning(f"Could not load CSS file: {e}")
    
    # Generate PDF
    html_doc = HTML(string=html_content)
    pdf_bytes = html_doc.write_pdf()
    
    # Create response
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="grades_report_{student.last_name}_{student.first_name}_{school_year.name}.pdf"'
    
    return response


@bp.route('/student/<int:student_id>/attendance')
@login_required
@teacher_required
def student_attendance_report(student_id):
    """View printable student attendance report."""
    from dateutil.relativedelta import relativedelta
    
    student = Student.query.get_or_404(student_id)
    teacher = get_teacher_or_admin()
    
    # Verify teacher has access
    if not is_admin():
        if teacher is None:
            flash("You are not authorized to view this student's attendance.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
        
        teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in teacher_classes]
        
        student_enrollments = Enrollment.query.filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active == True
        ).all()
        
        if not student_enrollments:
            flash("You are not authorized to view this student's attendance.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get active school year
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        flash('No active school year found.', 'error')
        return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get all attendance records for this student in this school year
    attendance_records = Attendance.query.filter_by(
        student_id=student_id
    ).join(Class, Attendance.class_id == Class.id).filter(
        Class.school_year_id == school_year.id
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate statistics
    total_records = len(attendance_records)
    present_count = sum(1 for r in attendance_records if r.status and r.status.lower() == 'present')
    late_count = sum(1 for r in attendance_records if r.status and r.status.lower() == 'late')
    absent_count = sum(1 for r in attendance_records if r.status and r.status.lower() in ['absent', 'unexcused absence', 'excused absence'])
    excused_absent_count = sum(1 for r in attendance_records if r.status and 'excused' in r.status.lower())
    unexcused_absent_count = sum(1 for r in attendance_records if r.status and 'unexcused' in r.status.lower())
    
    attendance_rate = round((present_count / total_records * 100) if total_records > 0 else 0, 1)
    
    # Group by month
    records_by_month = {}
    for record in attendance_records:
        month_key = record.date.strftime('%Y-%m')
        if month_key not in records_by_month:
            records_by_month[month_key] = []
        records_by_month[month_key].append(record)
    
    # Format student data
    student_data = {
        'id': student.id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'grade_level': student.grade_level,
        'student_id': student.student_id or 'N/A',
        'date_of_birth': student.dob or 'N/A'
    }
    
    return render_template('teachers/student_attendance_report.html',
                         student=student_data,
                         attendance_records=attendance_records,
                         records_by_month=records_by_month,
                         school_year=school_year,
                         total_records=total_records,
                         present_count=present_count,
                         late_count=late_count,
                         absent_count=absent_count,
                         excused_absent_count=excused_absent_count,
                         unexcused_absent_count=unexcused_absent_count,
                         attendance_rate=attendance_rate,
                         generated_date=datetime.utcnow())


@bp.route('/student/<int:student_id>/attendance/pdf')
@login_required
@teacher_required
def student_attendance_report_pdf(student_id):
    """Generate PDF of student attendance report."""
    from weasyprint import HTML
    from io import BytesIO
    from flask import make_response
    import os
    
    student = Student.query.get_or_404(student_id)
    teacher = get_teacher_or_admin()
    
    # Verify teacher has access
    if not is_admin():
        if teacher is None:
            flash("You are not authorized to view this student's attendance.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
        
        teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in teacher_classes]
        
        student_enrollments = Enrollment.query.filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active == True
        ).all()
        
        if not student_enrollments:
            flash("You are not authorized to view this student's attendance.", "danger")
            return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get active school year
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        flash('No active school year found.', 'error')
        return redirect(url_for('teacher.dashboard.my_students'))
    
    # Get attendance records
    attendance_records = Attendance.query.filter_by(
        student_id=student_id
    ).join(Class, Attendance.class_id == Class.id).filter(
        Class.school_year_id == school_year.id
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate statistics
    total_records = len(attendance_records)
    present_count = sum(1 for r in attendance_records if r.status and r.status.lower() == 'present')
    late_count = sum(1 for r in attendance_records if r.status and r.status.lower() == 'late')
    absent_count = sum(1 for r in attendance_records if r.status and r.status.lower() in ['absent', 'unexcused absence', 'excused absence'])
    excused_absent_count = sum(1 for r in attendance_records if r.status and 'excused' in r.status.lower())
    unexcused_absent_count = sum(1 for r in attendance_records if r.status and 'unexcused' in r.status.lower())
    
    attendance_rate = round((present_count / total_records * 100) if total_records > 0 else 0, 1)
    
    # Group by month
    records_by_month = {}
    for record in attendance_records:
        month_key = record.date.strftime('%Y-%m')
        if month_key not in records_by_month:
            records_by_month[month_key] = []
        records_by_month[month_key].append(record)
    
    student_data = {
        'id': student.id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'grade_level': student.grade_level,
        'student_id': student.student_id or 'N/A',
        'date_of_birth': student.dob or 'N/A'
    }
    
    # Render HTML template
    html_content = render_template('teachers/student_attendance_report_pdf.html',
                                  student=student_data,
                                  attendance_records=attendance_records,
                                  records_by_month=records_by_month,
                                  school_year=school_year,
                                  total_records=total_records,
                                  present_count=present_count,
                                  late_count=late_count,
                                  absent_count=absent_count,
                                  excused_absent_count=excused_absent_count,
                                  unexcused_absent_count=unexcused_absent_count,
                                  attendance_rate=attendance_rate,
                                  generated_date=datetime.utcnow())
    
    # Inject CSS
    css_path = os.path.join(current_app.root_path, 'static', 'report_card_styles.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        html_content = html_content.replace('</head>', f'<style>{css_content}</style></head>')
    except Exception as e:
        current_app.logger.warning(f"Could not load CSS file: {e}")
    
    # Generate PDF
    html_doc = HTML(string=html_content)
    pdf_bytes = html_doc.write_pdf()
    
    # Create response
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="attendance_report_{student.last_name}_{student.first_name}_{school_year.name}.pdf"'
    
    return response

