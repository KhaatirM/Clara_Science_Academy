# Standard library imports
import os
import json
from datetime import datetime, timedelta

# Core Flask imports
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort, jsonify, send_file
from flask_login import login_required, current_user

# Database and model imports - organized by category
from models import (
    # Core database
    db,
    # User models
    Student, User, TeacherStaff,
    # Academic structure
    Class, SchoolYear, AcademicPeriod, Enrollment, ClassSchedule,
    # Assignment system
    Assignment, AssignmentRedo, Submission, Grade, StudentGoal,
    # Group assignment system
    GroupAssignment, GroupGrade, StudentGroup, GroupSubmission, StudentGroupMember,
    # Quiz system
    QuizQuestion, QuizOption, QuizAnswer, QuizProgress,
    # Communication system
    Announcement, Notification, Message, MessageGroup, MessageGroupMember,
    # Attendance system
    Attendance,
    # Discussion system
    DiscussionThread, DiscussionPost
)

# Authentication and decorators
from decorators import student_required

# Werkzeug utilities
from werkzeug.utils import secure_filename

student_blueprint = Blueprint('student', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx', 'pptx', 'md'}

def allowed_file(filename):
    """Checks if the file's extension is in the allowed set."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_gpa(grades):
    """Calculate GPA from a list of grade percentages."""
    if not grades:
        return 0.0
    
    # Convert percentage to 4.0 scale
    def percentage_to_gpa(percentage):
        # Ensure percentage is a number
        try:
            percentage = float(percentage)
        except (ValueError, TypeError):
            return 0.0
        
        if percentage >= 93: return 4.0
        elif percentage >= 90: return 3.7
        elif percentage >= 87: return 3.3
        elif percentage >= 83: return 3.0
        elif percentage >= 80: return 2.7
        elif percentage >= 77: return 2.3
        elif percentage >= 73: return 2.0
        elif percentage >= 70: return 1.7
        elif percentage >= 67: return 1.3
        elif percentage >= 63: return 1.0
        elif percentage >= 60: return 0.7
        else: return 0.0
    
    gpa_points = [percentage_to_gpa(grade) for grade in grades]
    return round(sum(gpa_points) / len(gpa_points), 2) if gpa_points else 0.0

def get_student_assignment_status(assignment, submission, grade, student_id=None):
    """Determine the student-facing status for an assignment."""
    from datetime import datetime
    
    # Check if assignment is voided
    if assignment.status == 'Voided':
        return 'Voided'
    
    # Check if the student's grade is voided
    if grade and grade.is_voided:
        return 'Voided'
    
    # Check if assignment has an active extension for this student (before checking graded status)
    if student_id:
        from models import AssignmentExtension
        extension = AssignmentExtension.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True
        ).first()
        
        if extension:
            # Check if extension deadline has passed and assignment is not graded
            if not grade:
                extension_due_date = extension.extended_due_date.date() if hasattr(extension.extended_due_date, 'date') else extension.extended_due_date
                today = datetime.now().date()
                
                if extension_due_date >= today:
                    # Extension is still active
                    return 'Extended'
                else:
                    # Extension deadline has passed and not graded
                    return 'Past Due'
    
    # Check if assignment has been graded - this takes priority over due date
    if grade:
        return 'completed'
    
    # Check if assignment has been submitted
    if submission:
        return 'Submitted or Awaiting Grade'
    
    # Check if assignment is past due (only if not completed/submitted)
    if assignment.due_date:
        # Convert due_date to date if it's a datetime for comparison
        due_date = assignment.due_date.date() if hasattr(assignment.due_date, 'date') else assignment.due_date
        today = datetime.now().date()
        if due_date < today:
            return 'Past Due'
    
    # Default status for active assignments
    return 'Un-Submitted'

def get_grade_trends(student_id, class_id, limit=10):
    """Get grade trends for a specific class."""
    # Get grades directly from the Grade model, excluding Voided assignments and voided grades
    grades = Grade.query.join(Assignment).filter(
        Grade.student_id == student_id,
        Assignment.class_id == class_id,
        Assignment.status != 'Voided',  # Exclude Voided assignments from grade trends
        Grade.is_voided == False  # Exclude voided grades
    ).order_by(Grade.graded_at.desc()).limit(limit).all()
    
    trends = []
    for grade in reversed(grades):  # Reverse to show chronological order
        # Skip voided grades (double check)
        if grade.is_voided or grade.assignment.status == 'Voided':
            continue
            
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            if 'score' in grade_data and grade_data.get('score') is not None:
                trends.append({
                    'assignment': grade.assignment.title,
                    'grade': grade_data['score'],
                    'date': grade.graded_at.strftime('%Y-%m-%d')
                })
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue  # Skip invalid grade data
    
    return trends

def get_letter_grade(percentage):
    """Convert percentage to letter grade."""
    # Ensure percentage is a number
    try:
        percentage = float(percentage)
    except (ValueError, TypeError):
        return 'F'  # Return F for invalid percentages
    
    if percentage >= 93:
        return 'A'
    elif percentage >= 90:
        return 'A-'
    elif percentage >= 87:
        return 'B+'
    elif percentage >= 83:
        return 'B'
    elif percentage >= 80:
        return 'B-'
    elif percentage >= 77:
        return 'C+'
    elif percentage >= 73:
        return 'C'
    elif percentage >= 70:
        return 'C-'
    elif percentage >= 67:
        return 'D+'
    elif percentage >= 63:
        return 'D'
    elif percentage >= 60:
        return 'D-'
    else:
        return 'F'

def create_template_context(student, section, active_tab, **kwargs):
    """Helper function to create common template context."""
    base_context = {
        'student': student,
        'classes': kwargs.get('classes', []),
        'grades': kwargs.get('grades', {}),
        'attendance_summary': kwargs.get('attendance_summary', {}),
        'grades_by_class': kwargs.get('grades_by_class', {}),
        'gpa': kwargs.get('gpa', 0.0),
        'grade_trends': kwargs.get('grade_trends', {}),
        'today_schedule': kwargs.get('today_schedule', []),
        'goals': kwargs.get('goals', {}),
        'announcements': kwargs.get('announcements', []),
        'notifications': kwargs.get('notifications', []),
        'past_due_assignments': kwargs.get('past_due_assignments', []),
        'upcoming_assignments': kwargs.get('upcoming_assignments', []),
        'recent_grades': kwargs.get('recent_grades', []),
        'section': section,
        'active_tab': active_tab,
        'get_letter_grade': get_letter_grade,
        'calculate_gpa': calculate_gpa
    }
    
    # Add any additional kwargs to the context
    base_context.update(kwargs)
    
    return base_context

@student_blueprint.route('/submit-360-feedback', methods=['POST'])
@login_required
@student_required
def submit_360_feedback():
    """Handle 360 degree feedback submission"""
    student = Student.query.get_or_404(current_user.student_id)
    
    try:
        from models import Feedback360Response
        
        feedback360_id = request.form.get('feedback360_id')
        feedback_data = request.form.get('feedback_data')
        is_anonymous = request.form.get('is_anonymous') == 'true'
        
        # Create new response
        new_response = Feedback360Response(
            feedback360_id=int(feedback360_id),
            respondent_id=student.id,
            respondent_type='peer',  # Could be peer, self, or teacher
            feedback_data=feedback_data,
            is_anonymous=is_anonymous
        )
        
        db.session.add(new_response)
        db.session.commit()
        
        flash('360° Feedback submitted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting feedback: {str(e)}', 'error')
    
    return redirect(url_for('student.student_submissions'))

@student_blueprint.route('/submit-reflection-journal', methods=['POST'])
@login_required
@student_required
def submit_reflection_journal():
    """Handle reflection journal submission"""
    student = Student.query.get_or_404(current_user.student_id)
    
    try:
        from models import ReflectionJournal
        
        group_assignment_id = request.form.get('group_assignment_id')
        group_id = request.form.get('group_id')
        reflection_text = request.form.get('reflection_text')
        collaboration_rating = request.form.get('collaboration_rating')
        learning_rating = request.form.get('learning_rating')
        challenges_faced = request.form.get('challenges_faced', '')
        lessons_learned = request.form.get('lessons_learned', '')
        
        # Create new journal
        new_journal = ReflectionJournal(
            student_id=student.id,
            group_id=int(group_id),
            group_assignment_id=int(group_assignment_id),
            reflection_text=reflection_text,
            collaboration_rating=int(collaboration_rating),
            learning_rating=int(learning_rating),
            challenges_faced=challenges_faced,
            lessons_learned=lessons_learned
        )
        
        db.session.add(new_journal)
        db.session.commit()
        
        flash('Reflection journal submitted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting journal: {str(e)}', 'error')
    
    return redirect(url_for('student.student_submissions'))

@student_blueprint.route('/submit-conflict-report', methods=['POST'])
@login_required
@student_required
def submit_conflict_report():
    """Handle conflict report submission"""
    student = Student.query.get_or_404(current_user.student_id)
    
    try:
        from models import GroupConflict
        
        group_assignment_id = request.form.get('group_assignment_id')
        group_id = request.form.get('group_id')
        conflict_type = request.form.get('conflict_type')
        severity_level = request.form.get('severity_level')
        conflict_description = request.form.get('conflict_description')
        
        # Create new conflict report
        new_conflict = GroupConflict(
            group_id=int(group_id),
            group_assignment_id=int(group_assignment_id),
            reported_by=student.id,
            conflict_type=conflict_type,
            conflict_description=conflict_description,
            severity_level=severity_level,
            status='reported'
        )
        
        db.session.add(new_conflict)
        db.session.commit()
        
        flash('Conflict report submitted successfully! Your teacher will review it.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting conflict report: {str(e)}', 'error')
    
    return redirect(url_for('student.student_submissions'))

@student_blueprint.route('/submissions')
@login_required
@student_required
def student_submissions():
    """Student submissions page for 360 feedback, journals, and conflicts"""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Initialize empty lists as defaults
    feedback_submissions = []
    journal_submissions = []
    conflict_reports = []
    available_feedback_sessions = []
    student_group_assignments = []
    
    # Get current school year
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    # Try to get student's feedback submissions
    try:
        from models import Feedback360Response, Feedback360
        feedback_submissions = Feedback360Response.query.filter_by(respondent_id=student.id).order_by(Feedback360Response.submitted_at.desc()).all()
        
        # Get available active feedback sessions for student's classes
        if current_school_year:
            enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
            class_ids = [e.class_id for e in enrollments]
            available_feedback_sessions = Feedback360.query.filter(
                Feedback360.class_id.in_(class_ids),
                Feedback360.is_active == True
            ).all()
    except Exception as e:
        current_app.logger.warning(f"Could not load feedback submissions: {e}")
    
    # Try to get student's reflection journals
    try:
        from models import ReflectionJournal, StudentGroupMember, GroupAssignment
        journal_submissions = ReflectionJournal.query.filter_by(student_id=student.id).order_by(ReflectionJournal.submitted_at.desc()).all()
        
        # Get student's group assignments
        group_memberships = StudentGroupMember.query.filter_by(student_id=student.id).all()
        for membership in group_memberships:
            group = membership.group
            if group and group.class_id:
                # Get group assignments for this group's class
                assignments = GroupAssignment.query.filter_by(class_id=group.class_id).all()
                for assignment in assignments:
                    student_group_assignments.append({
                        'id': assignment.id,
                        'title': assignment.title,
                        'class_name': group.class_info.name if group.class_info else 'Unknown Class',
                        'group_id': group.id
                    })
    except Exception as e:
        current_app.logger.warning(f"Could not load reflection journals: {e}")
    
    # Try to get student's conflict reports
    try:
        from models import GroupConflict
        conflict_reports = GroupConflict.query.filter_by(reported_by=student.id).order_by(GroupConflict.reported_at.desc()).all()
    except Exception as e:
        current_app.logger.warning(f"Could not load conflict reports: {e}")
    
    return render_template('students/student_submissions.html',
                         student=student,
                         feedback_submissions=feedback_submissions,
                         journal_submissions=journal_submissions,
                         conflict_reports=conflict_reports,
                         available_feedback_sessions=available_feedback_sessions,
                         student_group_assignments=student_group_assignments)

@student_blueprint.route('/dashboard')
@login_required
@student_required
def student_dashboard():
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get current school year
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        flash("No active school year found.", "warning")
        return render_template('students/role_student_dashboard.html', 
                             **create_template_context(student, 'home', 'home'))

    # Get student's enrolled classes using the Enrollment model
    enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == current_school_year.id
    ).all()
    
    classes = [enrollment.class_info for enrollment in enrollments]

    # Get grades for each class and calculate GPA
    grades = {}
    grade_trends = {}
    all_grades = []
    
    for c in classes:
        # Get grades for this class
        class_grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student.id,
            Assignment.class_id == c.id,
            Assignment.school_year_id == current_school_year.id
        ).all()
        
        if class_grades:
            # Calculate average grade for this class
            grade_percentages = []
            for g in class_grades:
                grade_data = json.loads(g.grade_data)
                if 'score' in grade_data and grade_data['score'] is not None:
                    try:
                        # Convert to float in case it's stored as string
                        score = float(grade_data['score'])
                        grade_percentages.append(score)
                    except (ValueError, TypeError):
                        continue  # Skip invalid scores
            
            if grade_percentages:
                avg_grade = round(sum(grade_percentages) / len(grade_percentages), 2)
                grades[c.name] = avg_grade
                all_grades.append(avg_grade)
                
                # Get grade trends for this class
                grade_trends[c.id] = get_grade_trends(student.id, c.id)
    
    # Calculate overall GPA
    gpa = calculate_gpa(all_grades)
    
    # Get student goals
    goals = StudentGoal.query.filter_by(student_id=student.id).all()
    goals_dict = {goal.class_id: goal for goal in goals}
    
    # Get today's schedule using real ClassSchedule data
    today = datetime.now()
    today_weekday = today.weekday()  # 0=Monday, 1=Tuesday, etc.
    today_schedule = []
    
    for c in classes:
        # Get schedule for this class on today's weekday
        schedule = ClassSchedule.query.filter_by(
            class_id=c.id,
            day_of_week=today_weekday
        ).first()
        
        if schedule:
            today_schedule.append({
                'class': c,
                'time': f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}",
                'room': schedule.room or 'TBD',
                'teacher': c.teacher.first_name + ' ' + c.teacher.last_name if c.teacher else 'TBD'
            })
    
    # Sort by start time
    today_schedule.sort(key=lambda x: x['class'].id)  # Sort by class ID for now

    # Get real attendance summary from Attendance model
    attendance_records = Attendance.query.filter_by(
        student_id=student.id
    ).filter(
        Attendance.date >= current_school_year.start_date,
        Attendance.date <= current_school_year.end_date
    ).all()
    
    attendance_summary = {
        'Present': len([r for r in attendance_records if r.status == 'Present']),
        'Tardy': len([r for r in attendance_records if r.status == 'Tardy']),
        'Absent': len([r for r in attendance_records if r.status == 'Absent']),
    }

    # Get notifications for the current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).limit(10).all()

    # Get assignments for the student's enrolled classes only
    class_ids = [c.id for c in classes]
    assignments = Assignment.query.filter(
        Assignment.class_id.in_(class_ids),
        Assignment.school_year_id == current_school_year.id,
        Assignment.status == 'Active'  # Only show Active assignments to students
    ).all()
    
    past_due_assignments = []
    upcoming_assignments = []
    recent_grades = []
    
    for assignment in assignments:
        # Get submission and grade status to check if completed
        submission = Submission.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
        grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
        
        # Only check due dates for non-completed assignments
        if assignment.due_date and not grade:  # Not completed if no grade
            # Convert due_date to date if it's a datetime
            due_date = assignment.due_date.date() if hasattr(assignment.due_date, 'date') else assignment.due_date
            # Ensure today is also a date object for comparison
            today_date = today.date() if hasattr(today, 'date') else today
            if due_date < today_date:
                past_due_assignments.append(assignment)
            # Check if upcoming (due within 7 days)
            elif due_date <= today_date + timedelta(days=7):
                upcoming_assignments.append(assignment)
    
    # Get recent grades for enrolled classes only, excluding Voided assignments
    recent_grades_raw = Grade.query.filter_by(student_id=student.id).join(Assignment).filter(
        Assignment.class_id.in_(class_ids),
        Assignment.status != 'Voided'  # Exclude Voided assignments from recent grades
    ).order_by(Grade.graded_at.desc()).limit(5).all()
    
    # Format recent grades for template (excluding voided grades and voided assignments)
    recent_grades = []
    for grade in recent_grades_raw:
        # Skip voided grades and voided assignments
        if grade.is_voided or grade.assignment.status == 'Voided':
            continue
            
        grade_data = json.loads(grade.grade_data)
        recent_grades.append({
            'assignment': grade.assignment,
            'class_name': grade.assignment.class_info.name,
            'score': grade_data.get('score', 'N/A')
        })
    
    # Announcements: all students, all, or for any of their classes
    announcements = Announcement.query.filter(
        (Announcement.target_group.in_(['all_students', 'all'])) |
        ((Announcement.target_group == 'class') & (Announcement.class_id.in_(class_ids)))
    ).order_by(Announcement.timestamp.desc()).all()

    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'home', 'home',
                            grades=grades, 
                            attendance_summary=attendance_summary,
                             announcements=announcements,
                             notifications=notifications,
                             school_year=current_school_year,
                             past_due_assignments=past_due_assignments,
                             upcoming_assignments=upcoming_assignments,
                             recent_grades=recent_grades,
                             gpa=gpa,
                             grade_trends=grade_trends,
                             today_schedule=today_schedule,
                             goals=goals_dict,
                             classes=classes,
                             today=datetime.now().date()))

@student_blueprint.route('/assignments')
@login_required
@student_required
def student_assignments():
    student = Student.query.get_or_404(current_user.student_id)
    from datetime import datetime
    
    # Get current school year
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        flash("No active school year found.", "warning")
        return render_template('students/role_student_dashboard.html', 
                             **create_template_context(student, 'assignments', 'assignments'))
    
    # Get student's enrolled classes
    enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == current_school_year.id
    ).all()
    
    classes = [enrollment.class_info for enrollment in enrollments]
    class_ids = [enrollment.class_id for enrollment in enrollments]
    
    # Check if a specific class is requested via query parameter
    requested_class_id = request.args.get('class_id')
    if requested_class_id:
        # Redirect to the proper class-specific route
        return redirect(url_for('student.class_assignments', class_id=requested_class_id))
    
    # Get assignments for student's classes (show Active and Inactive assignments to students)
    assignments = Assignment.query.filter(
        Assignment.class_id.in_(class_ids),
        Assignment.school_year_id == current_school_year.id,
        Assignment.status.in_(['Active', 'Inactive'])  # Show both Active and Inactive assignments
    ).order_by(Assignment.due_date.asc()).all()
    
    # Get all submissions for this student
    submissions = Submission.query.filter_by(student_id=student.id).all()
    submissions_dict = {sub.assignment_id: sub for sub in submissions}
    
    # Get all grades for this student
    grades = Grade.query.filter_by(student_id=student.id).all()
    grades_dict = {g.assignment_id: g for g in grades}
    
    # Get redo opportunities for this student
    redo_opportunities = AssignmentRedo.query.filter_by(
        student_id=student.id,
        is_used=False
    ).join(Assignment).filter(
        Assignment.assignment_type.in_(['PDF', 'Paper', 'pdf', 'paper'])
    ).all()
    
    # Create assignments with status for template
    assignments_with_status = []
    past_due_assignments = []
    upcoming_assignments = []
    today = datetime.now().date()
    
    for assignment in assignments:
        submission = submissions_dict.get(assignment.id)
        grade = grades_dict.get(assignment.id)
        
        # Determine student-facing status
        student_status = get_student_assignment_status(assignment, submission, grade, student.id)
        
        assignments_with_status.append((assignment, submission, student_status))
        
        # Categorize assignments for alerts (only if not completed)
        if assignment.due_date and student_status not in ['completed', 'Voided']:
            # Convert due_date to date if it's a datetime
            due_date = assignment.due_date.date() if hasattr(assignment.due_date, 'date') else assignment.due_date
            
            if due_date < today:
                past_due_assignments.append(assignment)
            elif due_date <= today + timedelta(days=7):
                upcoming_assignments.append(assignment)
    
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'assignments', 'assignments',
                             assignments_with_status=assignments_with_status,
                             grades=grades_dict,
                             today=today,
                             classes=classes,
                             past_due_assignments=past_due_assignments,
                             upcoming_assignments=upcoming_assignments,
                             redo_opportunities=redo_opportunities))

@student_blueprint.route('/assignments/class/<int:class_id>')
@login_required
@student_required
def class_assignments(class_id):
    """View assignments for a specific class"""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get the class and verify student is enrolled
    class_obj = Class.query.get_or_404(class_id)
    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash("You are not enrolled in this class.", "error")
        return redirect(url_for('student.student_assignments'))
    
    # Get assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get all submissions for this student
    submissions = Submission.query.filter_by(student_id=student.id).all()
    submissions_dict = {sub.assignment_id: sub for sub in submissions}
    
    # Get all grades for this student
    grades = Grade.query.filter_by(student_id=student.id).all()
    grades_dict = {g.assignment_id: g for g in grades}
    
    # Create assignments with status for template
    assignments_with_status = []
    for assignment in assignments:
        submission = submissions_dict.get(assignment.id)
        grade = grades_dict.get(assignment.id)
        
        # Determine student-facing status
        student_status = get_student_assignment_status(assignment, submission, grade, student.id)
        
        assignments_with_status.append((assignment, submission, student_status))
    
    return render_template('students/class_assignments_detail.html',
                         **create_template_context(student, 'assignments', 'assignments',
                             class_obj=class_obj,
                             assignments_with_status=assignments_with_status,
                             today=datetime.now().date()))

@student_blueprint.route('/classes')
@login_required
@student_required
def student_classes():
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get current school year
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        flash("No active school year found.", "warning")
        return render_template('students/role_student_dashboard.html', 
                             **create_template_context(student, 'classes', 'classes'))

    # Get student's enrolled classes using the Enrollment model
    enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == current_school_year.id
    ).all()
    
    classes = [enrollment.class_info for enrollment in enrollments]

    # Get grades for each class and calculate GPA
    grades = {}
    all_grades = []
    
    for c in classes:
        # Get grades for this class
        class_grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student.id,
            Assignment.class_id == c.id,
            Assignment.school_year_id == current_school_year.id
        ).all()
        
        if class_grades:
            # Calculate average grade for this class
            grade_percentages = []
            for g in class_grades:
                # Skip voided grades and voided assignments
                if g.is_voided or g.assignment.status == 'Voided':
                    continue
                    
                try:
                    grade_data = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
                    if 'score' in grade_data and grade_data['score'] is not None:
                        # Convert to float in case it's stored as string
                        score = float(grade_data['score'])
                        grade_percentages.append(score)
                except (ValueError, TypeError, json.JSONDecodeError, AttributeError):
                    continue  # Skip invalid scores
            
            if grade_percentages:
                avg_grade = round(sum(grade_percentages) / len(grade_percentages), 2)
                grades[c.name] = avg_grade
                all_grades.append(avg_grade)
    
    return render_template('students/role_student_dashboard.html',
                          **create_template_context(student, 'classes', 'classes',
                              classes=classes,
                              my_classes=classes,
                              grades=grades))

@student_blueprint.route('/grades')
@login_required
@student_required
def student_grades():
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get active school year
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        flash('No active school year found.', 'error')
        return redirect(url_for('student.student_dashboard'))
    
    # Get academic periods for this school year
    academic_periods = AcademicPeriod.query.filter_by(
        school_year_id=school_year.id,
        is_active=True
    ).order_by(AcademicPeriod.start_date).all()
    
    # Organize periods by type
    quarters = [p for p in academic_periods if p.period_type == 'quarter']
    semesters = [p for p in academic_periods if p.period_type == 'semester']
    
    # Get student's enrolled classes for current school year
    enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == school_year.id
    ).all()
    
    if not enrollments:
        flash('No classes found for current school year.', 'info')
        return render_template('students/role_student_dashboard.html', 
                             **create_template_context(student, 'grades', 'grades'))
    
    # Calculate grades for each class organized by quarters and semesters
    grades_by_class = {}
    all_class_averages = []
    
    for enrollment in enrollments:
        class_info = enrollment.class_info
        
        # Get all assignments for this class (both regular and group assignments)
        assignments = Assignment.query.filter(
            Assignment.class_id == class_info.id,
            Assignment.school_year_id == school_year.id
        ).all()
        
        group_assignments = GroupAssignment.query.filter(
            GroupAssignment.class_id == class_info.id,
            GroupAssignment.school_year_id == school_year.id
        ).all()
        
        if not assignments and not group_assignments:
            continue
        
        # Get all grades for this student in this class (both regular and group grades)
        grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student.id,
            Assignment.class_id == class_info.id,
            Assignment.school_year_id == school_year.id
        ).order_by(Grade.graded_at.desc()).all()
        
        # Get group assignment grades for this student
        group_grades = GroupGrade.query.join(GroupAssignment).filter(
            GroupGrade.student_id == student.id,
            GroupAssignment.class_id == class_info.id,
            GroupAssignment.school_year_id == school_year.id
        ).order_by(GroupGrade.graded_at.desc()).all()
        
        if not grades and not group_grades:
            continue
        
        # Calculate individual assignment grades (including both regular and group assignments)
        assignment_grades = {}
        total_score = 0
        valid_grades = 0
        
        # Process regular assignment grades
        for grade in grades:
            # Skip voided grades and voided assignments
            if grade.is_voided or grade.assignment.status == 'Voided':
                continue
                
            grade_data = json.loads(grade.grade_data)
            if 'score' in grade_data and grade_data['score'] is not None:
                try:
                    score = float(grade_data['score'])  # Convert to float
                    assignment_grades[grade.assignment.title] = f"{score}%"
                    total_score += score
                    valid_grades += 1
                except (ValueError, TypeError):
                    continue  # Skip invalid scores
        
        # Process group assignment grades
        for group_grade in group_grades:
            # Skip voided grades and voided assignments
            if group_grade.is_voided or group_grade.group_assignment.status == 'Voided':
                continue
                
            grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else group_grade.grade_data
            if 'score' in grade_data and grade_data['score'] is not None:
                try:
                    score = float(grade_data['score'])  # Convert to float
                    assignment_grades[group_grade.group_assignment.title] = f"{score}%"
                    total_score += score
                    valid_grades += 1
                except (ValueError, TypeError):
                    continue  # Skip invalid scores
        
        if valid_grades > 0:
            class_average = round(total_score / valid_grades, 2)
            all_class_averages.append(class_average)
            
            # Convert percentage to letter grade
            letter_grade = get_letter_grade(class_average)
            
            # Get recent grades (last 3 assignments - combining regular and group assignments)
            recent_assignments = []
            all_recent_grades = []
            
            # Combine regular and group grades
            for grade in grades:
                # Skip voided grades and voided assignments
                if grade.is_voided or grade.assignment.status == 'Voided':
                    continue
                    
                grade_data = json.loads(grade.grade_data)
                if 'score' in grade_data and grade_data['score'] is not None:
                    try:
                        score = float(grade_data['score'])  # Convert to float
                        all_recent_grades.append({
                            'title': grade.assignment.title,
                            'score': score,
                            'letter': get_letter_grade(score),
                            'graded_at': grade.graded_at
                        })
                    except (ValueError, TypeError):
                        continue  # Skip invalid scores
            
            for group_grade in group_grades:
                # Skip voided grades and voided assignments
                if group_grade.is_voided or group_grade.group_assignment.status == 'Voided':
                    continue
                    
                grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else group_grade.grade_data
                if 'score' in grade_data and grade_data['score'] is not None:
                    try:
                        score = float(grade_data['score'])  # Convert to float
                        all_recent_grades.append({
                            'title': f"{group_grade.group_assignment.title} (Group)",
                            'score': score,
                            'letter': get_letter_grade(score),
                            'graded_at': group_grade.graded_at
                        })
                    except (ValueError, TypeError):
                        continue  # Skip invalid scores
            
            # Sort by graded_at and get last 3
            all_recent_grades.sort(key=lambda x: x['graded_at'], reverse=True)
            for grade_info in all_recent_grades[:3]:
                recent_assignments.append({
                    'title': grade_info['title'],
                    'score': grade_info['score'],
                    'letter': grade_info['letter'],
                    'graded_at': grade_info['graded_at'].strftime('%b %d, %Y')
                })
            
            # Calculate class GPA (convert percentage to 4.0 scale)
            class_gpa = calculate_gpa([class_average])
            
            # Organize grades by quarters and semesters
            quarter_grades = {}
            semester_grades = {}
            
            # Calculate grades for each quarter (including group assignments)
            from datetime import date
            for quarter in quarters:
                # Check if the quarter has ended before calculating grades
                today = date.today()
                if today < quarter.end_date:
                    # Quarter hasn't ended yet, show "In Progress" or similar
                    quarter_grades[quarter.name] = {
                        'average': None,
                        'letter': 'In Progress',
                        'gpa': None,
                        'assignments': 0,
                        'status': 'in_progress',
                        'end_date': quarter.end_date
                    }
                    continue
                
                quarter_assignments = [a for a in assignments if a.quarter == quarter.name]
                quarter_group_assignments = [a for a in group_assignments if a.quarter == quarter.name]
                quarter_grades_list = []
                
                # Add regular assignment grades
                for assignment in quarter_assignments:
                    # Skip voided assignments
                    if assignment.status == 'Voided':
                        continue
                        
                    grade = next((g for g in grades if g.assignment_id == assignment.id), None)
                    if grade and not grade.is_voided:
                        grade_data = json.loads(grade.grade_data)
                        if 'score' in grade_data and grade_data['score'] is not None:
                            try:
                                score = float(grade_data['score'])  # Convert to float
                                quarter_grades_list.append(score)
                            except (ValueError, TypeError):
                                continue  # Skip invalid scores
                
                # Add group assignment grades
                for group_assignment in quarter_group_assignments:
                    # Skip voided assignments
                    if group_assignment.status == 'Voided':
                        continue
                        
                    group_grade = next((g for g in group_grades if g.group_assignment_id == group_assignment.id), None)
                    if group_grade and not group_grade.is_voided:
                        grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else group_grade.grade_data
                        if 'score' in grade_data and grade_data['score'] is not None:
                            try:
                                score = float(grade_data['score'])  # Convert to float
                                quarter_grades_list.append(score)
                            except (ValueError, TypeError):
                                continue  # Skip invalid scores
                
                if quarter_grades_list:
                    quarter_avg = round(sum(quarter_grades_list) / len(quarter_grades_list), 2)
                    quarter_grades[quarter.name] = {
                        'average': quarter_avg,
                        'letter': get_letter_grade(quarter_avg),
                        'gpa': calculate_gpa([quarter_avg]),
                        'assignments': len(quarter_grades_list),
                        'status': 'completed',
                        'end_date': quarter.end_date
                    }
                else:
                    quarter_grades[quarter.name] = {
                        'average': None,
                        'letter': 'No Grades',
                        'gpa': None,
                        'assignments': 0,
                        'status': 'completed',
                        'end_date': quarter.end_date
                    }
            
            # Calculate grades for each semester (including group assignments)
            for semester in semesters:
                # Check if the semester has ended before calculating grades
                today = date.today()
                if today < semester.end_date:
                    # Semester hasn't ended yet, show "In Progress" or similar
                    semester_grades[semester.name] = {
                        'average': None,
                        'letter': 'In Progress',
                        'gpa': None,
                        'assignments': 0,
                        'status': 'in_progress',
                        'end_date': semester.end_date
                    }
                    continue
                
                semester_assignments = []
                semester_group_assignments = []
                
                # Get regular assignments for this semester
                for assignment in assignments:
                    # Determine which semester this assignment belongs to
                    if semester.name == 'S1' and assignment.due_date.date() <= semester.end_date:
                        semester_assignments.append(assignment)
                    elif semester.name == 'S2' and assignment.due_date.date() > semester.start_date:
                        semester_assignments.append(assignment)
                
                # Get group assignments for this semester
                for group_assignment in group_assignments:
                    # Determine which semester this assignment belongs to
                    if semester.name == 'S1' and group_assignment.due_date.date() <= semester.end_date:
                        semester_group_assignments.append(group_assignment)
                    elif semester.name == 'S2' and group_assignment.due_date.date() > semester.start_date:
                        semester_group_assignments.append(group_assignment)
                
                semester_grades_list = []
                
                # Add regular assignment grades
                for assignment in semester_assignments:
                    # Skip voided assignments
                    if assignment.status == 'Voided':
                        continue
                        
                    grade = next((g for g in grades if g.assignment_id == assignment.id), None)
                    if grade and not grade.is_voided:
                        grade_data = json.loads(grade.grade_data)
                        if 'score' in grade_data and grade_data['score'] is not None:
                            try:
                                score = float(grade_data['score'])  # Convert to float
                                semester_grades_list.append(score)
                            except (ValueError, TypeError):
                                continue  # Skip invalid scores
                
                # Add group assignment grades
                for group_assignment in semester_group_assignments:
                    # Skip voided assignments
                    if group_assignment.status == 'Voided':
                        continue
                        
                    group_grade = next((g for g in group_grades if g.group_assignment_id == group_assignment.id), None)
                    if group_grade and not group_grade.is_voided:
                        grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else group_grade.grade_data
                        if 'score' in grade_data and grade_data['score'] is not None:
                            try:
                                score = float(grade_data['score'])  # Convert to float
                                semester_grades_list.append(score)
                            except (ValueError, TypeError):
                                continue  # Skip invalid scores
                
                if semester_grades_list:
                    semester_avg = round(sum(semester_grades_list) / len(semester_grades_list), 2)
                    semester_grades[semester.name] = {
                        'average': semester_avg,
                        'letter': get_letter_grade(semester_avg),
                        'gpa': calculate_gpa([semester_avg]),
                        'assignments': len(semester_grades_list),
                        'status': 'completed',
                        'end_date': semester.end_date
                    }
                else:
                    semester_grades[semester.name] = {
                        'average': None,
                        'letter': 'No Grades',
                        'gpa': None,
                        'assignments': 0,
                        'status': 'completed',
                        'end_date': semester.end_date
                    }
            
            grades_by_class[class_info.name] = {
                'final_grade': {
                    'letter': letter_grade,
                    'percentage': class_average
                },
                'class_gpa': class_gpa,
                'recent_assignments': recent_assignments,
                'quarter_grades': quarter_grades,
                'semester_grades': semester_grades,
                'grades': {
                    'Current': {
                        'overall_letter': letter_grade,
                        'overall_percentage': class_average,
                        'grade_details': assignment_grades
                    }
                }
            }
    
    # Calculate overall GPA
    gpa = calculate_gpa(all_class_averages) if all_class_averages else 0.0
    
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'grades', 'grades',
                             grades_by_class=grades_by_class,
                             gpa=gpa,
                             quarters=quarters,
                             semesters=semesters))
                         
@student_blueprint.route('/schedule')
@login_required
@student_required
def student_schedule():
    student = Student.query.get_or_404(current_user.student_id)
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'schedule', 'schedule'))

@student_blueprint.route('/school-calendar')
@login_required
@student_required
def student_school_calendar():
    """View school calendar (read-only for students)"""
    from datetime import datetime, timedelta
    import calendar as cal
    
    # Get current month/year from query params or use current date
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Calculate previous and next month
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    
    # Create calendar data
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')
    
    # Get academic dates for this month
    academic_dates = get_academic_dates_for_calendar(year, month)
    
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
                
                # Get events for this day
                day_events = []
                for academic_date in academic_dates:
                    if academic_date['day'] == day:
                        day_events.append({
                            'title': academic_date['title'],
                            'category': academic_date['category']
                        })
                
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': day_events})
        calendar_data['weeks'].append(week_data)

    return render_template('shared/calendar.html',
                         calendar_data=calendar_data,
                         prev_month=prev_month,
                         next_month=next_month,
                         month_name=month_name,
                         year=year,
                         section='calendar',
                         active_tab='calendar')

def get_academic_dates_for_calendar(year, month):
    """Get academic dates (quarters, semesters, holidays) for a specific month/year."""
    from datetime import date, timedelta
    from models import SchoolYear, AcademicPeriod, CalendarEvent, TeacherWorkDay, SchoolBreak
    
    academic_dates = []
    
    # Get the active school year
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        return academic_dates
    
    # Get academic periods for this month
    start_of_month = date(year, month, 1)
    if month == 12:
        end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get academic periods that overlap with this month
    academic_periods = AcademicPeriod.query.filter(
        AcademicPeriod.school_year_id == active_year.id,
        AcademicPeriod.start_date <= end_of_month,
        AcademicPeriod.end_date >= start_of_month
    ).all()
    
    for period in academic_periods:
        # Add start date event
        if period.start_date.month == month:
            event_type = f"{period.period_type}_start"  # quarter_start, semester_start
            academic_dates.append({
                'day': period.start_date.day,
                'title': f"{period.name} Start",
                'category': f"{period.period_type.title()}",
                'type': event_type
            })
        
        # Add end date event
        if period.end_date.month == month:
            event_type = f"{period.period_type}_end"  # quarter_end, semester_end
            academic_dates.append({
                'day': period.end_date.day,
                'title': f"{period.name} End",
                'category': f"{period.period_type.title()}",
                'type': event_type
            })
    
    # Get calendar events for this month
    calendar_events = CalendarEvent.query.filter(
        CalendarEvent.school_year_id == active_year.id,
        CalendarEvent.start_date <= end_of_month,
        CalendarEvent.end_date >= start_of_month
    ).all()
    
    for event in calendar_events:
        if event.start_date.month == month:
            # Use the actual event_type from the database, or default to 'other_event'
            event_type = event.event_type if event.event_type else 'other_event'
            academic_dates.append({
                'day': event.start_date.day,
                'title': event.name,
                'category': event.event_type.replace('_', ' ').title() if event.event_type else 'Other Event',
                'type': event_type
            })
    
    # Get teacher work days for this month
    teacher_work_days = TeacherWorkDay.query.filter(
        TeacherWorkDay.school_year_id == active_year.id,
        TeacherWorkDay.date >= start_of_month,
        TeacherWorkDay.date <= end_of_month
    ).all()
    
    for work_day in teacher_work_days:
        if work_day.date.month == month:
            # Shorten the title for better display
            short_title = work_day.title
            if "Professional Development" in short_title:
                short_title = "PD Day"
            elif "First Day" in short_title:
                short_title = "First Day"
            
            academic_dates.append({
                'day': work_day.date.day,
                'title': short_title,
                'category': 'Teacher Work Day',
                'type': 'teacher_work_day'
            })
    
    # Get school breaks for this month
    school_breaks = SchoolBreak.query.filter(
        SchoolBreak.school_year_id == active_year.id,
        SchoolBreak.start_date <= end_of_month,
        SchoolBreak.end_date >= start_of_month
    ).all()
    
    for school_break in school_breaks:
        # Check if any part of the break falls in this month
        if (school_break.start_date.month == month or 
            school_break.end_date.month == month or
            (school_break.start_date.month < month and school_break.end_date.month > month)):
            
            # For multi-day breaks, show start and end dates
            if school_break.start_date.month == month:
                # Shorten break names for better display
                short_name = school_break.name
                if "Thanksgiving" in short_name:
                    short_name = "Thanksgiving Break"
                elif "Winter" in short_name:
                    short_name = "Winter Break"
                elif "Spring" in short_name:
                    short_name = "Spring Break"
                
                academic_dates.append({
                    'day': school_break.start_date.day,
                    'title': f"{short_name} Start",
                    'category': 'School Break',
                    'type': 'school_break_start'
                })
            
            if school_break.end_date.month == month:
                short_name = school_break.name
                if "Thanksgiving" in short_name:
                    short_name = "Thanksgiving Break"
                elif "Winter" in short_name:
                    short_name = "Winter Break"
                elif "Spring" in short_name:
                    short_name = "Spring Break"
                
                academic_dates.append({
                    'day': school_break.end_date.day,
                    'title': f"{short_name} End",
                    'category': 'School Break',
                    'type': 'school_break_end'
                })
    
    return academic_dates

@student_blueprint.route('/settings')
@login_required
@student_required
def student_settings():
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get current school year
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    # Get student's enrolled classes
    enrollments = []
    gpa = 0.0
    if current_school_year:
        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            is_active=True
        ).join(Class).filter(
            Class.school_year_id == current_school_year.id
        ).all()
        
        # Calculate GPA if we have enrollments
        if enrollments:
            class_ids = [e.class_id for e in enrollments]
            all_grades = []
            for class_id in class_ids:
                class_grades = Grade.query.join(Assignment).filter(
                    Grade.student_id == student.id,
                    Assignment.class_id == class_id,
                    Assignment.school_year_id == current_school_year.id
                ).all()
                
                if class_grades:
                    grade_percentages = []
                    for g in class_grades:
                        # Skip voided grades and voided assignments
                        if g.is_voided or g.assignment.status == 'Voided':
                            continue
                            
                        grade_data = json.loads(g.grade_data)
                        if 'score' in grade_data and grade_data['score'] is not None:
                            try:
                                score = float(grade_data['score'])
                                grade_percentages.append(score)
                            except (ValueError, TypeError):
                                continue
                    
                    if grade_percentages:
                        all_grades.extend(grade_percentages)
            
            if all_grades:
                gpa = calculate_gpa(all_grades)
    
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'settings', 'settings',
                            school_year=current_school_year,
                            enrollments=enrollments,
                            gpa=gpa))

@student_blueprint.route('/class/<int:class_id>')
@login_required
@student_required
def view_class(class_id):
    """View comprehensive class information including teacher, students, assignments, grades, and announcements"""
    student = Student.query.get_or_404(current_user.student_id)
    class_obj = Class.query.get_or_404(class_id)
    
    # Verify student is enrolled in this class
    enrollment = Enrollment.query.filter_by(student_id=student.id, class_id=class_id, is_active=True).first()
    if not enrollment:
        flash('You are not enrolled in this class.', 'danger')
        return redirect(url_for('student.student_classes'))

    # Get teacher information
    teacher = None
    if class_obj.teacher_id:
        teacher = TeacherStaff.query.get(class_obj.teacher_id)
    
    # Get all enrolled students in this class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments]
    
    # Get assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get submissions and grades for this student (excluding voided grades and voided assignments)
    all_grades = Grade.query.filter_by(student_id=student.id).all()
    student_grades = {}
    for g in all_grades:
        # Skip voided grades and voided assignments
        if not g.is_voided and g.assignment.status != 'Voided':
            student_grades[g.assignment_id] = json.loads(g.grade_data)
    
    student_submissions = {s.assignment_id: s for s in Submission.query.filter_by(student_id=student.id).all()}
    
    # Get announcements for this class
    announcements = Announcement.query.filter_by(class_id=class_id).order_by(Announcement.timestamp.desc()).limit(5).all()
    
    # Calculate student's GPA for this class
    class_gpa = 0.0
    if assignments:
        scores = []
        for assignment in assignments:
            # Skip voided assignments
            if assignment.status == 'Voided':
                continue
                
            if assignment.id in student_grades:
                score = student_grades[assignment.id].get('score', 0)
                if score is not None:
                    scores.append(score)
        
        if scores:
            # Convert percentage to GPA (90-100 = 4.0, 80-89 = 3.0, etc.)
            gpa_scores = []
            for score in scores:
                if score >= 90:
                    gpa_scores.append(4.0)
                elif score >= 80:
                    gpa_scores.append(3.0)
                elif score >= 70:
                    gpa_scores.append(2.0)
                elif score >= 60:
                    gpa_scores.append(1.0)
                else:
                    gpa_scores.append(0.0)
            
            class_gpa = sum(gpa_scores) / len(gpa_scores)
    
    # Get current date for assignment status
    from datetime import datetime
    today = datetime.now()
    
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'classes', 'classes', 
                                                grades=student_grades,
                                                assignments=assignments,
                                                submissions=student_submissions,
                                                announcements=announcements),
                         class_obj=class_obj,
                         teacher=teacher,
                         enrolled_students=enrolled_students,
                         class_gpa=class_gpa,
                         today=today,
                         show_class_details=True)


@student_blueprint.route('/class/<int:class_id>/assignments')
@login_required
@student_required
def view_class_assignments(class_id):
    """View all assignments for a specific class"""
    student = Student.query.get_or_404(current_user.student_id)
    class_obj = Class.query.get_or_404(class_id)
    
    # Get assignments for this class (show Active and Inactive assignments)
    assignments = Assignment.query.filter(
        Assignment.class_id == class_id,
        Assignment.status.in_(['Active', 'Inactive'])
    ).order_by(Assignment.due_date.desc()).all()
    
    # Get submissions and grades for this student (excluding voided grades and voided assignments)
    all_grades = Grade.query.filter_by(student_id=student.id).all()
    student_grades = {}
    for g in all_grades:
        # Skip voided grades and voided assignments
        if not g.is_voided and g.assignment.status != 'Voided':
            student_grades[g.assignment_id] = g
    
    student_submissions = {s.assignment_id: s for s in Submission.query.filter_by(student_id=student.id).all()}
    
    # Create assignments with status for template
    assignments_with_status = []
    for assignment in assignments:
        submission = student_submissions.get(assignment.id)
        grade = student_grades.get(assignment.id)
        
        # Determine student-facing status
        student_status = get_student_assignment_status(assignment, submission, grade, student.id)
        
        assignments_with_status.append((assignment, submission, student_status))
    
    from datetime import datetime
    today = datetime.now()
    
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'classes', 'classes',
                                                assignments_with_status=assignments_with_status,
                                                grades=student_grades,
                                                submissions=student_submissions),
                         class_obj=class_obj, 
                         today=today,
                         show_assignments=True)


@student_blueprint.route('/take-quiz/<int:assignment_id>')
@login_required
@student_required
def take_quiz(assignment_id):
    """Take a quiz assignment"""
    student = Student.query.get_or_404(current_user.student_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is a quiz
    if assignment.assignment_type != 'quiz':
        flash("This is not a quiz assignment.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Check if student is enrolled in the class
    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        class_id=assignment.class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash("You are not enrolled in this class.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Check if assignment is still active
    if assignment.status not in ['Active', 'Inactive']:
        flash("This assignment is no longer available.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Check if already submitted
    submission = Submission.query.filter_by(
        student_id=student.id,
        assignment_id=assignment_id
    ).first()
    
    # Check if already graded
    grade = Grade.query.filter_by(
        student_id=student.id,
        assignment_id=assignment_id
    ).first()
    
    # Load quiz questions
    questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).order_by(QuizQuestion.order).all()
    
    # Load student's existing answers if any
    existing_answers = {}
    if submission:
        answers = QuizAnswer.query.join(QuizQuestion).filter(
            QuizAnswer.student_id == student.id,
            QuizQuestion.assignment_id == assignment_id
        ).all()
        for answer in answers:
            existing_answers[answer.question_id] = answer
    
    return render_template('shared/take_quiz.html', 
                         assignment=assignment,
                         questions=questions,
                         submission=submission,
                         grade=grade,
                         student=student,
                         existing_answers=existing_answers)

@student_blueprint.route('/save-quiz-progress/<int:assignment_id>', methods=['POST'])
@login_required
@student_required
def save_quiz_progress(assignment_id):
    """Save quiz progress for later continuation"""
    try:
        student = Student.query.get_or_404(current_user.student_id)
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Check if assignment allows save and continue
        if not assignment.allow_save_and_continue:
            return jsonify({'success': False, 'message': 'This quiz does not allow save and continue'})
        
        data = request.get_json()
        answers = data.get('answers', {})
        progress_percentage = data.get('progress_percentage', 0)
        questions_answered = data.get('questions_answered', 0)
        
        # Get total questions count
        total_questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).count()
        
        # Check if progress already exists
        progress = QuizProgress.query.filter_by(
            student_id=student.id,
            assignment_id=assignment_id
        ).first()
        
        if progress:
            # Update existing progress
            progress.answers_data = json.dumps(answers)
            progress.progress_percentage = progress_percentage
            progress.questions_answered = questions_answered
            progress.total_questions = total_questions
            progress.last_saved_at = datetime.utcnow()
            progress.updated_at = datetime.utcnow()
        else:
            # Create new progress
            progress = QuizProgress(
                student_id=student.id,
                assignment_id=assignment_id,
                answers_data=json.dumps(answers),
                progress_percentage=progress_percentage,
                questions_answered=questions_answered,
                total_questions=total_questions,
                last_saved_at=datetime.utcnow()
            )
            db.session.add(progress)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Progress saved successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error saving progress: {str(e)}'})

@student_blueprint.route('/load-quiz-progress/<int:assignment_id>')
@login_required
@student_required
def load_quiz_progress(assignment_id):
    """Load saved quiz progress"""
    try:
        student = Student.query.get_or_404(current_user.student_id)
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Check if assignment allows save and continue
        if not assignment.allow_save_and_continue:
            return jsonify({'success': False, 'message': 'This quiz does not allow save and continue'})
        
        # Get saved progress
        progress = QuizProgress.query.filter_by(
            student_id=student.id,
            assignment_id=assignment_id,
            is_submitted=False
        ).first()
        
        if progress:
            # Check if progress is still valid (not expired)
            time_diff = datetime.utcnow() - progress.last_saved_at
            timeout_minutes = assignment.save_timeout_minutes or 30
            
            if time_diff.total_seconds() > (timeout_minutes * 60):
                # Progress expired, delete it
                db.session.delete(progress)
                db.session.commit()
                return jsonify({'success': False, 'message': 'Saved progress has expired'})
            
            # Return progress data
            return jsonify({
                'success': True,
                'progress': {
                    'answers': json.loads(progress.answers_data) if progress.answers_data else {},
                    'progress_percentage': progress.progress_percentage,
                    'questions_answered': progress.questions_answered,
                    'total_questions': progress.total_questions,
                    'last_saved_at': progress.last_saved_at.isoformat()
                }
            })
        else:
            return jsonify({'success': False, 'message': 'No saved progress found'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error loading progress: {str(e)}'})

@student_blueprint.route('/submit-quiz/<int:assignment_id>', methods=['POST'])
@login_required
@student_required
def submit_quiz(assignment_id):
    """Submit quiz answers"""
    student = Student.query.get_or_404(current_user.student_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is a quiz
    if assignment.assignment_type != 'quiz':
        flash("This is not a quiz assignment.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Check if already submitted
    existing_submission = Submission.query.filter_by(
        student_id=student.id,
        assignment_id=assignment_id
    ).first()
    
    if existing_submission:
        flash("You have already submitted this quiz.", "warning")
        return redirect(url_for('student.take_quiz', assignment_id=assignment_id))
    
    try:
        # Get all questions for this assignment
        questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).all()
        total_points = 0
        earned_points = 0
        
        # Process each question
        for question in questions:
            if question.question_type in ['multiple_choice', 'true_false']:
                # Get selected option
                selected_option_id = request.form.get(f'question_{question.id}')
                if selected_option_id:
                    try:
                        selected_option = QuizOption.query.get(int(selected_option_id))
                        is_correct = selected_option and selected_option.is_correct
                        points_earned = question.points if is_correct else 0
                        
                        # Save answer
                        answer = QuizAnswer(
                            student_id=student.id,
                            question_id=question.id,
                            selected_option_id=selected_option.id if selected_option else None,
                            is_correct=is_correct,
                            points_earned=points_earned
                        )
                        db.session.add(answer)
                        
                        if is_correct:
                            earned_points += points_earned
                    except (ValueError, TypeError):
                        # Handle invalid option ID
                        pass
                
            elif question.question_type in ['short_answer', 'essay']:
                # Get text answer
                answer_text = request.form.get(f'question_{question.id}', '')
                points_earned = 0  # Manual grading required for text answers
                
                # Save answer
                answer = QuizAnswer(
                    student_id=student.id,
                    question_id=question.id,
                    answer_text=answer_text,
                    is_correct=None,  # Will be graded manually
                    points_earned=points_earned
                )
                db.session.add(answer)
            
            total_points += question.points
        
        # Create submission record
        submission = Submission(
            student_id=student.id,
            assignment_id=assignment_id,
            comments=f"Quiz submitted with {earned_points}/{total_points} points"
        )
        db.session.add(submission)
        
        # Create grade record
        grade_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        grade = Grade(
            student_id=student.id,
            assignment_id=assignment_id,
            grade_percentage=round(grade_percentage, 2),
            comments=f"Auto-graded quiz: {earned_points}/{total_points} points"
        )
        db.session.add(grade)
        
        db.session.commit()
        flash('Quiz submitted successfully!', 'success')
        return redirect(url_for('student.take_quiz', assignment_id=assignment_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting quiz: {str(e)}', 'danger')
        return redirect(url_for('student.take_quiz', assignment_id=assignment_id))

@student_blueprint.route('/discussion/<int:assignment_id>')
@login_required
@student_required
def join_discussion(assignment_id):
    """Join a discussion assignment"""
    student = Student.query.get_or_404(current_user.student_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is a discussion
    if assignment.assignment_type != 'discussion':
        flash("This is not a discussion assignment.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Check if student is enrolled in the class
    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        class_id=assignment.class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash("You are not enrolled in this class.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Check if assignment is still active
    if assignment.status not in ['Active', 'Inactive']:
        flash("This assignment is no longer available.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    # Load discussion threads
    threads = DiscussionThread.query.filter_by(assignment_id=assignment_id).order_by(DiscussionThread.is_pinned.desc(), DiscussionThread.created_at.desc()).all()
    
    return render_template('shared/discussion.html', 
                         assignment=assignment,
                         student=student,
                         threads=threads)

@student_blueprint.route('/create-thread/<int:assignment_id>', methods=['POST'])
@login_required
@student_required
def create_discussion_thread(assignment_id):
    """Create a new discussion thread"""
    student = Student.query.get_or_404(current_user.student_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is a discussion
    if assignment.assignment_type != 'discussion':
        flash("This is not a discussion assignment.", "danger")
        return redirect(url_for('student.student_assignments'))
    
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    
    if not title or not content:
        flash("Please provide both title and content.", "danger")
        return redirect(url_for('student.join_discussion', assignment_id=assignment_id))
    
    try:
        thread = DiscussionThread(
            assignment_id=assignment_id,
            student_id=student.id,
            title=title,
            content=content
        )
        db.session.add(thread)
        db.session.commit()
        
        flash('Discussion thread created successfully!', 'success')
        return redirect(url_for('student.join_discussion', assignment_id=assignment_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating thread: {str(e)}', 'danger')
        return redirect(url_for('student.join_discussion', assignment_id=assignment_id))

@student_blueprint.route('/reply-to-thread/<int:thread_id>', methods=['POST'])
@login_required
@student_required
def reply_to_thread(thread_id):
    """Reply to a discussion thread"""
    student = Student.query.get_or_404(current_user.student_id)
    thread = DiscussionThread.query.get_or_404(thread_id)
    
    content = request.form.get('content', '').strip()
    
    if not content:
        flash("Please provide content for your reply.", "danger")
        return redirect(url_for('student.join_discussion', assignment_id=thread.assignment_id))
    
    try:
        post = DiscussionPost(
            thread_id=thread_id,
            student_id=student.id,
            content=content
        )
        db.session.add(post)
        db.session.commit()
        
        flash('Reply posted successfully!', 'success')
        return redirect(url_for('student.join_discussion', assignment_id=thread.assignment_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error posting reply: {str(e)}', 'danger')
        return redirect(url_for('student.join_discussion', assignment_id=thread.assignment_id))

@student_blueprint.route('/class/<int:class_id>/teacher')
@login_required
@student_required
def view_class_teacher(class_id):
    """View teacher information for a specific class"""
    student = Student.query.get_or_404(current_user.student_id)
    class_obj = Class.query.get_or_404(class_id)
    
    # Get teacher information
    teacher = None
    if class_obj.teacher_id:
        teacher = TeacherStaff.query.get(class_obj.teacher_id)
    
    return render_template('students/role_student_dashboard.html', 
                         **create_template_context(student, 'classes', 'classes'),
                         class_obj=class_obj, 
                         teacher=teacher,
                         show_teacher=True)

@student_blueprint.route('/submit/<int:assignment_id>', methods=['POST'])
@login_required
@student_required
def submit_assignment(assignment_id):
    student = Student.query.get_or_404(current_user.student_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if this is a redo submission
    is_redo = request.args.get('is_redo', '0') == '1' or request.form.get('is_redo', '0') == '1'
    redo_record = None
    
    if is_redo:
        # Verify redo permission exists and is not used
        redo_record = AssignmentRedo.query.filter_by(
            assignment_id=assignment_id,
            student_id=student.id,
            is_used=False
        ).first()
        
        if not redo_record:
            return jsonify({'success': False, 'message': 'No redo permission found or redo already submitted'}), 403

    if 'submission_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    file = request.files['submission_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        # Type assertion for filename
        assert file.filename is not None
        filename = secure_filename(file.filename)
        # Create a unique filename to avoid collisions
        redo_suffix = '_REDO' if is_redo else ''
        unique_filename = f"sub_{student.id}_{assignment.id}{redo_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            
            # Get optional notes
            notes = request.form.get('submission_notes', '')
            
            # Handle redo submission differently
            if is_redo and redo_record:
                # Create new submission for redo
                submission = Submission(
                    student_id=student.id,
                    assignment_id=assignment_id,
                    file_path=unique_filename,
                    comments=notes + ' [REDO ATTEMPT]',
                    submitted_at=datetime.utcnow()
                )
                db.session.add(submission)
                db.session.flush()  # Get submission ID
                
                # Update redo record
                redo_record.is_used = True
                redo_record.redo_submission_id = submission.id
                redo_record.redo_submitted_at = datetime.utcnow()
                
                # Check if redo was submitted late
                if datetime.utcnow() > redo_record.redo_deadline:
                    redo_record.was_redo_late = True
                
                db.session.commit()
                return jsonify({'success': True, 'message': 'Redo submitted successfully! Your teacher will grade it soon.'}), 200
            else:
                # Regular submission
                submission = Submission.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()
                if submission:
                    # Optionally, delete the old file
                    if submission.file_path and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], submission.file_path)):
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], submission.file_path))
                    submission.file_path = unique_filename
                    submission.submitted_at = db.func.now()
                    if notes:
                        submission.comments = notes
                else:
                    # Create new submission
                    submission = Submission(
                        student_id=student.id,
                        assignment_id=assignment_id,
                        file_path=unique_filename,
                        comments=notes,
                        submitted_at=datetime.utcnow()
                    )
                    db.session.add(submission)
            
                db.session.commit()
                return jsonify({'success': True, 'message': 'Assignment submitted successfully!'}), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"File upload failed for student {student.id}, assignment {assignment_id}: {e}")
            return jsonify({'success': False, 'message': f'An error occurred while saving the file: {e}'}), 500

    else:
        return jsonify({'success': False, 'message': f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

@student_blueprint.route('/submit/group/<int:assignment_id>', methods=['POST'])
@login_required
@student_required
def submit_group_assignment(assignment_id):
    """Submit a group assignment"""
    student = Student.query.get_or_404(current_user.student_id)
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Check if student is enrolled in the class
    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        class_id=group_assignment.class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        return jsonify({'success': False, 'message': 'You are not enrolled in this class'}), 403
    
    # Find which group the student belongs to for this assignment
    student_group = None
    if group_assignment.selected_group_ids:
        # Assignment is for specific groups
        import json
        selected_group_ids = json.loads(group_assignment.selected_group_ids)
        for group_id in selected_group_ids:
            membership = StudentGroupMember.query.filter_by(
                student_id=student.id,
                group_id=group_id
            ).first()
            if membership:
                student_group = StudentGroup.query.get(group_id)
                break
    else:
        # Assignment is for all groups in the class
        membership = StudentGroupMember.query.join(StudentGroup).filter(
            StudentGroupMember.student_id == student.id,
            StudentGroup.class_id == group_assignment.class_id,
            StudentGroup.is_active == True
        ).first()
        if membership:
            student_group = StudentGroup.query.get(membership.group_id)
    
    if not student_group and group_assignment.collaboration_type != 'both':
        return jsonify({'success': False, 'message': 'You are not assigned to a group for this assignment'}), 403
    
    if 'submission_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    file = request.files['submission_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"group_sub_{student.id}_{assignment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            
            # Get optional notes
            notes = request.form.get('submission_notes', '')
            
            # Check for existing group submission
            existing_submission = GroupSubmission.query.filter_by(
                group_assignment_id=assignment_id,
                group_id=student_group.id if student_group else None,
                submitted_by=student.id
            ).first()
            
            if existing_submission:
                # Update existing submission
                if existing_submission.attachment_file_path and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], existing_submission.attachment_file_path)):
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], existing_submission.attachment_file_path))
                
                existing_submission.attachment_filename = unique_filename
                existing_submission.attachment_original_filename = filename
                existing_submission.attachment_file_path = filepath
                existing_submission.attachment_file_size = os.path.getsize(filepath)
                existing_submission.attachment_mime_type = file.content_type
                existing_submission.submitted_at = datetime.utcnow()
                if notes:
                    existing_submission.submission_text = notes
            else:
                # Create new group submission
                group_submission = GroupSubmission(
                    group_assignment_id=assignment_id,
                    group_id=student_group.id if student_group else None,
                    submitted_by=student.id,
                    submission_text=notes,
                    attachment_filename=unique_filename,
                    attachment_original_filename=filename,
                    attachment_file_path=filepath,
                    attachment_file_size=os.path.getsize(filepath),
                    attachment_mime_type=file.content_type,
                    submitted_at=datetime.utcnow(),
                    is_late=datetime.utcnow() > group_assignment.due_date
                )
                db.session.add(group_submission)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Group assignment submitted successfully!'}), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Group assignment upload failed for student {student.id}, assignment {assignment_id}: {e}")
            return jsonify({'success': False, 'message': f'An error occurred while saving the file: {e}'}), 500

    else:
        return jsonify({'success': False, 'message': f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

@student_blueprint.route('/download-assignment-file/<int:assignment_id>')
@login_required
@student_required
def download_assignment_file(assignment_id):
    """Download assignment attachment file"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if student is enrolled in this class
    student = Student.query.get_or_404(current_user.student_id)
    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        class_id=assignment.class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        abort(403, description="You are not enrolled in this class")
    
    if not assignment.attachment_filename:
        abort(404, description="No attachment found for this assignment")
    
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.attachment_filename)
    
    if not os.path.exists(file_path):
        abort(404, description="File not found")
    
    # Get the original filename for download
    original_filename = assignment.attachment_original_filename or assignment.attachment_filename
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=original_filename
    )

