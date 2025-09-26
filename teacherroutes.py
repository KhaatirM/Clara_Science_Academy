from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort, jsonify
from flask_login import login_required, current_user
from models import db, TeacherStaff, Class, Student, Assignment, Grade, SchoolYear, Submission, Announcement, Notification, Message, MessageGroup, MessageGroupMember, MessageAttachment, ScheduledAnnouncement, Enrollment, Attendance, SchoolDayAttendance, StudentGroup, StudentGroupMember, GroupAssignment, GroupSubmission, GroupGrade, AcademicPeriod, GroupTemplate, PeerEvaluation, AssignmentRubric, GroupContract, ReflectionJournal, GroupProgress, AssignmentTemplate, GroupRotation, GroupRotationHistory, PeerReview, DraftSubmission, DraftFeedback, DeadlineReminder, ReminderNotification, Feedback360, Feedback360Response, Feedback360Criteria, GroupConflict, ConflictResolution, ConflictParticipant, GroupWorkReport, IndividualContribution, TimeTracking, CollaborationMetrics, ReportExport, AnalyticsDashboard, PerformanceBenchmark, AssignmentExtension, QuizQuestion, QuizOption, QuizAnswer, DiscussionThread, DiscussionPost
from decorators import teacher_required
import json
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import time

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_teacher_or_admin():
    """Helper function to get teacher object or None for administrators."""
    if current_user.role in ['Director', 'School Administrator']:
        return None
    else:
        if current_user.teacher_staff_id:
            return TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first()
        return None

def is_authorized_for_class(class_obj):
    """Check if current user is authorized to access a specific class."""
    if current_user.role == 'Director':
        return True  # Directors have access to all classes
    elif current_user.role == 'School Administrator':
        # School Administrators can access classes they are assigned to as teachers
        teacher_staff = None
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
        return teacher_staff and class_obj.teacher_id == teacher_staff.id
    else:
        # Regular teachers can only access their own classes
        teacher = get_teacher_or_admin()
        return teacher and class_obj.teacher_id == teacher.id

def is_admin():
    """Helper function to check if user is an administrator."""
    return current_user.role in ['Director', 'School Administrator']

def get_current_quarter():
    """Get the current quarter based on AcademicPeriod dates"""
    try:
        from datetime import date
        
        # Get the active school year
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            return "1"  # Default to Q1 if no active school year
        
        # Get all active quarters for the current school year
        quarters = AcademicPeriod.query.filter_by(
            school_year_id=current_school_year.id,
            period_type='quarter',
            is_active=True
        ).order_by(AcademicPeriod.start_date).all()
        
        if not quarters:
            return "1"  # Default to Q1 if no quarters defined
        
        # Get today's date
        today = date.today()
        
        # Find which quarter we're currently in
        for quarter in quarters:
            if quarter.start_date <= today <= quarter.end_date:
                # Extract quarter number from name (e.g., "Q1" -> "1")
                quarter_num = quarter.name.replace('Q', '')
                return quarter_num
        
        # If we're not in any quarter period, find the closest one
        # Check if we're before the first quarter
        if today < quarters[0].start_date:
            return quarters[0].name.replace('Q', '')
        
        # Check if we're after the last quarter
        if today > quarters[-1].end_date:
            return quarters[-1].name.replace('Q', '')
        
        # Default to Q1 if we can't determine
        return "1"
        
    except Exception as e:
        print(f"Error determining current quarter: {e}")
        return "1"  # Default to Q1 on error

def calculate_student_gpa(student_id):
    """Calculate GPA for a student based on their grades"""
    try:
        # Get all grades for the student, excluding Voided assignments
        grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student_id,
            Assignment.status != 'Voided'  # Exclude Voided assignments from GPA calculation
        ).all()
        
        if not grades:
            return 0.0
        
        total_points = 0
        total_weight = 0
        
        for grade in grades:
            try:
                grade_data = json.loads(grade.grade_data)
                score = grade_data.get('score', 0)
                
                # Convert percentage to GPA points (90-100 = 4.0, 80-89 = 3.0, etc.)
                if score >= 90:
                    gpa_points = 4.0
                elif score >= 80:
                    gpa_points = 3.0
                elif score >= 70:
                    gpa_points = 2.0
                elif score >= 60:
                    gpa_points = 1.0
                else:
                    gpa_points = 0.0
                
                total_points += gpa_points
                total_weight += 1
                
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        
        if total_weight == 0:
            return 0.0
        
        return round(total_points / total_weight, 2)
        
    except Exception as e:
        print(f"Error calculating GPA for student {student_id}: {e}")
        return 0.0

teacher_blueprint = Blueprint('teacher', __name__)

@teacher_blueprint.route('/dashboard')
@login_required
@teacher_required
def teacher_dashboard():
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
    from datetime import datetime, timedelta
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

@teacher_blueprint.route('/class/<int:class_id>')
@login_required
@teacher_required
def view_class(class_id):
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
    from datetime import datetime, timedelta
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

@teacher_blueprint.route('/assignment/type-selector')
@login_required
@teacher_required
def assignment_type_selector():
    """Assignment type selection page"""
    return render_template('assignment_type_selector.html')

