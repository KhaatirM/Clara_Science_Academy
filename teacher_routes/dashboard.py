"""
Dashboard and overview routes for teachers.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, Student, Grade, Submission, 
    Notification, Announcement, Enrollment, Attendance, SchoolYear, User, TeacherStaff
)
from sqlalchemy import or_, and_
import json
from datetime import datetime, timedelta
from google_classroom_service import get_google_service
from googleapiclient.errors import HttpError

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
            'link': url_for('teacher.grading.grade_assignment', assignment_id=submission.assignment_id)
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
                'link': url_for('teacher.grading.grade_assignment', assignment_id=grade.assignment_id)
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