@student_blueprint.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@student_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('student.student_dashboard'))

@student_blueprint.route('/goals/set', methods=['POST'])
@login_required
@student_required
def set_goal():
    """Set or update a goal for a specific class."""
    student = Student.query.get_or_404(current_user.student_id)
    
    class_id = request.form.get('class_id', type=int)
    target_grade = request.form.get('target_grade', type=float)
    
    if not class_id or not target_grade:
        flash('Please provide both class and target grade.', 'error')
        return redirect(url_for('student.student_dashboard'))
    
    # Check if goal already exists
    existing_goal = StudentGoal.query.filter_by(
        student_id=student.id,
        class_id=class_id
    ).first()
    
    if existing_goal:
        existing_goal.target_grade = target_grade
        existing_goal.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Goal updated successfully!', 'success')
    else:
        new_goal = StudentGoal(
            student_id=student.id,
            class_id=class_id,
            target_grade=target_grade
        )
        db.session.add(new_goal)
        db.session.commit()
        flash('Goal set successfully!', 'success')
    
    return redirect(url_for('student.student_dashboard'))

@student_blueprint.route('/goals/delete/<int:goal_id>', methods=['POST'])
@login_required
@student_required
def delete_goal(goal_id):
    """Delete a student goal."""
    goal = StudentGoal.query.get_or_404(goal_id)
    student = Student.query.get_or_404(current_user.student_id)
    
    # Ensure the goal belongs to the current student
    if goal.student_id != student.id:
        abort(403)
    
    db.session.delete(goal)
    db.session.commit()
    
    flash('Goal deleted successfully.', 'success')
    return redirect(url_for('student.student_dashboard'))