@teacher_blueprint.route('/assignment/create/quiz', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_quiz_assignment():
    """Create a quiz assignment"""
    if request.method == 'POST':
        # Handle quiz assignment creation
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('teacher.create_quiz_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.create_quiz_assignment'))
            
            # Get save and continue settings
            allow_save_and_continue = request.form.get('allow_save_and_continue') == 'on'
            max_save_attempts = int(request.form.get('max_save_attempts', 10))
            save_timeout_minutes = int(request.form.get('save_timeout_minutes', 30))
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                status='Active',
                assignment_type='quiz',
                allow_save_and_continue=allow_save_and_continue,
                max_save_attempts=max_save_attempts,
                save_timeout_minutes=save_timeout_minutes
            )
            
            db.session.add(new_assignment)
            db.session.flush()  # Get the assignment ID
            
            # Save quiz questions
            question_count = 0
            for key, value in request.form.items():
                if key.startswith('question_text_'):
                    question_id = key.split('_')[2]
                    question_text = value
                    question_type = request.form.get(f'question_type_{question_id}')
                    points = float(request.form.get(f'points_{question_id}', 1.0))
                    
                    # Create the question
                    question = QuizQuestion(
                        assignment_id=new_assignment.id,
                        question_text=question_text,
                        question_type=question_type,
                        points=points,
                        order=question_count
                    )
                    db.session.add(question)
                    db.session.flush()  # Get the question ID
                    
                    # Save options for multiple choice and true/false
                    if question_type in ['multiple_choice', 'true_false']:
                        option_count = 0
                        for option_key, option_value in request.form.items():
                            if option_key.startswith(f'option_text_{question_id}_'):
                                option_text = option_value
                                option_id = option_key.split('_')[3]
                                is_correct = request.form.get(f'correct_answer_{question_id}') == option_id
                                
                                option = QuizOption(
                                    question_id=question.id,
                                    option_text=option_text,
                                    is_correct=is_correct,
                                    order=option_count
                                )
                                db.session.add(option)
                                option_count += 1
                    
                    question_count += 1
            
            db.session.commit()
            flash('Quiz assignment created successfully!', 'success')
            return redirect(url_for('teacher.my_assignments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quiz assignment: {str(e)}', 'danger')
    
    # GET request - show form
    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    current_quarter = get_current_quarter()
    return render_template('create_quiz_assignment.html', classes=classes, current_quarter=current_quarter)

@teacher_blueprint.route('/assignment/create/discussion', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_discussion_assignment():
    """Create a discussion assignment"""
    if request.method == 'POST':
        # Handle discussion assignment creation
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        discussion_topic = request.form.get('discussion_topic')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, class_id, discussion_topic, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('teacher.create_discussion_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.create_discussion_assignment'))
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=f"{discussion_topic}\n\n{description}",
                due_date=due_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                status='Active',
                assignment_type='discussion'
            )
            
            db.session.add(new_assignment)
            db.session.commit()
            
            # TODO: Save discussion settings, rubric, and prompts
            # This would require additional models for discussion settings, rubric criteria, etc.
            
            flash('Discussion assignment created successfully!', 'success')
            return redirect(url_for('teacher.my_assignments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating discussion assignment: {str(e)}', 'danger')
    
    # GET request - show form
    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    current_quarter = get_current_quarter()
    return render_template('create_discussion_assignment.html', classes=classes, current_quarter=current_quarter)

@teacher_blueprint.route('/assignment/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment_select_class():
    """Add a new assignment - class selection page"""
    if request.method == 'POST':
        class_id = request.form.get('class_id', type=int)
        if class_id:
            return redirect(url_for('teacher.add_assignment', class_id=class_id))
        else:
            flash("Please select a class.", "danger")
    
    # Get classes for the current teacher
    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    return render_template('add_assignment_select_class.html', classes=classes)

@teacher_blueprint.route('/class/<int:class_id>/assignment/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment(class_id):
    class_obj = Class.query.get_or_404(class_id)
    # Authorization check - Directors and School Administrators can add assignments to any class
    teacher = get_teacher_or_admin()
    
    if not is_admin() and teacher and class_obj.teacher_id != teacher.id:
        flash("You are not authorized to add assignments to this class.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
        
        if not all([title, due_date_str, quarter]):
            flash("Title, Due Date, and Quarter are required.", "danger")
            return redirect(request.url)
        
        # Validate status
        valid_statuses = ['Active', 'Inactive', 'Voided']
        if status not in valid_statuses:
            flash('Invalid assignment status.', 'danger')
            return redirect(request.url)

        # Type assertion for due_date_str
        assert due_date_str is not None
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            flash("Cannot create assignment: No active school year.", "danger")
            return redirect(url_for('teacher.view_class', class_id=class_id))

        # Type assertion for quarter
        assert quarter is not None
        
        # Create assignment using attribute assignment
        new_assignment = Assignment()
        new_assignment.title = title
        new_assignment.description = description
        new_assignment.due_date = due_date
        new_assignment.class_id = class_id
        new_assignment.school_year_id = current_school_year.id
        new_assignment.quarter = str(quarter)  # Store as string to match model definition
        new_assignment.status = status
        
        # Handle file upload
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Type assertion for filename
                    assert file.filename is not None
                    filename = secure_filename(file.filename)
                    # Create a unique filename to avoid collisions
                    unique_filename = f"assignment_{class_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    try:
                        file.save(filepath)
                        
                        # Save file information to assignment
                        new_assignment.attachment_filename = unique_filename
                        new_assignment.attachment_original_filename = filename
                        new_assignment.attachment_file_path = filepath
                        new_assignment.attachment_file_size = os.path.getsize(filepath)
                        new_assignment.attachment_mime_type = file.content_type
                        
                    except Exception as e:
                        flash(f'Error saving file: {str(e)}', 'danger')
                        return redirect(request.url)
                else:
                    flash(f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                    return redirect(request.url)
        
        db.session.add(new_assignment)
        db.session.commit()
        
        # Create notifications for students in this class
        from app import create_notification_for_students_in_class
        create_notification_for_students_in_class(
            class_id=class_id,
            notification_type='assignment',
            title=f'New Assignment: {title}',
            message=f'A new assignment "{title}" has been created for {class_obj.name}. Due date: {due_date.strftime("%b %d, %Y")}',
            link=url_for('student.student_assignments')
        )
        
        flash('Assignment created successfully.', 'success')
        return redirect(url_for('teacher.view_class', class_id=class_id))

    # Get current quarter for pre-selection
    current_quarter = get_current_quarter()
    
    return render_template('add_assignment.html', class_obj=class_obj, current_quarter=current_quarter)


@teacher_blueprint.route('/assignment/view/<int:assignment_id>')
@login_required
@teacher_required
def view_assignment(assignment_id):
    """View assignment details"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Get class information
    class_info = Class.query.get(assignment.class_id) if assignment.class_id else None
    teacher = None
    if class_info and class_info.teacher_id:
        teacher = TeacherStaff.query.get(class_info.teacher_id)
    
    # Authorization check - Directors and School Administrators can view any assignment, teachers can only view their own
    current_teacher = get_teacher_or_admin()
    if not is_admin() and current_teacher and class_info.teacher_id != current_teacher.id:
        flash("You are not authorized to view this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get submissions count (if any)
    submissions_count = 0  # This would be implemented when submission system is added
    
    # Get current date for status calculations
    today = datetime.now().date()
    
    return render_template('view_assignment.html', 
                         assignment=assignment,
                         class_info=class_info,
                         teacher=teacher,
                         submissions_count=submissions_count,
                         today=today)


@teacher_blueprint.route('/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(assignment_id):
    """Edit an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors can edit any assignment, teachers can only edit their own
    current_teacher = get_teacher_or_admin()
    if current_user.role != 'Director' and class_obj.teacher_id != current_teacher.id:
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
        
        if not all([title, due_date_str, quarter]):
            flash('Title, Due Date, and Quarter are required.', 'danger')
            return redirect(request.url)
        
        # Validate status
        valid_statuses = ['Active', 'Inactive', 'Voided']
        if status not in valid_statuses:
            flash('Invalid assignment status.', 'danger')
            return redirect(request.url)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Update assignment
            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.quarter = str(quarter)  # Store as string to match model definition
            assignment.status = status
            
            # Handle file upload
            if 'assignment_file' in request.files:
                file = request.files['assignment_file']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"assignment_{assignment.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        try:
                            file.save(filepath)
                            
                            # Update file information
                            assignment.attachment_filename = unique_filename
                            assignment.attachment_original_filename = filename
                        except Exception as e:
                            flash(f'Error saving file: {str(e)}', 'danger')
                            return redirect(request.url)
            
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('teacher.view_class', class_id=class_obj.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(request.url)
    
    # For GET request, get all classes for the dropdown
    classes = Class.query.all()
    school_years = SchoolYear.query.all()
    
    # Debug: Print assignment values
    print(f"Edit Assignment Debug - Assignment ID: {assignment.id}")
    print(f"  Title: {assignment.title}")
    print(f"  Quarter: {assignment.quarter} (type: {type(assignment.quarter)})")
    print(f"  Class ID: {assignment.class_id}")
    print(f"  School Year ID: {assignment.school_year_id}")
    print(f"  Status: {assignment.status}")
    print(f"  Due Date: {assignment.due_date}")
    
    return render_template('edit_assignment.html', 
                         assignment=assignment,
                         classes=classes,
                         school_years=school_years)


@teacher_blueprint.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors can remove any assignment, teachers can only remove their own
    current_teacher = get_teacher_or_admin()
    if current_user.role != 'Director' and class_obj.teacher_id != current_teacher.id:
        flash("You are not authorized to remove this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Delete associated extensions first
        AssignmentExtension.query.filter_by(assignment_id=assignment_id).delete()
        
        # Delete associated file if it exists
        if assignment.attachment_filename:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.attachment_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete the assignment
        db.session.delete(assignment)
        db.session.commit()
        
        flash('Assignment removed successfully.', 'success')
        # Redirect back to assignments page instead of class page
        return redirect(url_for('teacher.my_assignments'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing assignment: {str(e)}', 'danger')
        return redirect(url_for('teacher.my_assignments'))


@teacher_blueprint.route('/assignment/<int:assignment_id>/change-status', methods=['POST'])
@login_required
@teacher_required
def change_assignment_status(assignment_id):
    """Change assignment status"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors can change any assignment, teachers can only change their own
    current_teacher = get_teacher_or_admin()
    if current_user.role != 'Director' and class_obj.teacher_id != current_teacher.id:
        flash("You are not authorized to change this assignment status.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    new_status = request.form.get('status')
    
    # Validate status
    valid_statuses = ['Active', 'Inactive', 'Voided']
    if new_status not in valid_statuses:
        flash("Invalid status selected.", "danger")
        return redirect(url_for('teacher.view_class', class_id=class_obj.id))
    
    try:
        assignment.status = new_status
        db.session.commit()
        
        flash(f'Assignment status changed to {new_status} successfully.', 'success')
        return redirect(url_for('teacher.my_assignments'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing assignment status: {str(e)}', 'danger')
        return redirect(url_for('teacher.my_assignments'))


@teacher_blueprint.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to grade this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get only students enrolled in this specific class
    enrolled_students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_obj.id,
        Enrollment.is_active == True
    ).order_by(Student.last_name, Student.first_name).all()
    
    if not enrolled_students:
        flash("No students are currently enrolled in this class.", "warning")
        return redirect(url_for('teacher.view_class', class_id=class_obj.id))
    
    students = enrolled_students
    
    if request.method == 'POST':
        for student in students:
            score = request.form.get(f'score_{student.id}')
            comment = request.form.get(f'comment_{student.id}')
            
            if score is not None:
                try:
                    score_val = float(score) if score else 0.0
                    grade_data = json.dumps({'score': score_val, 'comment': comment})
                    
                    grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()
                    if grade:
                        grade.grade_data = grade_data
                    else:
                        # Create grade using attribute assignment
                        grade = Grade()
                        grade.student_id = student.id
                        grade.assignment_id = assignment_id
                        grade.grade_data = grade_data
                        db.session.add(grade)
                    
                    # Create notification for the student
                    if student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='grade',
                            title=f'Grade posted for {assignment.title}',
                            message=f'Your grade for "{assignment.title}" has been posted. Score: {score_val}%',
                            link=url_for('student.student_grades')
                        )
                        
                except ValueError:
                    flash(f"Invalid score format for student {student.id}.", "warning")
                    continue # Skip this student and continue with others
        
        db.session.commit()
        flash('Grades updated successfully.', 'success')
        return redirect(url_for('teacher.grade_assignment', assignment_id=assignment_id))

    # Get existing grades for this assignment
    grades = {g.student_id: json.loads(g.grade_data) for g in Grade.query.filter_by(assignment_id=assignment_id).all()}
    submissions = {s.student_id: s for s in Submission.query.filter_by(assignment_id=assignment_id).all()}
    
    return render_template('teacher_grade_assignment.html', 
                         assignment=assignment, 
                         class_obj=class_obj,
                         students=students, 
                         grades=grades, 
                         submissions=submissions)


@teacher_blueprint.route('/attendance/take/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def take_attendance(class_id):
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if class is active (has an active school year)
    if not hasattr(class_obj, 'school_year_id') or not class_obj.school_year_id:
        flash("This class is not associated with an active school year.", "warning")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Check if class is archived or inactive
    if hasattr(class_obj, 'is_active') and not class_obj.is_active:
        flash("This class is archived or inactive. Cannot take attendance.", "warning")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    teacher = get_teacher_or_admin()
    # Directors and School Administrators can take attendance for any class
    if not is_admin() and teacher and class_obj.teacher_id != teacher.id:
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get only students enrolled in this specific class
    enrolled_students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_id,
        Enrollment.is_active == True
    ).order_by(Student.last_name, Student.first_name).all()
    
    if not enrolled_students:
        flash("No students are currently enrolled in this class.", "warning")
        return redirect(url_for('teacher.view_class', class_id=class_id))
    
    students = enrolled_students
    
    # Additional validation - ensure class has active enrollment
    active_enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).count()
    if active_enrollments == 0:
        flash("This class has no active enrollments. Cannot take attendance.", "warning")
        return redirect(url_for('teacher.view_class', class_id=class_id))
    statuses = [
        "Present",
        "Late",
        "Unexcused Absence",
        "Excused Absence",
        "Suspended"
    ]

    attendance_date_str = request.args.get('date') or request.form.get('attendance_date')
    if not attendance_date_str:
        attendance_date_str = datetime.now().strftime('%Y-%m-%d')
    
    try:
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD format.", "danger")
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
    
    # Check if date is not in the future
    if attendance_date > datetime.now().date():
        flash("Cannot take attendance for future dates.", "warning")
        attendance_date_str = datetime.now().strftime('%Y-%m-%d')
        attendance_date = datetime.now().date()

    # Load existing records for this class/date
    existing_records = {rec.student_id: rec for rec in Attendance.query.filter_by(class_id=class_id, date=attendance_date).all()}
    
    # Load school-day attendance records for the same date
    school_day_records = {}
    if attendance_date:
        school_day_attendance = SchoolDayAttendance.query.filter_by(date=attendance_date).all()
        school_day_records = {record.student_id: record for record in school_day_attendance}
    
    # Calculate attendance statistics
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == "Present")
    late_count = sum(1 for record in existing_records.values() if record.status == "Late")
    absent_count = sum(1 for record in existing_records.values() if record.status in ["Unexcused Absence", "Excused Absence"])
    suspended_count = sum(1 for record in existing_records.values() if record.status == "Suspended")
    
    attendance_stats = {
        'total': total_students,
        'present': present_count,
        'late': late_count,
        'absent': absent_count,
        'suspended': suspended_count,
        'present_percentage': round((present_count / total_students * 100) if total_students > 0 else 0, 1)
    }

    if request.method == 'POST':
        attendance_saved = False
        valid_statuses = ["Present", "Late", "Unexcused Absence", "Excused Absence", "Suspended"]
        
        for student in students:
            status = request.form.get(f'status-{student.id}')
            notes = request.form.get(f'notes-{student.id}')
            
            if not status:
                continue
                
            # Validate status
            if status not in valid_statuses:
                flash(f"Invalid attendance status for {student.first_name} {student.last_name}.", "warning")
                continue
            
            # Validate that the student is still enrolled in this class
            enrollment = Enrollment.query.filter_by(
                student_id=student.id, 
                class_id=class_id, 
                is_active=True
            ).first()
            
            if not enrollment:
                flash(f'Student {student.first_name} {student.last_name} is no longer enrolled in this class.', 'warning')
                continue
            
            # Check if record exists
            record = Attendance.query.filter_by(student_id=student.id, class_id=class_id, date=attendance_date).first()
            if record:
                record.status = status
                record.notes = notes
                record.teacher_id = teacher.id if teacher else None
            else:
                record = Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    date=attendance_date,
                    status=status,
                    notes=notes,
                    teacher_id=teacher.id if teacher else None
                )
                db.session.add(record)
            attendance_saved = True
            
            # Check for duplicate records (safety check)
            duplicate_count = Attendance.query.filter_by(
                student_id=student.id, 
                class_id=class_id, 
                date=attendance_date
            ).count()
            
            if duplicate_count > 1:
                flash(f"Warning: Multiple attendance records found for {student.first_name} {student.last_name} on {attendance_date_str}. Please contact administration.", "warning")
        
        if attendance_saved:
            try:
                db.session.commit()
                flash('Attendance recorded successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error saving attendance. Please try again.', 'danger')
                print(f"Error saving attendance: {e}")
        else:
            flash('No attendance data was submitted.', 'warning')
        
        return redirect(url_for('teacher.view_class', class_id=class_id))

    return render_template(
        'take_attendance_improved.html',
        class_item=class_obj,
        students=students,
        attendance_date_str=attendance_date_str,
        statuses=statuses,
        existing_records=existing_records,
        school_day_records=school_day_records,
        attendance_stats=attendance_stats
    )

@teacher_blueprint.route('/classes')
@login_required
@teacher_required
def my_classes():
    """View all classes taught by the teacher, or all classes for Directors and School Administrators"""
    teacher = get_teacher_or_admin()
    
    # Directors and School Administrators see all classes, teachers only see their assigned classes
    if current_user.role in ['Director', 'School Administrator']:
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher, 
                         classes=classes,
                         section='classes',
                         active_tab='classes')

def update_assignment_statuses():
    """Automatically update assignment statuses based on due dates"""
    from datetime import datetime
    now = datetime.now()
    
    try:
        # Only update assignments that are past due and currently Active to Inactive
        # This preserves manual status changes (Inactive, Voided)
        past_due_assignments = Assignment.query.filter(
            Assignment.due_date < now,
            Assignment.status == 'Active'
        ).all()
        
        for assignment in past_due_assignments:
            assignment.status = 'Inactive'
        
        if past_due_assignments:
            db.session.commit()
            print(f"Updated {len(past_due_assignments)} assignments to Inactive status")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error updating assignment statuses: {e}")

@teacher_blueprint.route('/assignments')
@login_required
@teacher_required
def my_assignments():
    """View all assignments created by the teacher, or all assignments for Directors"""
    teacher = get_teacher_or_admin()
    
    # Update assignment statuses before displaying (only for Active assignments past due)
    update_assignment_statuses()
    
    # Get filter and sort parameters
    class_filter = request.args.get('class_id', '')
    sort_by = request.args.get('sort', 'due_date')  # 'due_date' or 'title'
    sort_order = request.args.get('order', 'desc')  # 'asc' or 'desc'
    
    # Directors see all classes and assignments, teachers only see their assigned ones
    if current_user.role == 'Director':
        classes = Class.query.all()
        assignments_query = Assignment.query
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in classes]
        assignments_query = Assignment.query.filter(Assignment.class_id.in_(class_ids))
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
        assignments_query = Assignment.query.filter(Assignment.id == -1)  # No results
    
    # Apply class filter if specified
    if class_filter:
        assignments_query = assignments_query.filter(Assignment.class_id == int(class_filter))
    
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
    
    assignments = assignments_query.all()
    
    from datetime import datetime
    return render_template('teacher_assignments.html',
                         teacher=teacher,
                         classes=classes,
                         assignments=assignments,
                         today=datetime.now(),
                         section='assignments',
                         active_tab='assignments',
                         now=datetime.now(),
                         selected_class_id=class_filter,
                         sort_by=sort_by,
                         sort_order=sort_order)

@teacher_blueprint.route('/class/<int:class_id>/students')
@login_required
@teacher_required
def get_class_students(class_id):
    """Get students for a specific class"""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Authorization check
        teacher = get_teacher_or_admin()
        if current_user.role != 'Director' and class_obj.teacher_id != teacher.id:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        # Get students enrolled in this class
        students = Student.query.join(Enrollment).filter(
            Enrollment.class_id == class_id,
            Enrollment.is_active == True
        ).all()
        
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'student_id': student.student_id
            })
        
        return jsonify({'success': True, 'students': students_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@teacher_blueprint.route('/grant-extensions', methods=['POST'])
@login_required
@teacher_required
def grant_extensions():
    """Grant extensions to selected students for an assignment"""
    try:
        assignment_id = request.form.get('assignment_id')
        extended_due_date_str = request.form.get('extended_due_date')
        reason = request.form.get('reason', '')
        student_ids = request.form.getlist('student_ids')
        
        if not assignment_id or not extended_due_date_str or not student_ids:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        # Parse the extended due date
        from datetime import datetime
        extended_due_date = datetime.fromisoformat(extended_due_date_str.replace('Z', '+00:00'))
        
        # Get assignment and verify authorization
        assignment = Assignment.query.get_or_404(assignment_id)
        teacher = get_teacher_or_admin()
        
        if current_user.role != 'Director' and assignment.class_info.teacher_id != teacher.id:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        # Grant extensions to selected students
        granted_count = 0
        for student_id in student_ids:
            # Check if extension already exists and deactivate it
            existing_extension = AssignmentExtension.query.filter_by(
                assignment_id=assignment_id,
                student_id=student_id,
                is_active=True
            ).first()
            
            if existing_extension:
                existing_extension.is_active = False
            
            # Create new extension
            extension = AssignmentExtension(
                assignment_id=assignment_id,
                student_id=student_id,
                extended_due_date=extended_due_date,
                reason=reason,
                granted_by=teacher.id
            )
            
            db.session.add(extension)
            granted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Extensions granted to {granted_count} student(s)',
            'granted_count': granted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@teacher_blueprint.route('/grades')
@login_required
@teacher_required
def my_grades():
    """View all grades entered by the teacher, or all grades for Directors"""
    teacher = get_teacher_or_admin()
    
    # Directors see all classes, assignments, and grades, teachers only see their assigned ones
    if current_user.role == 'Director':
        classes = Class.query.all()
        assignments = Assignment.query.all()
        grades = Grade.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in classes]
        assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
        assignment_ids = [a.id for a in assignments]
        grades = Grade.query.filter(Grade.assignment_id.in_(assignment_ids)).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
        assignments = []
        grades = []
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher,
                         classes=classes,
                         assignments=assignments,
                         grades=grades,
                         section='grades',
                         active_tab='grades')


@teacher_blueprint.route('/student-grades')
@login_required
@teacher_required
def student_grades():
    """View detailed student grades for teacher's classes"""
    # Handle Directors and School Administrators who don't have teacher_staff_id
    if current_user.role in ['Director', 'School Administrator']:
        teacher = None
    else:
        teacher = get_teacher_or_admin()
    
    # Get the class filter if provided
    class_filter = request.args.get('class_id', type=int)
    student_filter = request.args.get('student_id', type=int)
    
    # Directors and School Administrators see all classes, teachers only see their assigned ones
    if current_user.role in ['Director', 'School Administrator']:
        classes = Class.query.all()
        if class_filter:
            classes = [c for c in classes if c.id == class_filter]
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        if class_filter:
            classes = [c for c in classes if c.id == class_filter]
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    # Get all students enrolled in these classes
    class_ids = [c.id for c in classes]
    enrollments = Enrollment.query.filter(
        Enrollment.class_id.in_(class_ids),
        Enrollment.is_active == True
    ).all()
    
    # Group students by class
    students_by_class = {}
    for enrollment in enrollments:
        # Skip enrollments where the student doesn't exist
        if not enrollment.student:
            continue
        class_id = enrollment.class_id
        if class_id not in students_by_class:
            students_by_class[class_id] = []
        students_by_class[class_id].append(enrollment.student)
    
    # Get assignments and grades for these classes
    assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
    assignment_ids = [a.id for a in assignments]
    
    # Get all grades for these assignments
    all_grades = Grade.query.filter(Grade.assignment_id.in_(assignment_ids)).all()
    
    # Organize grades by student and assignment
    grades_by_student = {}
    for grade in all_grades:
        student_id = grade.student_id
        assignment_id = grade.assignment_id
        
        if student_id not in grades_by_student:
            grades_by_student[student_id] = {}
        
        grade_data = json.loads(grade.grade_data)
        grades_by_student[student_id][assignment_id] = {
            'score': grade_data.get('score', 0),
            'feedback': grade_data.get('feedback', ''),
            'graded_at': grade.graded_at,
            'assignment': grade.assignment
        }
    
    # Calculate GPA for each student by class
    student_gpas_by_class = {}
    for class_id in class_ids:
        student_gpas_by_class[class_id] = {}
        
        # Get students in this class
        class_students = students_by_class.get(class_id, [])
        class_assignments = [a for a in assignments if a.class_id == class_id]
        class_assignment_ids = [a.id for a in class_assignments]
        
        for student in class_students:
            student_id = student.id
            # Get grades only for this class's assignments
            class_grades = {}
            for assignment_id in class_assignment_ids:
                if student_id in grades_by_student and assignment_id in grades_by_student[student_id]:
                    class_grades[assignment_id] = grades_by_student[student_id][assignment_id]
            
            # Calculate GPA for this specific class
            scores = [grade_info['score'] for grade_info in class_grades.values() if 'score' in grade_info]
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
                
                student_gpas_by_class[class_id][student_id] = sum(gpa_scores) / len(gpa_scores)
            else:
                student_gpas_by_class[class_id][student_id] = 0.0
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher,
                         classes=classes,
                         assignments=assignments,
                         students_by_class=students_by_class,
                         grades_by_student=grades_by_student,
                         student_gpas_by_class=student_gpas_by_class,
                         class_filter=class_filter,
                         student_filter=student_filter,
                         section='student-grades',
                         active_tab='student-grades')

@teacher_blueprint.route('/attendance')
@login_required
@teacher_required
def attendance():
    """View all classes for attendance taking with improved interface."""
    teacher = get_teacher_or_admin()
    
    # Directors and School Administrators see all classes, teachers only see their assigned classes
    if current_user.role in ['Director', 'School Administrator']:
        classes = Class.query.all()
    else:
        if teacher:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
        else:
            classes = []
    
    # Get today's date
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate attendance stats for each class
    for class_obj in classes:
        # Get student count
        class_obj.student_count = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active == True
        ).count()
        
        # Check if attendance was taken today
        today_attendance = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=datetime.now().date()
        ).count()
        class_obj.attendance_taken_today = today_attendance > 0
        
        # Get today's attendance stats
        if class_obj.attendance_taken_today:
            present_count = Attendance.query.filter_by(
                class_id=class_obj.id,
                date=datetime.now().date(),
                status='Present'
            ).count()
            absent_count = Attendance.query.filter(
                Attendance.class_id == class_obj.id,
                Attendance.date == datetime.now().date(),
                Attendance.status.in_(['Unexcused Absence', 'Excused Absence'])
            ).count()
            class_obj.today_present = present_count
            class_obj.today_absent = absent_count
        else:
            class_obj.today_present = 0
            class_obj.today_absent = 0
    
    # Calculate overall stats
    today_attendance_count = sum(1 for c in classes if c.attendance_taken_today)
    pending_classes_count = len(classes) - today_attendance_count
    
    # Calculate overall attendance rate
    total_attendance_records = Attendance.query.filter_by(date=datetime.now().date()).count()
    present_records = Attendance.query.filter_by(date=datetime.now().date(), status='Present').count()
    overall_attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    return render_template('attendance_hub_simple.html',
                         classes=classes,
                         today_date=today_date,
                         today_attendance_count=today_attendance_count,
                         pending_classes_count=pending_classes_count,
                         overall_attendance_rate=overall_attendance_rate,
                         section='attendance',
                         active_tab='attendance')

@teacher_blueprint.route('/mark-all-present/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def mark_all_present(class_id):
    """Mark all students as present for a specific class on a given date"""
    from datetime import datetime
    
    try:
        # Get the class and check if teacher is authorized
        class_obj = Class.query.get_or_404(class_id)
        
        # Check if current user is authorized for this class
        if not is_authorized_for_class(class_obj):
            flash('You are not authorized to take attendance for this class.', 'danger')
            return redirect(url_for('teacher.attendance'))
        
        # Get the date from form data or use today
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            attendance_date = datetime.now().date()
        
        # Get all enrolled students for this class
        enrolled_students = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_id,
            Enrollment.is_active == True
        ).all()
        
        if not enrolled_students:
            flash(f'No students enrolled in {class_obj.name}.', 'warning')
            return redirect(url_for('teacher.attendance'))
        
        # Process each student
        updated_count = 0
        created_count = 0
        
        for student in enrolled_students:
            # Check if attendance record already exists
            existing_record = Attendance.query.filter_by(
                student_id=student.id,
                class_id=class_id,
                date=attendance_date
            ).first()
            
            if existing_record:
                # Update existing record to Present
                existing_record.status = 'Present'
                existing_record.notes = 'Marked all present'
                updated_count += 1
            else:
                # Create new record
                new_record = Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    date=attendance_date,
                    status='Present',
                    notes='Marked all present',
                    teacher_id=class_obj.teacher_id
                )
                db.session.add(new_record)
                created_count += 1
        
        # Commit changes
        db.session.commit()
        
        if created_count > 0 and updated_count > 0:
            flash(f'Successfully marked {created_count + updated_count} students as present for {class_obj.name}.', 'success')
        elif created_count > 0:
            flash(f'Successfully marked {created_count} students as present for {class_obj.name}.', 'success')
        elif updated_count > 0:
            flash(f'Successfully updated {updated_count} students to present for {class_obj.name}.', 'success')
        else:
            flash(f'No students to mark present for {class_obj.name}.', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error marking students as present: {str(e)}', 'danger')
    
    # Redirect back to teacher attendance
    return redirect(url_for('teacher.attendance'))

@teacher_blueprint.route('/quick-attendance/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def quick_attendance(class_id):
    """Handle quick attendance actions like marking all present."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    teacher = get_teacher_or_admin()
    if not is_admin() and teacher and class_obj.teacher_id != teacher.id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.get_json()
    action = data.get('action')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    
    # Get enrolled students
    students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_id,
        Enrollment.is_active == True
    ).all()
    
    if action == 'mark_all_present':
        # Delete existing records for this date
        Attendance.query.filter_by(class_id=class_id, date=attendance_date).delete()
        
        # Create new records
        for student in students:
            attendance = Attendance(
                student_id=student.id,
                class_id=class_id,
                date=attendance_date,
                status='Present',
                notes='Bulk marked as present'
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All students marked as present',
            'present_count': len(students),
            'absent_count': 0
        })
    
    return jsonify({'success': False, 'message': 'Unknown action'}), 400

@teacher_blueprint.route('/students')
@login_required
@teacher_required
def students_directory():
    """View students directory with enhanced search functionality"""
    # Get search parameters
    search_query = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'all')
    grade_filter = request.args.get('grade_filter', '')
    status_filter = request.args.get('status_filter', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Build the query
    query = Student.query
    
    # Apply search filter if query exists
    if search_query:
        if search_type == 'all':
            search_filter = db.or_(
                Student.first_name.ilike(f'%{search_query}%'),
                Student.last_name.ilike(f'%{search_query}%'),
                Student.middle_initial.ilike(f'%{search_query}%'),
                Student.email.ilike(f'%{search_query}%'),
                Student.phone.ilike(f'%{search_query}%'),
                Student.student_id.ilike(f'%{search_query}%'),
                Student.grade_level.ilike(f'%{search_query}%'),
                Student.street.ilike(f'%{search_query}%'),
                Student.city.ilike(f'%{search_query}%'),
                Student.state.ilike(f'%{search_query}%'),
                Student.zip_code.ilike(f'%{search_query}%'),
                Student.emergency_first_name.ilike(f'%{search_query}%'),
                Student.emergency_last_name.ilike(f'%{search_query}%'),
                Student.emergency_phone.ilike(f'%{search_query}%'),
                Student.emergency_relationship.ilike(f'%{search_query}%')
            )
        elif search_type == 'name':
            search_filter = db.or_(
                Student.first_name.ilike(f'%{search_query}%'),
                Student.last_name.ilike(f'%{search_query}%'),
                Student.middle_initial.ilike(f'%{search_query}%')
            )
        elif search_type == 'contact':
            search_filter = db.or_(
                Student.email.ilike(f'%{search_query}%'),
                Student.phone.ilike(f'%{search_query}%')
            )
        elif search_type == 'academic':
            search_filter = db.or_(
                Student.grade_level.ilike(f'%{search_query}%'),
                Student.student_id.ilike(f'%{search_query}%')
            )
        elif search_type == 'address':
            search_filter = db.or_(
                Student.street.ilike(f'%{search_query}%'),
                Student.city.ilike(f'%{search_query}%'),
                Student.state.ilike(f'%{search_query}%'),
                Student.zip_code.ilike(f'%{search_query}%')
            )
        elif search_type == 'emergency':
            search_filter = db.or_(
                Student.emergency_first_name.ilike(f'%{search_query}%'),
                Student.emergency_last_name.ilike(f'%{search_query}%'),
                Student.emergency_phone.ilike(f'%{search_query}%'),
                Student.emergency_relationship.ilike(f'%{search_query}%')
            )
        elif search_type == 'student_id':
            search_filter = Student.student_id.ilike(f'%{search_query}%')
        else:
            search_filter = db.or_(
                Student.first_name.ilike(f'%{search_query}%'),
                Student.last_name.ilike(f'%{search_query}%'),
                Student.email.ilike(f'%{search_query}%'),
                Student.student_id.ilike(f'%{search_query}%')
            )
        query = query.filter(search_filter)
    
    # Apply grade filter
    if grade_filter:
        query = query.filter(Student.grade_level == grade_filter)
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter(Student.user_id.isnot(None))
    elif status_filter == 'inactive':
        query = query.filter(Student.user_id.is_(None))
    elif status_filter == 'no_account':
        query = query.filter(Student.user_id.is_(None))
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'desc':
            query = query.order_by(Student.last_name.desc(), Student.first_name.desc())
        else:
            query = query.order_by(Student.last_name, Student.first_name)
    elif sort_by == 'grade':
        if sort_order == 'desc':
            query = query.order_by(Student.grade_level.desc(), Student.last_name)
        else:
            query = query.order_by(Student.grade_level, Student.last_name)
    elif sort_by == 'student_id':
        if sort_order == 'desc':
            query = query.order_by(Student.student_id.desc())
        else:
            query = query.order_by(Student.student_id)
    else:  # default to name
        query = query.order_by(Student.last_name, Student.first_name)
    
    students = query.all()
    
    # Calculate GPAs for students
    student_gpas = {}
    for student in students:
        student_gpas[student.id] = calculate_student_gpa(student.id)
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=current_user,
                         students=students,
                         student_gpas=student_gpas,
                         search_query=search_query,
                         search_type=search_type,
                         grade_filter=grade_filter,
                         status_filter=status_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         section='students',
                         active_tab='students')

@teacher_blueprint.route('/teachers-staff')
@login_required
@teacher_required
def teachers_staff_directory():
    """View teachers and staff directory with search functionality"""
    search_query = request.args.get('search', '').strip()
    
    # Build the query
    query = TeacherStaff.query
    
    # Apply search filter if query exists
    if search_query:
        search_filter = db.or_(
            TeacherStaff.first_name.ilike(f'%{search_query}%'),
            TeacherStaff.last_name.ilike(f'%{search_query}%'),
            TeacherStaff.email.ilike(f'%{search_query}%'),
            TeacherStaff.assigned_role.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # Order by last name, then first name
    teachers_staff = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=current_user,
                         teachers_staff=teachers_staff,
                         search_query=search_query,
                         section='teachers-staff',
                         active_tab='teachers-staff')

@teacher_blueprint.route('/calendar')
@login_required
@teacher_required
def calendar():
    """View school calendar"""
    from datetime import datetime, timedelta, date
    import calendar as cal
    
    # Try to import holidays module, with fallback
    try:
        import holidays as pyholidays
        holidays_available = True
    except ImportError:
        holidays_available = False
        pyholidays = None
        print("Warning: holidays module not available. Calendar will show limited holiday information.")
    
    # Import all required models at the top of the function
    from models import AcademicPeriod, CalendarEvent

    def get_religious_holidays(year):
        jewish = [
            (date(year, 4, 23), "Passover (Pesach)"),
            (date(year, 9, 16), "Rosh Hashanah"),
            (date(year, 9, 25), "Yom Kippur"),
            (date(year, 9, 30), "Sukkot"),
            (date(year, 12, 25), "Hanukkah (start)")
        ]
        christian = [
            (date(year, 12, 25), "Christmas"),
            (date(year, 4, 20), "Easter"),
            (date(year, 12, 24), "Christmas Eve"),
            (date(year, 1, 6), "Epiphany"),
            (date(year, 4, 18), "Good Friday")
        ]
        muslim = [
            (date(year, 3, 10), "Ramadan Begins"),
            (date(year, 4, 9), "Eid al-Fitr"),
            (date(year, 6, 16), "Eid al-Adha")
        ]
        return jewish + christian + muslim

    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')

    # Get academic dates from the database
    academic_dates = []
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if active_year:
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
                academic_dates.append((period.start_date.day, f"{period.name} Start", 'Academic Period'))
            
            # Add end date event
            if period.end_date.month == month:
                academic_dates.append((period.end_date.day, f"{period.name} End", 'Academic Period'))
        
        # Get calendar events for this month
        calendar_events = CalendarEvent.query.filter(
            CalendarEvent.school_year_id == active_year.id,
            CalendarEvent.start_date <= end_of_month,
            CalendarEvent.end_date >= start_of_month
        ).all()
        
        for event in calendar_events:
            if event.start_date.month == month:
                academic_dates.append((event.start_date.day, event.name, event.event_type.replace('_', ' ').title()))
    
    religious_holidays = get_religious_holidays(year)
    holidays_this_month = []
    
    # Add religious holidays
    for hol_date, hol_name in religious_holidays:
        if hol_date.month == month:
            holidays_this_month.append((hol_date.day, hol_name))
    
    # Add US Federal holidays if holidays module is available
    if holidays_available and pyholidays:
        try:
            us_holidays = pyholidays.country_holidays('US', years=[year])
            
            # Add US Federal holidays with "No School" for weekdays during school year
            school_year_start = date(year, 8, 1)  # August 1st
            school_year_end = date(year, 6, 30)   # June 30th
            
            for hol_date, hol_name in us_holidays.items():
                if hol_date.month == month:
                    # Check if it's a weekday (Monday=0, Sunday=6)
                    is_weekday = hol_date.weekday() < 5
                    # Check if it's during school year
                    is_school_year = (hol_date >= school_year_start and hol_date <= school_year_end) or \
                                   (hol_date >= date(year-1, 8, 1) and hol_date <= date(year, 6, 30))
                    
                    if is_weekday and is_school_year:
                        holidays_this_month.append((hol_date.day, f"{hol_name} - No School"))
                    else:
                        holidays_this_month.append((hol_date.day, hol_name))
        except Exception as e:
            print(f"Error processing US holidays: {e}")
            # Continue without US holidays

    calendar_data = {
        'month_name': month_name,
        'year': year,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'weeks': []
    }
    for week in cal_obj:
        week_data = []
        for day in week:
            events = []
            if day != 0:
                # Add academic dates
                for acad_day, acad_name, acad_category in academic_dates:
                    if day == acad_day:
                        events.append({'title': acad_name, 'category': acad_category})
                
                # Add holidays
                for hol_day, hol_name in holidays_this_month:
                    if day == hol_day:
                        events.append({'title': hol_name, 'category': 'Holiday'})
            if day == 0:
                week_data.append({'day_num': '', 'is_current_month': False, 'is_today': False, 'events': []})
            else:
                is_today = (day == datetime.now().day and month == datetime.now().month and year == datetime.now().year)
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': events})
        calendar_data['weeks'].append(week_data)

    return render_template('role_teacher_dashboard.html',
                         teacher=current_user,
                         calendar_data=calendar_data,
                         month_name=month_name,
                         year=year,
                         prev_month=prev_month,
                         next_month=next_month,
                         section='calendar',
                         active_tab='calendar')

# Enhanced Communications Routes
@teacher_blueprint.route('/communications')
@login_required
@teacher_required
def teacher_communications():
    """Communications tab - Under Development."""
    return render_template('under_development.html',
                         section='communications',
                         active_tab='communications')


@teacher_blueprint.route('/messages')
@login_required
@teacher_required
def teacher_messages():
    """View all messages with filtering and sorting."""
    teacher = get_teacher_or_admin()
    
    # Get filter parameters
    message_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'date')
    
    # Build query
    query = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    )
    
    # Apply filters
    if message_type != 'all':
        query = query.filter(Message.message_type == message_type)
    
    if status == 'unread':
        query = query.filter(Message.is_read == False)
    elif status == 'read':
        query = query.filter(Message.is_read == True)
    
    # Apply sorting
    if sort_by == 'date':
        query = query.order_by(Message.created_at.desc())
    elif sort_by == 'sender':
        query = query.order_by(Message.sender_id)
    elif sort_by == 'subject':
        query = query.order_by(Message.subject)
    
    messages = query.all()
    
    return render_template('teacher_messages.html',
                         teacher=teacher,
                         messages=messages,
                         message_type=message_type,
                         status=status,
                         sort_by=sort_by,
                         section='communications',
                         active_tab='messages')


@teacher_blueprint.route('/messages/send', methods=['GET', 'POST'])
@login_required
@teacher_required
def send_message():
    """Send a new message."""
    teacher = get_teacher_or_admin()
    
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        message_type = request.form.get('message_type', 'direct')
        group_id = request.form.get('group_id', type=int)
        
        if not content:
            flash('Message content is required.', 'error')
            return redirect(url_for('teacher.send_message'))
        
        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id if message_type == 'direct' else None,
            subject=subject,
            content=content,
            message_type=message_type,
            group_id=group_id if message_type == 'group' else None
        )
        
        db.session.add(message)
        
        # Handle file attachments
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"msg_{message.id}_{int(time.time())}_{filename}"
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        try:
                            file.save(filepath)
                            attachment = MessageAttachment(
                                message_id=message.id,
                                filename=unique_filename,
                                original_filename=filename,
                                file_path=filepath,
                                file_size=os.path.getsize(filepath),
                                mime_type=file.content_type
                            )
                            db.session.add(attachment)
                        except Exception as e:
                            current_app.logger.error(f"File upload failed: {e}")
        
        db.session.commit()
        
        # Create notification for recipient
        if message_type == 'direct' and recipient_id:
            notification = Notification(
                user_id=recipient_id,
                type='message',
                title=f'New message from {teacher.first_name} {teacher.last_name}',
                message=content[:100] + '...' if len(content) > 100 else content,
                message_id=message.id
            )
            db.session.add(notification)
            db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('teacher.teacher_messages'))
    
    # Get potential recipients
    students = Student.query.all()
    teachers = TeacherStaff.query.all()
    groups = MessageGroup.query.filter_by(is_active=True).all()
    
    return render_template('teacher_send_message.html',
                         teacher=teacher,
                         students=students,
                         teachers=teachers,
                         groups=groups,
                         section='communications',
                         active_tab='messages')


@teacher_blueprint.route('/messages/<int:message_id>')
@login_required
@teacher_required
def view_message(message_id):
    """View a specific message."""
    teacher = get_teacher_or_admin()
    message = Message.query.get_or_404(message_id)
    
    # Check if user has access to this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        abort(403)
    
    # Mark as read if user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('teacher_view_message.html',
                         teacher=teacher,
                         message=message,
                         section='communications',
                         active_tab='messages')


@teacher_blueprint.route('/messages/<int:message_id>/reply', methods=['POST'])
@login_required
@teacher_required
def reply_to_message(message_id):
    """Reply to a message."""
    original_message = Message.query.get_or_404(message_id)
    
    # Check if user has access to this message
    if original_message.recipient_id != current_user.id and original_message.sender_id != current_user.id:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Reply content is required.', 'error')
        return redirect(url_for('teacher.view_message', message_id=message_id))
    
    # Determine recipient
    if original_message.sender_id == current_user.id:
        recipient_id = original_message.recipient_id
    else:
        recipient_id = original_message.sender_id
    
    # Create reply
    reply = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        subject=f"Re: {original_message.subject}" if original_message.subject else "Re: Message",
        content=content,
        message_type='direct'
    )
    
    db.session.add(reply)
    db.session.commit()
    
    # Create notification
    notification = Notification(
        user_id=recipient_id,
        type='message',
        title=f'Reply from {current_user.username}',
        message=content[:100] + '...' if len(content) > 100 else content,
        message_id=reply.id
    )
    db.session.add(notification)
    db.session.commit()
    
    flash('Reply sent successfully!', 'success')
    return redirect(url_for('teacher.view_message', message_id=message_id))


@teacher_blueprint.route('/groups')
@login_required
@teacher_required
def teacher_groups():
    """Manage message groups."""
    teacher = get_teacher_or_admin()
    
    # Get groups the teacher is part of
    group_memberships = MessageGroupMember.query.filter_by(user_id=current_user.id).all()
    groups = [membership.group for membership in group_memberships if membership.group.is_active]
    
    # Get teacher's classes for creating new groups
    if teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    return render_template('teacher_groups.html',
                         teacher=teacher,
                         groups=groups,
                         classes=classes,
                         section='communications',
                         active_tab='groups')


@teacher_blueprint.route('/message-groups/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_message_group():
    """Create a new message group."""
    teacher = get_teacher_or_admin()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        group_type = request.form.get('group_type', 'class')
        class_id = request.form.get('class_id', type=int)
        
        if not name:
            flash('Group name is required.', 'error')
            return redirect(url_for('teacher.create_message_group'))
        
        # Create group
        group = MessageGroup(
            name=name,
            description=description,
            group_type=group_type,
            class_id=class_id,
            created_by=current_user.id
        )
        
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add creator as admin member
        member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(member)
        
        # Add class members if it's a class group
        if class_id and group_type == 'class':
            class_obj = Class.query.get(class_id)
            if class_obj:
                # Add teacher
                if class_obj.teacher and class_obj.teacher.user:
                    member = MessageGroupMember(
                        group_id=group.id,
                        user_id=class_obj.teacher.user.id,
                        is_admin=True
                    )
                    db.session.add(member)
                
                # Add only students enrolled in this specific class
                enrolled_students = db.session.query(Student).join(Enrollment).filter(
                    Enrollment.class_id == class_id,
                    Enrollment.is_active == True
                ).order_by(Student.last_name, Student.first_name).all()
                
                for student in enrolled_students:
                    if student.user:
                        member = MessageGroupMember(
                            group_id=group.id,
                            user_id=student.user.id,
                            is_admin=False
                        )
                        db.session.add(member)
        
        db.session.commit()
        flash('Group created successfully!', 'success')
        return redirect(url_for('teacher.teacher_groups'))
    
    # Directors can create groups for any class
    if current_user.role == 'Director':
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    return render_template('teacher_create_group.html',
                         teacher=teacher,
                         classes=classes,
                         section='communications',
                         active_tab='groups')


@teacher_blueprint.route('/groups/<int:group_id>')
@login_required
@teacher_required
def view_group(group_id):
    """View a message group and its messages."""
    teacher = get_teacher_or_admin()
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.created_at.desc()).all()
    
    # Get group members
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    
    return render_template('teacher_view_group.html',
                         teacher=teacher,
                         group=group,
                         messages=messages,
                         members=members,
                         membership=membership,
                         section='communications',
                         active_tab='groups')


@teacher_blueprint.route('/groups/<int:group_id>/send', methods=['POST'])
@login_required
@teacher_required
def send_group_message(group_id):
    """Send a message to a group."""
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Message content is required.', 'error')
        return redirect(url_for('teacher.view_group', group_id=group_id))
    
    # Create group message
    message = Message(
        sender_id=current_user.id,
        content=content,
        message_type='group',
        group_id=group_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Create notifications for all group members except sender
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        if member.user_id != current_user.id and not member.is_muted:
            notification = Notification(
                user_id=member.user_id,
                type='group_message',
                title=f'New message in {group.name}',
                message=content[:100] + '...' if len(content) > 100 else content,
                message_id=message.id
            )
            db.session.add(notification)
    
    db.session.commit()
    
    flash('Message sent to group!', 'success')
    return redirect(url_for('teacher.view_group', group_id=group_id))


@teacher_blueprint.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_announcement():
    """Create a new announcement."""
    teacher = get_teacher_or_admin()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        is_important = request.form.get('is_important', type=bool)
        requires_confirmation = request.form.get('requires_confirmation', type=bool)
        rich_content = request.form.get('rich_content', '')
        
        if not title or not message:
            flash('Title and message are required.', 'error')
            return redirect(url_for('teacher.create_announcement'))
        
        # Create announcement
        announcement = Announcement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            is_important=is_important,
            requires_confirmation=requires_confirmation,
            rich_content=rich_content
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('teacher.teacher_communications'))
    
    # Directors can create announcements for any class
    if current_user.role == 'Director':
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    return render_template('teacher_create_announcement.html',
                         teacher=teacher,
                         classes=classes,
                         section='communications',
                         active_tab='announcements')


@teacher_blueprint.route('/announcements/schedule', methods=['GET', 'POST'])
@login_required
@teacher_required
def schedule_announcement():
    """Schedule an announcement for future delivery."""
    teacher = get_teacher_or_admin()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        scheduled_for = request.form.get('scheduled_for')
        
        if not title or not message or not scheduled_for:
            flash('Title, message, and scheduled time are required.', 'error')
            return redirect(url_for('teacher.schedule_announcement'))
        
        try:
            scheduled_datetime = datetime.strptime(scheduled_for, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'error')
            return redirect(url_for('teacher.schedule_announcement'))
        
        # Create scheduled announcement
        scheduled = ScheduledAnnouncement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            scheduled_for=scheduled_datetime
        )
        
        db.session.add(scheduled)
        db.session.commit()
        
        flash('Announcement scheduled successfully!', 'success')
        return redirect(url_for('teacher.teacher_communications'))
    
    # Directors can schedule announcements for any class
    if current_user.role == 'Director':
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Teacher user without teacher_staff_id - show empty results
        classes = []
    
    return render_template('teacher_schedule_announcement.html',
                         teacher=teacher,
                         classes=classes,
                         section='communications',
                         active_tab='announcements')


@teacher_blueprint.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@teacher_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('teacher.teacher_communications'))


@teacher_blueprint.route('/messages/mark-read/<int:message_id>', methods=['POST'])
@login_required
@teacher_required
def mark_message_read(message_id):
    """Mark a message as read."""
    message = Message.query.get_or_404(message_id)
    
    # Ensure the message belongs to the current user
    if message.recipient_id != current_user.id:
        abort(403)
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    db.session.commit()
    
    flash('Message marked as read.', 'success')
    return redirect(request.referrer or url_for('teacher.teacher_messages'))


@teacher_blueprint.route('/settings')
@login_required
@teacher_required
def settings():
    """Teacher settings page."""
    teacher = get_teacher_or_admin()
    
    return render_template('teacher_settings.html',
                         teacher=teacher,
                         section='settings',
                         active_tab='settings')


# ===== GROUP MANAGEMENT ROUTES =====

@teacher_blueprint.route('/class/<int:class_id>/groups')
@login_required
@teacher_required
def class_groups(class_id):
    """View all groups for a specific class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all groups for this class
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    
    # Get enrolled students for this class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    return render_template('teacher_class_groups.html',
                         class_obj=class_obj,
                         groups=groups,
                         enrolled_students=enrolled_students)


@teacher_blueprint.route('/class/<int:class_id>/groups/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_student_group(class_id):
    """Create a new group for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        max_students = request.form.get('max_students')
        
        if not name:
            flash('Group name is required.', 'danger')
            return render_template('teacher_create_group.html', class_obj=class_obj)
        
        # Check if group name already exists for this class
        existing_group = StudentGroup.query.filter_by(class_id=class_id, name=name, is_active=True).first()
        if existing_group:
            flash('A group with this name already exists in this class.', 'danger')
            return render_template('teacher_create_group.html', class_obj=class_obj)
        
        # Create the group
        group = StudentGroup(
            name=name,
            description=description,
            class_id=class_id,
            created_by=teacher.id,
            max_students=int(max_students) if max_students else None
        )
        
        db.session.add(group)
        db.session.commit()
        
        flash(f'Group "{name}" created successfully!', 'success')
        return redirect(url_for('teacher.class_groups', class_id=class_id))
    
    return render_template('teacher_create_group.html', class_obj=class_obj)


@teacher_blueprint.route('/group/<int:group_id>/manage', methods=['GET', 'POST'])
@login_required
@teacher_required
def manage_group(group_id):
    """Manage students in a specific group."""
    teacher = get_teacher_or_admin()
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check if teacher has access to this group's class
    if not is_admin() and group.class_info.teacher_id != teacher.id:
        flash('You do not have access to this group.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get current group members
    current_members = StudentGroupMember.query.filter_by(group_id=group_id).all()
    current_member_ids = [member.student_id for member in current_members]
    
    # Get all enrolled students for this class
    enrollments = Enrollment.query.filter_by(class_id=group.class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    if request.method == 'POST':
        # Handle adding/removing students
        action = request.form.get('action')
        
        if action == 'add_student':
            student_id = request.form.get('student_id')
            if student_id and int(student_id) not in current_member_ids:
                # Check if group has reached max capacity
                if group.max_students and len(current_members) >= group.max_students:
                    flash('Group has reached maximum capacity.', 'warning')
                else:
                    # Add student to group
                    member = StudentGroupMember(
                        group_id=group_id,
                        student_id=int(student_id)
                    )
                    db.session.add(member)
                    db.session.commit()
                    flash('Student added to group successfully!', 'success')
                    return redirect(url_for('teacher.manage_group', group_id=group_id))
        
        elif action == 'remove_student':
            student_id = request.form.get('student_id')
            if student_id:
                member = StudentGroupMember.query.filter_by(
                    group_id=group_id, 
                    student_id=int(student_id)
                ).first()
                if member:
                    db.session.delete(member)
                    db.session.commit()
                    flash('Student removed from group successfully!', 'success')
                    return redirect(url_for('teacher.manage_group', group_id=group_id))
        
        elif action == 'set_leader':
            student_id = request.form.get('student_id')
            if student_id:
                # Remove leader status from all members
                StudentGroupMember.query.filter_by(group_id=group_id).update({'is_leader': False})
                
                # Set new leader
                member = StudentGroupMember.query.filter_by(
                    group_id=group_id, 
                    student_id=int(student_id)
                ).first()
                if member:
                    member.is_leader = True
                    db.session.commit()
                    flash('Group leader updated successfully!', 'success')
                    return redirect(url_for('teacher.manage_group', group_id=group_id))
    
    return render_template('teacher_manage_group.html',
                         group=group,
                         current_members=current_members,
                         enrolled_students=enrolled_students,
                         current_member_ids=current_member_ids)


@teacher_blueprint.route('/group/<int:group_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_group(group_id):
    """Delete a group (soft delete by setting is_active=False)."""
    teacher = get_teacher_or_admin()
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check if teacher has access to this group's class
    if not is_admin() and group.class_info.teacher_id != teacher.id:
        flash('You do not have access to this group.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Soft delete the group
    group.is_active = False
    db.session.commit()
    
    flash(f'Group "{group.name}" deleted successfully!', 'success')
    return redirect(url_for('teacher.class_groups', class_id=group.class_id))


# ===== GROUP ASSIGNMENT ROUTES =====

@teacher_blueprint.route('/class/<int:class_id>/group-assignments')
@login_required
@teacher_required
def class_group_assignments(class_id):
    """View all group assignments for a specific class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true'
    
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
        # Handle case where tables don't exist yet
        flash('Group assignments feature is not yet available. Please run the database migration first.', 'warning')
        group_assignments = []
    
    return render_template('teacher_class_group_assignments.html',
                         class_obj=class_obj,
                         group_assignments=group_assignments,
                         moment=datetime.utcnow(),
                         admin_view=admin_view)


@teacher_blueprint.route('/class/<int:class_id>/group-assignment/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group_assignment(class_id):
    """Create a new group assignment for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if teacher has access to this class
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get current school year and academic periods
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods = []
    if current_school_year:
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=current_school_year.id, is_active=True).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter', '')
        semester = request.form.get('semester', '')
        academic_period_id = request.form.get('academic_period_id')
        group_size_min = request.form.get('group_size_min', 2)
        group_size_max = request.form.get('group_size_max', 4)
        allow_individual = 'allow_individual' in request.form
        collaboration_type = request.form.get('collaboration_type', 'group')
        
        if not title or not due_date_str or not quarter:
            flash('Title, due date, and quarter are required.', 'danger')
            return render_template('teacher_create_group_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid due date format.', 'danger')
            return render_template('teacher_create_group_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods)
        
        # Handle file upload
        attachment_filename = None
        attachment_original_filename = None
        attachment_file_path = None
        attachment_file_size = None
        attachment_mime_type = None
        
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(time.time()))
                attachment_filename = f"group_assignment_{class_id}_{timestamp}_{filename}"
                attachment_original_filename = file.filename
                
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(current_app.static_folder, 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                attachment_file_path = os.path.join(upload_dir, attachment_filename)
                file.save(attachment_file_path)
                attachment_file_size = os.path.getsize(attachment_file_path)
                attachment_mime_type = file.content_type
        
        # Create the group assignment
        group_assignment = GroupAssignment(
            title=title,
            description=description,
            class_id=class_id,
            due_date=due_date,
            quarter=quarter,
            semester=semester if semester else None,
            academic_period_id=int(academic_period_id) if academic_period_id else None,
            school_year_id=current_school_year.id if current_school_year else None,
            group_size_min=int(group_size_min),
            group_size_max=int(group_size_max),
            allow_individual=allow_individual,
            collaboration_type=collaboration_type,
            attachment_filename=attachment_filename,
            attachment_original_filename=attachment_original_filename,
            attachment_file_path=attachment_file_path,
            attachment_file_size=attachment_file_size,
            attachment_mime_type=attachment_mime_type
        )
        
        db.session.add(group_assignment)
        db.session.commit()
        
        flash(f'Group assignment "{title}" created successfully!', 'success')
        return redirect(url_for('teacher.class_group_assignments', class_id=class_id))
    
    return render_template('teacher_create_group_assignment.html', 
                         class_obj=class_obj, 
                         academic_periods=academic_periods)


@teacher_blueprint.route('/group-assignment/<int:assignment_id>/view')
@login_required
@teacher_required
def view_group_assignment(assignment_id):
    """View details of a specific group assignment."""
    teacher = get_teacher_or_admin()
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Check if teacher has access to this assignment's class
    if not is_admin() and group_assignment.class_info.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get submissions for this assignment
    submissions = GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all()
    
    # Get groups for this class
    groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
    
    return render_template('teacher_view_group_assignment.html',
                         group_assignment=group_assignment,
                         submissions=submissions,
                         groups=groups)


@teacher_blueprint.route('/group-assignment/<int:assignment_id>/grade', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_group_assignment(assignment_id):
    """Grade a group assignment."""
    teacher = get_teacher_or_admin()
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Check if teacher has access to this assignment's class
    if not is_admin() and group_assignment.class_info.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all groups for this class
    groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
    
    # Get existing grades
    existing_grades = GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()
    grades_by_student = {grade.student_id: grade for grade in existing_grades}
    
    if request.method == 'POST':
        # Process grade submissions
        for group in groups:
            for member in group.members:
                student_id = member.student_id
                score_key = f'score_{student_id}'
                comments_key = f'comments_{student_id}'
                
                if score_key in request.form:
                    score = request.form.get(score_key, '').strip()
                    comments = request.form.get(comments_key, '').strip()
                    
                    if score:
                        try:
                            score_value = float(score)
                            if 0 <= score_value <= 100:
                                grade_data = json.dumps({
                                    'score': score_value,
                                    'max_score': 100,
                                    'letter_grade': get_letter_grade(score_value)
                                })
                                
                                # Update or create grade
                                if student_id in grades_by_student:
                                    grade = grades_by_student[student_id]
                                    grade.grade_data = grade_data
                                    grade.comments = comments
                                    grade.graded_at = datetime.utcnow()
                                else:
                                    grade = GroupGrade(
                                        group_assignment_id=assignment_id,
                                        group_id=group.id,
                                        student_id=student_id,
                                        grade_data=grade_data,
                                        graded_by=teacher.id,
                                        comments=comments
                                    )
                                    db.session.add(grade)
                                
                                db.session.commit()
                        except ValueError:
                            flash(f'Invalid score for {member.student.first_name} {member.student.last_name}', 'warning')
        
        flash('Grades saved successfully!', 'success')
        return redirect(url_for('teacher.view_group_assignment', assignment_id=assignment_id))
    
    return render_template('teacher_grade_group_assignment.html',
                         group_assignment=group_assignment,
                         groups=groups,
                         grades_by_student=grades_by_student)


def get_letter_grade(percentage):
    """Convert percentage to letter grade."""
    if percentage >= 97:
        return 'A+'
    elif percentage >= 93:
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


# ============================================================================
# ENHANCED GROUP MANAGEMENT FEATURES
# ============================================================================

@teacher_blueprint.route('/class/<int:class_id>/groups/analytics')
@login_required
@teacher_required
def group_analytics(class_id):
    """View group analytics and performance insights."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get groups and their performance data
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    
    # Calculate analytics
    analytics_data = []
    for group in groups:
        # Get group assignments and grades
        assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
        group_grades = GroupGrade.query.filter_by(group_id=group.id).all()
        
        # Calculate average grade
        if group_grades:
            total_score = 0
            count = 0
            for grade in group_grades:
                try:
                    grade_data = json.loads(grade.grade_data)
                    if 'score' in grade_data:
                        total_score += grade_data['score']
                        count += 1
                except:
                    continue
            
            avg_grade = total_score / count if count > 0 else 0
        else:
            avg_grade = 0
        
        # Get peer evaluations
        peer_evals = PeerEvaluation.query.filter_by(group_id=group.id).all()
        avg_peer_score = 0
        if peer_evals:
            total_peer_score = sum(eval.overall_score for eval in peer_evals)
            avg_peer_score = total_peer_score / len(peer_evals)
        
        analytics_data.append({
            'group': group,
            'member_count': len(group.members),
            'avg_grade': avg_grade,
            'avg_peer_score': avg_peer_score,
            'assignments_count': len(assignments),
            'submissions_count': len([s for s in group.submissions if s.submitted_at])
        })
    
    return render_template('teacher_group_analytics.html',
                         class_obj=class_obj,
                         analytics_data=analytics_data)


@teacher_blueprint.route('/class/<int:class_id>/groups/auto-create', methods=['GET', 'POST'])
@login_required
@teacher_required
def auto_create_groups(class_id):
    """Auto-create groups with different criteria."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        group_size = int(request.form.get('group_size', 3))
        grouping_criteria = request.form.get('grouping_criteria', 'random')
        group_prefix = request.form.get('group_prefix', 'Group')
        
        # Get enrolled students
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        if len(students) < group_size:
            flash('Not enough students to create groups of the specified size.', 'warning')
            return redirect(url_for('teacher.auto_create_groups', class_id=class_id))
        
        # Create groups based on criteria
        groups_created = 0
        if grouping_criteria == 'random':
            import random
            random.shuffle(students)
            
            for i in range(0, len(students), group_size):
                group_students = students[i:i + group_size]
                if len(group_students) >= 2:  # Minimum 2 students per group
                    group = StudentGroup(
                        name=f"{group_prefix} {groups_created + 1}",
                        description=f"Auto-created group with {len(group_students)} members",
                        class_id=class_id,
                        created_by=teacher.id,
                        max_students=group_size
                    )
                    db.session.add(group)
                    db.session.flush()  # Get the group ID
                    
                    # Add students to group
                    for j, student in enumerate(group_students):
                        member = StudentGroupMember(
                            group_id=group.id,
                            student_id=student.id,
                            is_leader=(j == 0)  # First student is leader
                        )
                        db.session.add(member)
                    
                    groups_created += 1
        
        elif grouping_criteria == 'mixed_ability':
            # Simple mixed ability grouping (would need more sophisticated logic in real implementation)
            import random
            random.shuffle(students)
            
            for i in range(0, len(students), group_size):
                group_students = students[i:i + group_size]
                if len(group_students) >= 2:
                    group = StudentGroup(
                        name=f"{group_prefix} {groups_created + 1}",
                        description=f"Mixed ability group with {len(group_students)} members",
                        class_id=class_id,
                        created_by=teacher.id,
                        max_students=group_size
                    )
                    db.session.add(group)
                    db.session.flush()
                    
                    for j, student in enumerate(group_students):
                        member = StudentGroupMember(
                            group_id=group.id,
                            student_id=student.id,
                            is_leader=(j == 0)
                        )
                        db.session.add(member)
                    
                    groups_created += 1
        
        try:
            db.session.commit()
            flash(f'Successfully created {groups_created} groups!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating groups: {str(e)}', 'danger')
        
        return redirect(url_for('teacher.class_groups', class_id=class_id))
    
    # Get enrolled students for preview
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    return render_template('teacher_auto_create_groups.html',
                         class_obj=class_obj,
                         students=students)


@teacher_blueprint.route('/class/<int:class_id>/group-templates')
@login_required
@teacher_required
def class_group_templates(class_id):
    """View and manage group templates for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    templates = GroupTemplate.query.filter_by(class_id=class_id, is_active=True).all()
    
    return render_template('teacher_group_templates.html',
                         class_obj=class_obj,
                         templates=templates)


@teacher_blueprint.route('/class/<int:class_id>/group-template/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group_template(class_id):
    """Create a new group template."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        group_size = int(request.form.get('group_size', 3))
        grouping_criteria = request.form.get('grouping_criteria', 'random')
        
        template = GroupTemplate(
            name=name,
            description=description,
            class_id=class_id,
            created_by=teacher.id,
            group_size=group_size,
            grouping_criteria=grouping_criteria
        )
        
        try:
            db.session.add(template)
            db.session.commit()
            flash('Group template created successfully!', 'success')
            return redirect(url_for('teacher.class_group_templates', class_id=class_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating template: {str(e)}', 'danger')
    
    return render_template('teacher_create_group_template.html',
                         class_obj=class_obj)


@teacher_blueprint.route('/group-assignment/<int:assignment_id>/rubric/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_assignment_rubric(assignment_id):
    """Create a rubric for a group assignment."""
    teacher = get_teacher_or_admin()
    assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Check if teacher has access to this assignment
    if not is_admin() and assignment.class_info.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        total_points = int(request.form.get('total_points', 100))
        
        # Get rubric criteria from form
        criteria = []
        criteria_names = request.form.getlist('criteria_name[]')
        criteria_descriptions = request.form.getlist('criteria_description[]')
        criteria_points = request.form.getlist('criteria_points[]')
        
        for i in range(len(criteria_names)):
            if criteria_names[i] and criteria_points[i]:
                criteria.append({
                    'name': criteria_names[i],
                    'description': criteria_descriptions[i],
                    'points': int(criteria_points[i])
                })
        
        rubric = AssignmentRubric(
            group_assignment_id=assignment_id,
            name=name,
            description=description,
            criteria_data=json.dumps(criteria),
            total_points=total_points,
            created_by=teacher.id
        )
        
        try:
            db.session.add(rubric)
            db.session.commit()
            flash('Rubric created successfully!', 'success')
            return redirect(url_for('teacher.view_group_assignment', assignment_id=assignment_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating rubric: {str(e)}', 'danger')
    
    return render_template('teacher_create_rubric.html',
                         assignment=assignment)


@teacher_blueprint.route('/group/<int:group_id>/contract/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group_contract(group_id):
    """Create a group contract."""
    teacher = get_teacher_or_admin()
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check if teacher has access to this group
    if not is_admin() and group.class_info.teacher_id != teacher.id:
        flash('You do not have access to this group.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        assignment_id = request.form.get('assignment_id')
        contract_terms = request.form.get('contract_terms')
        
        # Create contract data
        contract_data = {
            'terms': contract_terms,
            'created_by_teacher': teacher.id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        contract = GroupContract(
            group_id=group_id,
            group_assignment_id=assignment_id if assignment_id else None,
            contract_data=json.dumps(contract_data),
            created_by=teacher.id
        )
        
        try:
            db.session.add(contract)
            db.session.commit()
            flash('Group contract created successfully!', 'success')
            return redirect(url_for('teacher.manage_group', group_id=group_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating contract: {str(e)}', 'danger')
    
    # Get available assignments for this group's class
    assignments = GroupAssignment.query.filter_by(class_id=group.class_id).all()
    
    return render_template('teacher_create_group_contract.html',
                         group=group,
                         assignments=assignments)


@teacher_blueprint.route('/group-assignment/<int:assignment_id>/peer-evaluations')
@login_required
@teacher_required
def view_peer_evaluations(assignment_id):
    """View peer evaluations for a group assignment."""
    teacher = get_teacher_or_admin()
    assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Check if teacher has access to this assignment
    if not is_admin() and assignment.class_info.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all peer evaluations for this assignment
    evaluations = PeerEvaluation.query.filter_by(group_assignment_id=assignment_id).all()
    
    # Group evaluations by group
    evaluations_by_group = {}
    for eval in evaluations:
        if eval.group_id not in evaluations_by_group:
            evaluations_by_group[eval.group_id] = []
        evaluations_by_group[eval.group_id].append(eval)
    
    return render_template('teacher_peer_evaluations.html',
                         assignment=assignment,
                         evaluations_by_group=evaluations_by_group)


@teacher_blueprint.route('/group-assignment/<int:assignment_id>/progress')
@login_required
@teacher_required
def view_group_progress(assignment_id):
    """View group progress for an assignment."""
    teacher = get_teacher_or_admin()
    assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Check if teacher has access to this assignment
    if not is_admin() and assignment.class_info.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get groups and their progress
    groups = StudentGroup.query.filter_by(class_id=assignment.class_id, is_active=True).all()
    progress_data = []
    
    for group in groups:
        progress = GroupProgress.query.filter_by(
            group_id=group.id,
            group_assignment_id=assignment_id
        ).first()
        
        if not progress:
            # Create initial progress record
            progress = GroupProgress(
                group_id=group.id,
                group_assignment_id=assignment_id,
                progress_percentage=0,
                status='not_started'
            )
            db.session.add(progress)
            db.session.commit()
        
        progress_data.append({
            'group': group,
            'progress': progress,
            'submission': GroupSubmission.query.filter_by(
                group_id=group.id,
                group_assignment_id=assignment_id
            ).first()
        })
    
    return render_template('teacher_group_progress.html',
                         assignment=assignment,
                         progress_data=progress_data)


@teacher_blueprint.route('/class/<int:class_id>/group-template/delete', methods=['POST'])
@login_required
@teacher_required
def delete_group_template(class_id):
    """Delete a group template."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    template_id = request.form.get('template_id')
    if not template_id:
        flash('Template ID is required.', 'danger')
        return redirect(url_for('teacher.class_group_templates', class_id=class_id))
    
    template = GroupTemplate.query.filter_by(id=template_id, class_id=class_id).first()
    if not template:
        flash('Template not found.', 'danger')
        return redirect(url_for('teacher.class_group_templates', class_id=class_id))
    
    try:
        template.is_active = False
        db.session.commit()
        flash('Template deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting template: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_group_templates', class_id=class_id))


@teacher_blueprint.route('/group-progress/update', methods=['POST'])
@login_required
@teacher_required
def update_group_progress():
    """Update group progress."""
    teacher = get_teacher_or_admin()
    
    group_id = request.form.get('group_id')
    assignment_id = request.form.get('assignment_id')
    progress_percentage = int(request.form.get('progress_percentage', 0))
    status = request.form.get('status', 'not_started')
    notes = request.form.get('notes', '')
    
    # Verify teacher has access to this group
    group = StudentGroup.query.get_or_404(group_id)
    if not is_admin() and group.class_info.teacher_id != teacher.id:
        flash('You do not have access to this group.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Find or create progress record
    progress = GroupProgress.query.filter_by(
        group_id=group_id,
        group_assignment_id=assignment_id
    ).first()
    
    if not progress:
        progress = GroupProgress(
            group_id=group_id,
            group_assignment_id=assignment_id,
            progress_percentage=progress_percentage,
            status=status,
            notes=notes
        )
        db.session.add(progress)
    else:
        progress.progress_percentage = progress_percentage
        progress.status = status
        progress.notes = notes
        progress.last_updated = datetime.utcnow()
    
    try:
        db.session.commit()
        flash('Progress updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating progress: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.view_group_progress', assignment_id=assignment_id))


@teacher_blueprint.route('/class/<int:class_id>/assignment-templates')
@login_required
@teacher_required
def class_assignment_templates(class_id):
    """View and manage assignment templates for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    templates = AssignmentTemplate.query.filter_by(class_id=class_id, is_active=True).all()
    
    return render_template('teacher_assignment_templates.html',
                         class_obj=class_obj,
                         templates=templates)


@teacher_blueprint.route('/class/<int:class_id>/assignment-template/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_assignment_template(class_id):
    """Create a new assignment template."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Get template data from form
        template_data = {
            'title': request.form.get('title', ''),
            'description': request.form.get('template_description', ''),
            'group_size_min': int(request.form.get('group_size_min', 2)),
            'group_size_max': int(request.form.get('group_size_max', 4)),
            'allow_individual': request.form.get('allow_individual') == 'on',
            'collaboration_type': request.form.get('collaboration_type', 'group'),
            'quarter': request.form.get('quarter', ''),
            'semester': request.form.get('semester', ''),
            'due_days': int(request.form.get('due_days', 7)),
            'has_attachment': request.form.get('has_attachment') == 'on',
            'attachment_required': request.form.get('attachment_required') == 'on',
            'rubric_included': request.form.get('rubric_included') == 'on',
            'peer_evaluation': request.form.get('peer_evaluation') == 'on',
            'progress_tracking': request.form.get('progress_tracking') == 'on'
        }
        
        template = AssignmentTemplate(
            name=name,
            description=description,
            class_id=class_id,
            created_by=teacher.id,
            template_data=json.dumps(template_data)
        )
        
        try:
            db.session.add(template)
            db.session.commit()
            flash('Assignment template created successfully!', 'success')
            return redirect(url_for('teacher.class_assignment_templates', class_id=class_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating template: {str(e)}', 'danger')
    
    return render_template('teacher_create_assignment_template.html',
                         class_obj=class_obj)


@teacher_blueprint.route('/assignment-template/<int:template_id>/use', methods=['GET', 'POST'])
@login_required
@teacher_required
def use_assignment_template(template_id):
    """Use an assignment template to create a new assignment."""
    teacher = get_teacher_or_admin()
    template = AssignmentTemplate.query.get_or_404(template_id)
    
    # Check if teacher has access to this template
    if not is_admin() and template.class_info.teacher_id != teacher.id:
        flash('You do not have access to this template.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        # Get template data
        template_data = json.loads(template.template_data)
        
        # Create new assignment with template data
        assignment = GroupAssignment(
            title=request.form.get('title', template_data.get('title', '')),
            description=request.form.get('description', template_data.get('description', '')),
            class_id=template.class_id,
            due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%dT%H:%M'),
            quarter=request.form.get('quarter', template_data.get('quarter', '')),
            semester=request.form.get('semester', template_data.get('semester', '')),
            school_year_id=request.form.get('school_year_id'),
            group_size_min=template_data.get('group_size_min', 2),
            group_size_max=template_data.get('group_size_max', 4),
            allow_individual=template_data.get('allow_individual', False),
            collaboration_type=template_data.get('collaboration_type', 'group')
        )
        
        try:
            db.session.add(assignment)
            db.session.commit()
            flash('Assignment created successfully from template!', 'success')
            return redirect(url_for('teacher.view_group_assignment', assignment_id=assignment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating assignment: {str(e)}', 'danger')
    
    # Get available school years and academic periods
    school_years = SchoolYear.query.filter_by(is_active=True).all()
    academic_periods = AcademicPeriod.query.filter_by(is_active=True).all()
    template_data = json.loads(template.template_data)
    
    return render_template('teacher_use_assignment_template.html',
                         template=template,
                         template_data=template_data,
                         school_years=school_years,
                         academic_periods=academic_periods)

# Group Rotation Routes
@teacher_blueprint.route('/class/<int:class_id>/group-rotations')
@login_required
@teacher_required
def class_group_rotations(class_id):
    """View all group rotations for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    rotations = GroupRotation.query.filter_by(class_id=class_id, is_active=True).order_by(GroupRotation.created_at.desc()).all()
    
    return render_template('teacher_class_group_rotations.html',
                         class_obj=class_obj,
                         rotations=rotations)

@teacher_blueprint.route('/class/<int:class_id>/group-rotation/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group_rotation(class_id):
    """Create a new group rotation."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        rotation_name = request.form.get('rotation_name')
        description = request.form.get('description')
        rotation_type = request.form.get('rotation_type')
        rotation_frequency = request.form.get('rotation_frequency')
        group_size = int(request.form.get('group_size', 3))
        grouping_criteria = request.form.get('grouping_criteria')

        rotation = GroupRotation(
            class_id=class_id,
            rotation_name=rotation_name,
            description=description,
            rotation_type=rotation_type,
            rotation_frequency=rotation_frequency,
            group_size=group_size,
            grouping_criteria=grouping_criteria,
            created_by=teacher.id
        )

        try:
            db.session.add(rotation)
            db.session.commit()
            flash('Group rotation created successfully!', 'success')
            return redirect(url_for('teacher.class_group_rotations', class_id=class_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating group rotation: {str(e)}', 'danger')

    return render_template('teacher_create_group_rotation.html',
                         class_obj=class_obj)

@teacher_blueprint.route('/group-rotation/<int:rotation_id>/execute', methods=['POST'])
@login_required
@teacher_required
def execute_group_rotation(rotation_id):
    """Execute a group rotation."""
    teacher = get_teacher_or_admin()
    rotation = GroupRotation.query.get_or_404(rotation_id)
    class_obj = Class.query.get_or_404(rotation.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    try:
        # Get current groups
        current_groups = StudentGroup.query.filter_by(class_id=rotation.class_id, is_active=True).all()
        previous_groups_data = []
        
        for group in current_groups:
            members = [member.student_id for member in group.members]
            previous_groups_data.append({
                'group_id': group.id,
                'group_name': group.name,
                'members': members
            })

        # Get all students in the class
        enrollments = Enrollment.query.filter_by(class_id=rotation.class_id).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        if len(students) < rotation.group_size:
            flash('Not enough students for group rotation.', 'warning')
            return redirect(url_for('teacher.class_group_rotations', class_id=rotation.class_id))

        # Deactivate current groups
        for group in current_groups:
            group.is_active = False

        # Create new groups based on criteria
        new_groups = []
        if rotation.grouping_criteria == 'random':
            import random
            random.shuffle(students)
        elif rotation.grouping_criteria == 'skill_based':
            # Sort by some criteria (could be based on grades, etc.)
            students.sort(key=lambda s: s.id)  # Simple sort for now
        
        # Create groups
        for i in range(0, len(students), rotation.group_size):
            group_students = students[i:i + rotation.group_size]
            if len(group_students) >= 2:  # Minimum group size
                group = StudentGroup(
                    class_id=rotation.class_id,
                    name=f"Group {len(new_groups) + 1}",
                    is_active=True
                )
                db.session.add(group)
                db.session.flush()  # Get the group ID
                
                for student in group_students:
                    member = StudentGroupMember(
                        group_id=group.id,
                        student_id=student.id
                    )
                    db.session.add(member)
                
                new_groups.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'members': [s.id for s in group_students]
                })

        # Save rotation history
        history = GroupRotationHistory(
            rotation_id=rotation.id,
            previous_groups=json.dumps(previous_groups_data),
            new_groups=json.dumps(new_groups),
            rotation_notes=request.form.get('rotation_notes', '')
        )
        db.session.add(history)

        # Update rotation
        rotation.last_rotated = datetime.utcnow()
        
        db.session.commit()
        flash(f'Group rotation executed successfully! Created {len(new_groups)} new groups.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error executing group rotation: {str(e)}', 'danger')

    return redirect(url_for('teacher.class_group_rotations', class_id=rotation.class_id))

@teacher_blueprint.route('/group-rotation/<int:rotation_id>/history')
@login_required
@teacher_required
def view_rotation_history(rotation_id):
    """View rotation history for a specific rotation."""
    teacher = get_teacher_or_admin()
    rotation = GroupRotation.query.get_or_404(rotation_id)
    class_obj = Class.query.get_or_404(rotation.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    history = GroupRotationHistory.query.filter_by(rotation_id=rotation_id).order_by(GroupRotationHistory.rotation_date.desc()).all()
    
    return render_template('teacher_rotation_history.html',
                         class_obj=class_obj,
                         rotation=rotation,
                         history=history)

@teacher_blueprint.route('/class/<int:class_id>/group-rotation/delete', methods=['POST'])
@login_required
@teacher_required
def delete_group_rotation(class_id):
    """Delete a group rotation (soft delete)."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    rotation_id = request.form.get('rotation_id')
    rotation = GroupRotation.query.get_or_404(rotation_id)
    
    if rotation.class_id != class_id:
        flash('Invalid rotation.', 'danger')
        return redirect(url_for('teacher.class_group_rotations', class_id=class_id))

    try:
        rotation.is_active = False
        db.session.commit()
        flash('Group rotation deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting group rotation: {str(e)}', 'danger')

    return redirect(url_for('teacher.class_group_rotations', class_id=class_id))

# Peer Review Routes
@teacher_blueprint.route('/group-assignment/<int:assignment_id>/peer-reviews')
@login_required
@teacher_required
def view_peer_reviews(assignment_id):
    """View peer reviews for a group assignment."""
    teacher = get_teacher_or_admin()
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get all peer reviews for this assignment
    peer_reviews = PeerReview.query.filter_by(group_assignment_id=assignment_id).all()
    
    # Group reviews by reviewer
    reviews_by_reviewer = {}
    for review in peer_reviews:
        if review.reviewer_id not in reviews_by_reviewer:
            reviews_by_reviewer[review.reviewer_id] = []
        reviews_by_reviewer[review.reviewer_id].append(review)
    
    return render_template('teacher_peer_reviews.html',
                         class_obj=class_obj,
                         group_assignment=group_assignment,
                         peer_reviews=peer_reviews,
                         reviews_by_reviewer=reviews_by_reviewer)

@teacher_blueprint.route('/group-assignment/<int:assignment_id>/peer-review/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_peer_review(assignment_id):
    """Create a peer review for a group assignment."""
    teacher = get_teacher_or_admin()
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        group_id = int(request.form.get('group_id'))
        reviewer_id = int(request.form.get('reviewer_id'))
        reviewee_id = int(request.form.get('reviewee_id'))
        
        work_quality_score = int(request.form.get('work_quality_score'))
        creativity_score = int(request.form.get('creativity_score'))
        presentation_score = int(request.form.get('presentation_score'))
        overall_score = int(request.form.get('overall_score'))
        
        constructive_feedback = request.form.get('constructive_feedback')
        strengths = request.form.get('strengths')
        improvements = request.form.get('improvements')

        # Check if review already exists
        existing_review = PeerReview.query.filter_by(
            group_assignment_id=assignment_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id
        ).first()
        
        if existing_review:
            flash('A review already exists for this student pair.', 'warning')
            return redirect(url_for('teacher.create_peer_review', assignment_id=assignment_id))

        peer_review = PeerReview(
            group_assignment_id=assignment_id,
            group_id=group_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            work_quality_score=work_quality_score,
            creativity_score=creativity_score,
            presentation_score=presentation_score,
            overall_score=overall_score,
            constructive_feedback=constructive_feedback,
            strengths=strengths,
            improvements=improvements
        )

        try:
            db.session.add(peer_review)
            db.session.commit()
            flash('Peer review created successfully!', 'success')
            return redirect(url_for('teacher.view_peer_reviews', assignment_id=assignment_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating peer review: {str(e)}', 'danger')

    # Get groups and students for the assignment
    groups = StudentGroup.query.filter_by(class_id=class_obj.id, is_active=True).all()
    
    return render_template('teacher_create_peer_review.html',
                         class_obj=class_obj,
                         group_assignment=group_assignment,
                         groups=groups)

@teacher_blueprint.route('/peer-review/<int:review_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_peer_review(review_id):
    """Edit a peer review."""
    teacher = get_teacher_or_admin()
    peer_review = PeerReview.query.get_or_404(review_id)
    group_assignment = peer_review.group_assignment
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this review.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        peer_review.work_quality_score = int(request.form.get('work_quality_score'))
        peer_review.creativity_score = int(request.form.get('creativity_score'))
        peer_review.presentation_score = int(request.form.get('presentation_score'))
        peer_review.overall_score = int(request.form.get('overall_score'))
        peer_review.constructive_feedback = request.form.get('constructive_feedback')
        peer_review.strengths = request.form.get('strengths')
        peer_review.improvements = request.form.get('improvements')

        try:
            db.session.commit()
            flash('Peer review updated successfully!', 'success')
            return redirect(url_for('teacher.view_peer_reviews', assignment_id=group_assignment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating peer review: {str(e)}', 'danger')

    return render_template('teacher_edit_peer_review.html',
                         class_obj=class_obj,
                         group_assignment=group_assignment,
                         peer_review=peer_review)

@teacher_blueprint.route('/peer-review/<int:review_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_peer_review(review_id):
    """Delete a peer review."""
    teacher = get_teacher_or_admin()
    peer_review = PeerReview.query.get_or_404(review_id)
    group_assignment = peer_review.group_assignment
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this review.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    try:
        db.session.delete(peer_review)
        db.session.commit()
        flash('Peer review deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting peer review: {str(e)}', 'danger')

    return redirect(url_for('teacher.view_peer_reviews', assignment_id=group_assignment.id))

# Draft Submission Routes
@teacher_blueprint.route('/group-assignment/<int:assignment_id>/draft-submissions')
@login_required
@teacher_required
def view_draft_submissions(assignment_id):
    """View draft submissions for a group assignment."""
    teacher = get_teacher_or_admin()
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get all draft submissions for this assignment
    draft_submissions = DraftSubmission.query.filter_by(group_assignment_id=assignment_id).order_by(DraftSubmission.submitted_at.desc()).all()
    
    return render_template('teacher_draft_submissions.html',
                         class_obj=class_obj,
                         group_assignment=group_assignment,
                         draft_submissions=draft_submissions)

@teacher_blueprint.route('/draft-submission/<int:draft_id>/feedback', methods=['GET', 'POST'])
@login_required
@teacher_required
def provide_draft_feedback(draft_id):
    """Provide feedback on a draft submission."""
    teacher = get_teacher_or_admin()
    draft_submission = DraftSubmission.query.get_or_404(draft_id)
    group_assignment = draft_submission.group_assignment
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this submission.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        feedback_content = request.form.get('feedback_content')
        feedback_type = request.form.get('feedback_type', 'general')
        is_approved = request.form.get('is_approved') == 'on'

        if not feedback_content:
            flash('Feedback content is required.', 'danger')
            return redirect(url_for('teacher.provide_draft_feedback', draft_id=draft_id))

        feedback = DraftFeedback(
            draft_submission_id=draft_id,
            feedback_provider_id=teacher.id,
            feedback_content=feedback_content,
            feedback_type=feedback_type,
            is_approved=is_approved
        )

        try:
            db.session.add(feedback)
            db.session.commit()
            flash('Feedback provided successfully!', 'success')
            return redirect(url_for('teacher.view_draft_submissions', assignment_id=group_assignment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error providing feedback: {str(e)}', 'danger')

    return render_template('teacher_provide_draft_feedback.html',
                         class_obj=class_obj,
                         group_assignment=group_assignment,
                         draft_submission=draft_submission)

@teacher_blueprint.route('/draft-submission/<int:draft_id>/approve', methods=['POST'])
@login_required
@teacher_required
def approve_draft_submission(draft_id):
    """Approve a draft submission."""
    teacher = get_teacher_or_admin()
    draft_submission = DraftSubmission.query.get_or_404(draft_id)
    group_assignment = draft_submission.group_assignment
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this submission.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    try:
        draft_submission.is_final = True
        db.session.commit()
        flash('Draft submission approved successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving submission: {str(e)}', 'danger')

    return redirect(url_for('teacher.view_draft_submissions', assignment_id=group_assignment.id))

@teacher_blueprint.route('/draft-submission/<int:draft_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_draft_submission(draft_id):
    """Delete a draft submission."""
    teacher = get_teacher_or_admin()
    draft_submission = DraftSubmission.query.get_or_404(draft_id)
    group_assignment = draft_submission.group_assignment
    class_obj = Class.query.get_or_404(group_assignment.class_id)

    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this submission.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    try:
        # Delete associated feedback first
        DraftFeedback.query.filter_by(draft_submission_id=draft_id).delete()
        db.session.delete(draft_submission)
        db.session.commit()
        flash('Draft submission deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting submission: {str(e)}', 'danger')

    return redirect(url_for('teacher.view_draft_submissions', assignment_id=group_assignment.id))


# Deadline Reminder Routes
@teacher_blueprint.route('/class/<int:class_id>/deadline-reminders')
@login_required
@teacher_required
def class_deadline_reminders(class_id):
    """View deadline reminders for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if this is an admin view request
    admin_view = request.args.get('admin_view') == 'true'
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        if admin_view:
            return redirect(url_for('management.view_class', class_id=class_id))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all deadline reminders for this class
    try:
        reminders = DeadlineReminder.query.filter_by(class_id=class_id).order_by(DeadlineReminder.reminder_date.desc()).all()
        
        # Get upcoming reminders (next 7 days)
        from datetime import datetime, timedelta
        upcoming_date = datetime.utcnow() + timedelta(days=7)
        upcoming_reminders = DeadlineReminder.query.filter(
            DeadlineReminder.class_id == class_id,
            DeadlineReminder.reminder_date <= upcoming_date,
            DeadlineReminder.reminder_date >= datetime.utcnow(),
            DeadlineReminder.is_active == True
    ).order_by(DeadlineReminder.reminder_date.asc()).all()
    
    except Exception as e:
        # Handle case where tables don't exist yet
        flash('Deadline reminders feature is not yet available. Please run the database migration first.', 'warning')
        reminders = []
        upcoming_reminders = []
    
    return render_template('teacher_class_deadline_reminders.html',
                         class_obj=class_obj,
                         reminders=reminders,
                         upcoming_reminders=upcoming_reminders,
                         admin_view=admin_view)


@teacher_blueprint.route('/class/<int:class_id>/deadline-reminder/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_deadline_reminder(class_id):
    """Create a new deadline reminder."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get assignments and group assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
    
    if request.method == 'POST':
        try:
            reminder_type = request.form.get('reminder_type')
            assignment_id = request.form.get('assignment_id')
            group_assignment_id = request.form.get('group_assignment_id')
            reminder_title = request.form.get('reminder_title')
            reminder_message = request.form.get('reminder_message')
            reminder_date = request.form.get('reminder_date')
            reminder_frequency = request.form.get('reminder_frequency', 'once')
            
            if not all([reminder_title, reminder_message, reminder_date]):
                flash('All fields are required.', 'danger')
                return render_template('teacher_create_deadline_reminder.html',
                                     class_obj=class_obj,
                                     assignments=assignments,
                                     group_assignments=group_assignments)
            
            # Parse reminder date
            try:
                reminder_datetime = datetime.strptime(reminder_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format.', 'danger')
                return render_template('teacher_create_deadline_reminder.html',
                                     class_obj=class_obj,
                                     assignments=assignments,
                                     group_assignments=group_assignments)
            
            # Create reminder
            reminder = DeadlineReminder(
                assignment_id=assignment_id if assignment_id else None,
                group_assignment_id=group_assignment_id if group_assignment_id else None,
                class_id=class_id,
                reminder_type=reminder_type,
                reminder_title=reminder_title,
                reminder_message=reminder_message,
                reminder_date=reminder_datetime,
                reminder_frequency=reminder_frequency,
                created_by=teacher.id
            )
            
            db.session.add(reminder)
            db.session.commit()
            
            flash('Deadline reminder created successfully!', 'success')
            return redirect(url_for('teacher.class_deadline_reminders', class_id=class_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating reminder: {str(e)}', 'danger')
    
    return render_template('teacher_create_deadline_reminder.html',
                         class_obj=class_obj,
                         assignments=assignments,
                         group_assignments=group_assignments)


@teacher_blueprint.route('/deadline-reminder/<int:reminder_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_deadline_reminder(reminder_id):
    """Edit a deadline reminder."""
    teacher = get_teacher_or_admin()
    reminder = DeadlineReminder.query.get_or_404(reminder_id)
    class_obj = Class.query.get_or_404(reminder.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get assignments and group assignments for this class
    assignments = Assignment.query.filter_by(class_id=reminder.class_id).all()
    group_assignments = GroupAssignment.query.filter_by(class_id=reminder.class_id).all()
    
    if request.method == 'POST':
        try:
            reminder.reminder_type = request.form.get('reminder_type')
            reminder.assignment_id = request.form.get('assignment_id') if request.form.get('assignment_id') else None
            reminder.group_assignment_id = request.form.get('group_assignment_id') if request.form.get('group_assignment_id') else None
            reminder.reminder_title = request.form.get('reminder_title')
            reminder.reminder_message = request.form.get('reminder_message')
            reminder.reminder_frequency = request.form.get('reminder_frequency', 'once')
            
            reminder_date = request.form.get('reminder_date')
            if reminder_date:
                try:
                    reminder.reminder_date = datetime.strptime(reminder_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid date format.', 'danger')
                    return render_template('teacher_edit_deadline_reminder.html',
                                         reminder=reminder,
                                         class_obj=class_obj,
                                         assignments=assignments,
                                         group_assignments=group_assignments)
            
            db.session.commit()
            flash('Deadline reminder updated successfully!', 'success')
            return redirect(url_for('teacher.class_deadline_reminders', class_id=reminder.class_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating reminder: {str(e)}', 'danger')
    
    return render_template('teacher_edit_deadline_reminder.html',
                         reminder=reminder,
                         class_obj=class_obj,
                         assignments=assignments,
                         group_assignments=group_assignments)


@teacher_blueprint.route('/deadline-reminder/<int:reminder_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_deadline_reminder(reminder_id):
    """Delete a deadline reminder."""
    teacher = get_teacher_or_admin()
    reminder = DeadlineReminder.query.get_or_404(reminder_id)
    class_obj = Class.query.get_or_404(reminder.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Delete associated notifications first
        ReminderNotification.query.filter_by(reminder_id=reminder_id).delete()
        db.session.delete(reminder)
        db.session.commit()
        flash('Deadline reminder deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting reminder: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_deadline_reminders', class_id=reminder.class_id))


@teacher_blueprint.route('/deadline-reminder/<int:reminder_id>/toggle', methods=['POST'])
@login_required
@teacher_required
def toggle_deadline_reminder(reminder_id):
    """Toggle reminder active status."""
    teacher = get_teacher_or_admin()
    reminder = DeadlineReminder.query.get_or_404(reminder_id)
    class_obj = Class.query.get_or_404(reminder.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        reminder.is_active = not reminder.is_active
        db.session.commit()
        
        status = 'activated' if reminder.is_active else 'deactivated'
        flash(f'Reminder {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating reminder: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_deadline_reminders', class_id=reminder.class_id))


@teacher_blueprint.route('/deadline-reminder/<int:reminder_id>/send-now', methods=['POST'])
@login_required
@teacher_required
def send_deadline_reminder_now(reminder_id):
    """Send a deadline reminder immediately."""
    teacher = get_teacher_or_admin()
    reminder = DeadlineReminder.query.get_or_404(reminder_id)
    class_obj = Class.query.get_or_404(reminder.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Get all students in the class
        enrollments = Enrollment.query.filter_by(class_id=reminder.class_id).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student]
        
        # Create notifications for each student
        for student in students:
            notification = ReminderNotification(
                reminder_id=reminder_id,
                student_id=student.id,
                notification_type='in_app',
                status='sent'
            )
            db.session.add(notification)
        
        # Update reminder last sent time
        reminder.last_sent = datetime.utcnow()
        db.session.commit()
        
        flash(f'Reminder sent to {len(students)} students successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending reminder: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_deadline_reminders', class_id=reminder.class_id))


# 360-Degree Feedback Routes
@teacher_blueprint.route('/class/<int:class_id>/360-feedback')
@login_required
@teacher_required
def class_360_feedback(class_id):
    """View 360-degree feedback sessions for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all 360-degree feedback sessions for this class
    feedback_sessions = Feedback360.query.filter_by(class_id=class_id).order_by(Feedback360.created_at.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teacher_class_360_feedback.html',
                         class_obj=class_obj,
                         feedback_sessions=feedback_sessions,
                         students=students)


@teacher_blueprint.route('/class/<int:class_id>/360-feedback/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_360_feedback(class_id):
    """Create a new 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            target_student_id = request.form.get('target_student_id')
            feedback_type = request.form.get('feedback_type')
            due_date = request.form.get('due_date')
            
            if not all([title, target_student_id, feedback_type]):
                flash('Title, target student, and feedback type are required.', 'danger')
                return render_template('teacher_create_360_feedback.html',
                                     class_obj=class_obj,
                                     students=students)
            
            # Parse due date if provided
            due_datetime = None
            if due_date:
                try:
                    due_datetime = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid due date format.', 'danger')
                    return render_template('teacher_create_360_feedback.html',
                                         class_obj=class_obj,
                                         students=students)
            
            # Create feedback session
            feedback_session = Feedback360(
                title=title,
                description=description,
                class_id=class_id,
                target_student_id=target_student_id,
                feedback_type=feedback_type,
                due_date=due_datetime,
                created_by=teacher.id
            )
            
            db.session.add(feedback_session)
            db.session.commit()
            
            flash('360-degree feedback session created successfully!', 'success')
            return redirect(url_for('teacher.view_360_feedback', session_id=feedback_session.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating feedback session: {str(e)}', 'danger')
    
    return render_template('teacher_create_360_feedback.html',
                         class_obj=class_obj,
                         students=students)


@teacher_blueprint.route('/360-feedback/<int:session_id>')
@login_required
@teacher_required
def view_360_feedback(session_id):
    """View a specific 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all responses for this session
    responses = Feedback360Response.query.filter_by(feedback360_id=session_id).all()
    
    # Get criteria for this session
    criteria = Feedback360Criteria.query.filter_by(feedback360_id=session_id).order_by(Feedback360Criteria.order_index).all()
    
    # Get students in the class for potential respondents
    enrollments = Enrollment.query.filter_by(class_id=feedback_session.class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teacher_view_360_feedback.html',
                         feedback_session=feedback_session,
                         class_obj=class_obj,
                         responses=responses,
                         criteria=criteria,
                         students=students)


@teacher_blueprint.route('/360-feedback/<int:session_id>/criteria/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_360_feedback_criteria(session_id):
    """Create criteria for a 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        try:
            criteria_name = request.form.get('criteria_name')
            criteria_description = request.form.get('criteria_description')
            criteria_type = request.form.get('criteria_type')
            scale_min = request.form.get('scale_min', 1)
            scale_max = request.form.get('scale_max', 5)
            is_required = request.form.get('is_required') == 'on'
            order_index = request.form.get('order_index', 0)
            
            if not criteria_name:
                flash('Criteria name is required.', 'danger')
                return render_template('teacher_create_360_feedback_criteria.html',
                                     feedback_session=feedback_session,
                                     class_obj=class_obj)
            
            # Create criteria
            criteria = Feedback360Criteria(
                feedback360_id=session_id,
                criteria_name=criteria_name,
                criteria_description=criteria_description,
                criteria_type=criteria_type,
                scale_min=int(scale_min),
                scale_max=int(scale_max),
                is_required=is_required,
                order_index=int(order_index)
            )
            
            db.session.add(criteria)
            db.session.commit()
            
            flash('Feedback criteria created successfully!', 'success')
            return redirect(url_for('teacher.view_360_feedback', session_id=session_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating criteria: {str(e)}', 'danger')
    
    return render_template('teacher_create_360_feedback_criteria.html',
                         feedback_session=feedback_session,
                         class_obj=class_obj)


@teacher_blueprint.route('/360-feedback/<int:session_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_360_feedback(session_id):
    """Delete a 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Delete associated responses and criteria first
        Feedback360Response.query.filter_by(feedback360_id=session_id).delete()
        Feedback360Criteria.query.filter_by(feedback360_id=session_id).delete()
        db.session.delete(feedback_session)
        db.session.commit()
        flash('360-degree feedback session deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting feedback session: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_360_feedback', class_id=feedback_session.class_id))


@teacher_blueprint.route('/360-feedback/<int:session_id>/toggle', methods=['POST'])
@login_required
@teacher_required
def toggle_360_feedback(session_id):
    """Toggle feedback session active status."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        feedback_session.is_active = not feedback_session.is_active
        db.session.commit()
        
        status = 'activated' if feedback_session.is_active else 'deactivated'
        flash(f'Feedback session {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating feedback session: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.view_360_feedback', session_id=session_id))


# Reflection Journal Routes
@teacher_blueprint.route('/class/<int:class_id>/reflection-journals')
@login_required
@teacher_required
def class_reflection_journals(class_id):
    """View reflection journals for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all reflection journals for this class
    journals = ReflectionJournal.query.join(GroupAssignment).filter(
        GroupAssignment.class_id == class_id
    ).order_by(ReflectionJournal.submitted_at.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teacher_class_reflection_journals.html',
                         class_obj=class_obj,
                         journals=journals,
                         students=students)


@teacher_blueprint.route('/reflection-journal/<int:journal_id>')
@login_required
@teacher_required
def view_reflection_journal(journal_id):
    """View a specific reflection journal."""
    teacher = get_teacher_or_admin()
    journal = ReflectionJournal.query.get_or_404(journal_id)
    class_obj = Class.query.get_or_404(journal.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reflection journal.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    return render_template('teacher_view_reflection_journal.html',
                         journal=journal,
                         class_obj=class_obj)


@teacher_blueprint.route('/reflection-journal/<int:journal_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_reflection_journal(journal_id):
    """Delete a reflection journal."""
    teacher = get_teacher_or_admin()
    journal = ReflectionJournal.query.get_or_404(journal_id)
    class_obj = Class.query.get_or_404(journal.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reflection journal.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        db.session.delete(journal)
        db.session.commit()
        flash('Reflection journal deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting reflection journal: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_reflection_journals', class_id=class_obj.id))


@teacher_blueprint.route('/group-assignment/<int:assignment_id>/reflection-journals')
@login_required
@teacher_required
def group_assignment_reflection_journals(assignment_id):
    """View reflection journals for a specific group assignment."""
    teacher = get_teacher_or_admin()
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    class_obj = Class.query.get_or_404(group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this assignment.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all reflection journals for this assignment
    journals = ReflectionJournal.query.filter_by(group_assignment_id=assignment_id).order_by(ReflectionJournal.submitted_at.desc()).all()
    
    return render_template('teacher_group_assignment_reflection_journals.html',
                         group_assignment=group_assignment,
                         class_obj=class_obj,
                         journals=journals)


# Conflict Resolution Routes
@teacher_blueprint.route('/class/<int:class_id>/conflicts')
@login_required
@teacher_required
def class_conflicts(class_id):
    """View conflicts for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all conflicts for this class
    conflicts = GroupConflict.query.join(GroupAssignment).filter(
        GroupAssignment.class_id == class_id
    ).order_by(GroupConflict.reported_at.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teacher_class_conflicts.html',
                         class_obj=class_obj,
                         conflicts=conflicts,
                         students=students)


@teacher_blueprint.route('/conflict/<int:conflict_id>')
@login_required
@teacher_required
def view_conflict(conflict_id):
    """View a specific conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get resolution steps
    resolution_steps = ConflictResolution.query.filter_by(conflict_id=conflict_id).order_by(ConflictResolution.implemented_at.asc()).all()
    
    # Get participants
    participants = ConflictParticipant.query.filter_by(conflict_id=conflict_id).all()
    
    return render_template('teacher_view_conflict.html',
                         conflict=conflict,
                         class_obj=class_obj,
                         resolution_steps=resolution_steps,
                         participants=participants)


@teacher_blueprint.route('/conflict/<int:conflict_id>/resolve', methods=['GET', 'POST'])
@login_required
@teacher_required
def resolve_conflict(conflict_id):
    """Resolve a conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        try:
            resolution_notes = request.form.get('resolution_notes')
            new_status = request.form.get('status')
            
            # Update conflict status
            conflict.status = new_status
            conflict.resolution_notes = resolution_notes
            conflict.resolved_by = teacher.id
            
            if new_status == 'resolved':
                conflict.resolved_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Conflict resolution updated successfully!', 'success')
            return redirect(url_for('teacher.view_conflict', conflict_id=conflict_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating conflict resolution: {str(e)}', 'danger')
    
    return render_template('teacher_resolve_conflict.html',
                         conflict=conflict,
                         class_obj=class_obj)


@teacher_blueprint.route('/conflict/<int:conflict_id>/add-resolution-step', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_conflict_resolution_step(conflict_id):
    """Add a resolution step to a conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        try:
            resolution_step = request.form.get('resolution_step')
            step_description = request.form.get('step_description')
            step_type = request.form.get('step_type')
            outcome = request.form.get('outcome')
            follow_up_date = request.form.get('follow_up_date')
            follow_up_notes = request.form.get('follow_up_notes')
            
            if not all([resolution_step, step_description, step_type]):
                flash('Resolution step, description, and type are required.', 'danger')
                return render_template('teacher_add_conflict_resolution_step.html',
                                     conflict=conflict,
                                     class_obj=class_obj)
            
            # Parse follow-up date if provided
            follow_up_datetime = None
            if follow_up_date:
                try:
                    follow_up_datetime = datetime.strptime(follow_up_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid follow-up date format.', 'danger')
                    return render_template('teacher_add_conflict_resolution_step.html',
                                         conflict=conflict,
                                         class_obj=class_obj)
            
            # Create resolution step
            resolution = ConflictResolution(
                conflict_id=conflict_id,
                resolution_step=resolution_step,
                step_description=step_description,
                step_type=step_type,
                outcome=outcome,
                implemented_by=teacher.id,
                follow_up_date=follow_up_datetime,
                follow_up_notes=follow_up_notes
            )
            
            db.session.add(resolution)
            db.session.commit()
            
            flash('Resolution step added successfully!', 'success')
            return redirect(url_for('teacher.view_conflict', conflict_id=conflict_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding resolution step: {str(e)}', 'danger')
    
    return render_template('teacher_add_conflict_resolution_step.html',
                         conflict=conflict,
                         class_obj=class_obj)


@teacher_blueprint.route('/conflict/<int:conflict_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_conflict(conflict_id):
    """Delete a conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Delete associated resolution steps and participants first
        ConflictResolution.query.filter_by(conflict_id=conflict_id).delete()
        ConflictParticipant.query.filter_by(conflict_id=conflict_id).delete()
        db.session.delete(conflict)
        db.session.commit()
        flash('Conflict deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting conflict: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.class_conflicts', class_id=class_obj.id))


# Comprehensive Reporting & Analytics Routes
@teacher_blueprint.route('/class/<int:class_id>/reports')
@login_required
@teacher_required
def class_reports(class_id):
    """View comprehensive reports for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all reports for this class
    reports = GroupWorkReport.query.filter_by(class_id=class_id).order_by(GroupWorkReport.generated_at.desc()).all()
    
    # Get recent analytics data
    recent_contributions = IndividualContribution.query.join(StudentGroup).filter(
        StudentGroup.class_id == class_id
    ).order_by(IndividualContribution.recorded_at.desc()).limit(10).all()
    
    recent_time_tracking = TimeTracking.query.join(StudentGroup).filter(
        StudentGroup.class_id == class_id
    ).order_by(TimeTracking.start_time.desc()).limit(10).all()
    
    return render_template('teacher_class_reports.html',
                         class_obj=class_obj,
                         reports=reports,
                         recent_contributions=recent_contributions,
                         recent_time_tracking=recent_time_tracking)


@teacher_blueprint.route('/class/<int:class_id>/analytics')
@login_required
@teacher_required
def class_analytics(class_id):
    """View comprehensive analytics dashboard for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get analytics data
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
    
    # Get collaboration metrics
    collaboration_metrics = CollaborationMetrics.query.join(StudentGroup).filter(
        StudentGroup.class_id == class_id
    ).order_by(CollaborationMetrics.measurement_date.desc()).all()
    
    # Get performance benchmarks
    benchmarks = PerformanceBenchmark.query.filter_by(class_id=class_id, is_active=True).all()
    
    # Get saved dashboards
    dashboards = AnalyticsDashboard.query.filter_by(class_id=class_id).order_by(AnalyticsDashboard.last_accessed.desc()).all()
    
    return render_template('teacher_class_analytics.html',
                         class_obj=class_obj,
                         groups=groups,
                         group_assignments=group_assignments,
                         collaboration_metrics=collaboration_metrics,
                         benchmarks=benchmarks,
                         dashboards=dashboards)


@teacher_blueprint.route('/class/<int:class_id>/contributions')
@login_required
@teacher_required
def class_contributions(class_id):
    """View individual contributions tracking for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get all contributions for this class
    contributions = IndividualContribution.query.join(StudentGroup).filter(
        StudentGroup.class_id == class_id
    ).order_by(IndividualContribution.recorded_at.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teacher_class_contributions.html',
                         class_obj=class_obj,
                         contributions=contributions,
                         students=students)


@teacher_blueprint.route('/class/<int:class_id>/time-tracking')
@login_required
@teacher_required
def class_time_tracking(class_id):
    """View time tracking for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get time tracking data
    time_tracking = TimeTracking.query.join(StudentGroup).filter(
        StudentGroup.class_id == class_id
    ).order_by(TimeTracking.start_time.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teacher_class_time_tracking.html',
                         class_obj=class_obj,
                         time_tracking=time_tracking,
                         students=students)


@teacher_blueprint.route('/class/<int:class_id>/create-report', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_report(class_id):
    """Create a comprehensive report for a class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        try:
            report_name = request.form.get('report_name')
            report_type = request.form.get('report_type')
            report_period_start = request.form.get('report_period_start')
            report_period_end = request.form.get('report_period_end')
            
            if not all([report_name, report_type, report_period_start, report_period_end]):
                flash('All fields are required.', 'danger')
                return render_template('teacher_create_report.html', class_obj=class_obj)
            
            # Parse dates
            start_date = datetime.strptime(report_period_start, '%Y-%m-%d')
            end_date = datetime.strptime(report_period_end, '%Y-%m-%d')
            
            # Generate report data based on type
            report_data = generate_report_data(class_id, report_type, start_date, end_date)
            
            # Create report
            report = GroupWorkReport(
                class_id=class_id,
                report_name=report_name,
                report_type=report_type,
                report_period_start=start_date,
                report_period_end=end_date,
                generated_by=teacher.id,
                report_data=json.dumps(report_data)
            )
            
            db.session.add(report)
            db.session.commit()
            
            flash('Report generated successfully!', 'success')
            return redirect(url_for('teacher.class_reports', class_id=class_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating report: {str(e)}', 'danger')
    
    return render_template('teacher_create_report.html', class_obj=class_obj)


@teacher_blueprint.route('/report/<int:report_id>')
@login_required
@teacher_required
def view_report(report_id):
    """View a specific report."""
    teacher = get_teacher_or_admin()
    report = GroupWorkReport.query.get_or_404(report_id)
    class_obj = Class.query.get_or_404(report.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this report.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Parse report data
    report_data = json.loads(report.report_data) if report.report_data else {}
    
    return render_template('teacher_view_report.html',
                         report=report,
                         class_obj=class_obj,
                         report_data=report_data)


@teacher_blueprint.route('/report/<int:report_id>/export/<format>')
@login_required
@teacher_required
def export_report(report_id, format):
    """Export a report in the specified format."""
    teacher = get_teacher_or_admin()
    report = GroupWorkReport.query.get_or_404(report_id)
    class_obj = Class.query.get_or_404(report.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this report.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Generate export file
        export_path = generate_export_file(report, format)
        
        # Create export record
        export_record = ReportExport(
            report_id=report_id,
            export_format=format,
            export_path=export_path,
            exported_by=teacher.id
        )
        
        db.session.add(export_record)
        db.session.commit()
        
        flash(f'Report exported successfully as {format.upper()}!', 'success')
        return redirect(url_for('teacher.view_report', report_id=report_id))
        
    except Exception as e:
        flash(f'Error exporting report: {str(e)}', 'danger')
        return redirect(url_for('teacher.view_report', report_id=report_id))


def generate_report_data(class_id, report_type, start_date, end_date):
    """Generate comprehensive report data based on type and date range."""
    report_data = {
        'class_id': class_id,
        'report_type': report_type,
        'period_start': start_date.isoformat(),
        'period_end': end_date.isoformat(),
        'generated_at': datetime.utcnow().isoformat()
    }
    
    if report_type == 'comprehensive':
        # Get all relevant data
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
        contributions = IndividualContribution.query.join(StudentGroup).filter(
            StudentGroup.class_id == class_id,
            IndividualContribution.recorded_at >= start_date,
            IndividualContribution.recorded_at <= end_date
        ).all()
        
        report_data.update({
            'groups': [{'id': g.id, 'name': g.name, 'member_count': len(g.members)} for g in groups],
            'assignments': [{'id': a.id, 'title': a.title, 'due_date': a.due_date.isoformat()} for a in assignments],
            'contributions': [{'student_id': c.student_id, 'type': c.contribution_type, 'quality': c.contribution_quality} for c in contributions]
        })
    
    elif report_type == 'performance':
        # Get performance-related data
        grades = GroupGrade.query.join(GroupAssignment).filter(
            GroupAssignment.class_id == class_id,
            GroupGrade.graded_at >= start_date,
            GroupGrade.graded_at <= end_date
        ).all()
        
        report_data.update({
            'grades': [{'student_id': g.student_id, 'grade_data': g.grade_data} for g in grades]
        })
    
    elif report_type == 'collaboration':
        # Get collaboration metrics
        metrics = CollaborationMetrics.query.join(StudentGroup).filter(
            StudentGroup.class_id == class_id,
            CollaborationMetrics.measurement_date >= start_date,
            CollaborationMetrics.measurement_date <= end_date
        ).all()
        
        report_data.update({
            'collaboration_metrics': [{'group_id': m.group_id, 'type': m.metric_type, 'value': m.metric_value} for m in metrics]
        })
    
    return report_data


def generate_export_file(report, format):
    """Generate export file for a report."""
    # This is a placeholder - in a real implementation, you would generate actual files
    # For now, we'll just return a mock path
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{report.id}_{timestamp}.{format}"
    return f"exports/{filename}"