# Communications Routes for Students
@student_blueprint.route('/communications')
@login_required
@student_required
def student_communications():
    """Communications tab - Under Development."""
    return render_template('shared/under_development.html',
                         section='communications',
                         active_tab='communications')

@student_blueprint.route('/communications/messages')
@login_required
@student_required
def student_messages():
    """View all messages for the student."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get all messages for the student
    messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'messages', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             messages=messages))

@student_blueprint.route('/communications/message/<int:message_id>')
@login_required
@student_required
def student_view_message(message_id):
    """View a specific message."""
    student = Student.query.get_or_404(current_user.student_id)
    message = Message.query.get_or_404(message_id)
    
    # Ensure the student is the recipient
    if message.recipient_id != current_user.id:
        abort(403)
    
    # Mark as read
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'view_message', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             message=message))

@student_blueprint.route('/communications/groups')
@login_required
@student_required
def student_groups():
    """View message groups the student is a member of."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get groups the student is a member of
    groups = MessageGroup.query.join(MessageGroupMember).filter(
        MessageGroupMember.user_id == current_user.id
    ).all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'groups', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             groups=groups))

@student_blueprint.route('/communications/group/<int:group_id>')
@login_required
@student_required
def student_view_group(group_id):
    """View a specific message group."""
    student = Student.query.get_or_404(current_user.student_id)
    group = MessageGroup.query.get_or_404(group_id)
    
    # Ensure the student is a member of this group
    membership = MessageGroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        abort(403)
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.created_at.desc()).all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'view_group', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             group=group,
                             messages=messages))

@student_blueprint.route('/communications/announcements')
@login_required
@student_required
def student_announcements():
    """View announcements relevant to the student."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get student's classes for filtering
    classes = Class.query.all()  # Simplified - should filter by enrollment
    class_ids = [c.id for c in classes]
    
    # Get announcements relevant to the student
    announcements = Announcement.query.filter(
        (Announcement.target_group.in_(['all_students', 'all'])) |
        ((Announcement.target_group == 'class') & (Announcement.class_id.in_(class_ids)))
    ).order_by(Announcement.timestamp.desc()).all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'announcements', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=announcements,
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             get_letter_grade=get_letter_grade))

# New routes for student messaging capabilities
@student_blueprint.route('/communications/send-message', methods=['GET', 'POST'])
@login_required
@student_required
def student_send_message():
    """Send a new message."""
    student = Student.query.get_or_404(current_user.student_id)
    
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        
        if not recipient_id or not content:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('student.student_send_message'))
        
        # Verify recipient exists
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Invalid recipient selected.', 'error')
            return redirect(url_for('student.student_send_message'))
        
        # Create the message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            message_type='direct'
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('student.student_messages'))
    
    # Get potential recipients (other students and teachers)
    students = Student.query.all()
    teachers = TeacherStaff.query.all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'send_message', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             students=students,
                             teachers=teachers))

@student_blueprint.route('/communications/create-group', methods=['GET', 'POST'])
@login_required
@student_required
def student_create_group():
    """Create a new message group."""
    student = Student.query.get_or_404(current_user.student_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        group_type = request.form.get('group_type', 'student')
        member_ids = request.form.getlist('members')
        
        if not name:
            flash('Please provide a group name.', 'error')
            return redirect(url_for('student.student_create_group'))
        
        # Create the group
        group = MessageGroup(
            name=name,
            description=description,
            group_type=group_type,
            created_by=current_user.id
        )
        
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add the creator as a member and admin
        creator_member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(creator_member)
        
        # Add other members
        for member_id in member_ids:
            if member_id and int(member_id) != current_user.id:
                member = MessageGroupMember(
                    group_id=group.id,
                    user_id=int(member_id)
                )
                db.session.add(member)
        
        db.session.commit()
        
        flash('Group created successfully!', 'success')
        return redirect(url_for('student.student_groups'))
    
    # Get potential members (other students)
    students = Student.query.filter(Student.id != student.id).all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'create_group', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             students=students))

@student_blueprint.route('/communications/group/<int:group_id>/send-message', methods=['POST'])
@login_required
@student_required
def student_send_group_message(group_id):
    """Send a message to a group."""
    student = Student.query.get_or_404(current_user.student_id)
    group = MessageGroup.query.get_or_404(group_id)
    
    # Ensure the student is a member of this group
    membership = MessageGroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        abort(403)
    
    content = request.form.get('content', '').strip()
    subject = request.form.get('subject', '').strip()
    
    if not content:
        flash('Please provide message content.', 'error')
        return redirect(url_for('student.student_view_group', group_id=group_id))
    
    # Create the group message
    message = Message(
        sender_id=current_user.id,
        recipient_id=None,  # Group messages don't have a specific recipient
        subject=subject,
        content=content,
        message_type='group',
        group_id=group_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    flash('Message sent to group!', 'success')
    return redirect(url_for('student.student_view_group', group_id=group_id))

@student_blueprint.route('/communications/sent-messages')
@login_required
@student_required
def student_sent_messages():
    """View messages sent by the student."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get messages sent by the student
    sent_messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    return render_template('students/role_student_dashboard.html',
                         **create_template_context(student, 'sent_messages', 'communications',
                             grades={},
                             attendance_summary={},
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             notifications=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             sent_messages=sent_messages))

@student_blueprint.route('/communications/group/<int:group_id>/leave', methods=['POST'])
@login_required
@student_required
def student_leave_group(group_id):
    """Leave a message group."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Find the membership
    membership = MessageGroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('student.student_groups'))
    
    # Don't allow the creator to leave (or implement group transfer logic)
    group = MessageGroup.query.get(group_id)
    if group.created_by == current_user.id:
        flash('Group creators cannot leave their own groups.', 'error')
        return redirect(url_for('student.student_groups'))
    
    db.session.delete(membership)
    db.session.commit()
    
    flash('You have left the group.', 'success')
    return redirect(url_for('student.student_groups'))
