"""
Assignment management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class, get_current_quarter
from teacher_routes.assignment_utils import is_assignment_open_for_student
from models import (
    db, Class, Assignment, AssignmentAttachment, SchoolYear, Enrollment, TeacherStaff, AssignmentExtension,
    Grade, GroupAssignment, GroupGrade, GradeHistory, GroupSubmission, StudentGroup,
    class_additional_teachers, class_substitute_teachers, AssignmentReopening, Submission,
    DiscussionThread, DiscussionPost
)
from sqlalchemy import or_
from datetime import datetime, time
from utils.quarter_grade_calculator import update_quarter_grade
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from werkzeug.utils import secure_filename
import os

bp = Blueprint('assignments', __name__)

def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'xls', 'xlsx', 'ppt', 'pptx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/assignment/type-selector')
@login_required
@teacher_required
def assignment_type_selector():
    """Assignment type selection page"""
    preselected_class_id = request.args.get('class_id', type=int)
    return render_template('shared/assignment_type_selector.html', preselected_class_id=preselected_class_id)

@bp.route('/assignment/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment():
    """Add a new assignment - class selection page (or auto-redirect if only 1 class)"""
    context = request.args.get('context', 'homework')
    
    if request.method == 'POST':
        class_id = request.form.get('class_id', type=int)
        if class_id:
            return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id, context=context))
        else:
            flash("Please select a class.", "danger")
    
    teacher = get_teacher_or_admin()
    
    # Get accessible classes for the current teacher/admin
    if is_admin():
        classes = Class.query.all()
    elif teacher is not None:
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
    else:
        classes = []
    
    # If teacher has only 1 class, automatically redirect to the assignment details page
    if len(classes) == 1:
        return redirect(url_for('teacher.assignments.add_assignment_for_class', 
                              class_id=classes[0].id, 
                              context=context))
    
    # If multiple classes or no classes, show the selection page
    return render_template('shared/add_assignment_select_class.html', classes=classes, context=context)

@bp.route('/assignment/add/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment_for_class(class_id):
    """Add a new assignment for a specific class"""
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to add assignments to this class.", "danger")
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            due_date_str = request.form.get('due_date')
            quarter = request.form.get('quarter')
            status = request.form.get('status', 'Active')
            assignment_context = request.form.get('assignment_context', 'homework')
            total_points = request.form.get('total_points', type=float)
            allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
            max_extra_credit_points = request.form.get('max_extra_credit_points', type=float) or 0.0
            late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
            late_penalty_per_day = request.form.get('late_penalty_per_day', type=float) or 0.0
            late_penalty_max_days = request.form.get('late_penalty_max_days', type=int) or 0
            
            if not all([title, due_date_str, quarter]):
                flash("Title, Due Date, and Quarter are required.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
            
            if total_points is None or total_points <= 0:
                total_points = 100.0
            
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            
            # Parse open_date and close_date if provided
            # IMPORTANT: close_date should default to due_date if not provided
            open_date_str = request.form.get('open_date', '').strip()
            close_date_str = request.form.get('close_date', '').strip()
            open_date = None
            close_date = None
            allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
            max_extra_credit_points = request.form.get('max_extra_credit_points', type=float) or 0.0
            late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
            late_penalty_per_day = request.form.get('late_penalty_per_day', type=float) or 0.0
            late_penalty_max_days = request.form.get('late_penalty_max_days', type=int) or 0
            
            if open_date_str:
                try:
                    open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            
            if close_date_str:
                try:
                    close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            
            # If close_date not provided, default to due_date
            if not close_date:
                close_date = due_date
            
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
            
            # IMPORTANT:
            # Assignment.created_by is a FK to user.id (not teacher_staff.id).
            # Using teacher_staff.id here can collide with a student user.id and display the wrong creator.
            creator_user_id = current_user.id
            
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                open_date=open_date,
                close_date=close_date,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status=status,
                assignment_context=assignment_context,
                total_points=total_points,
                allow_extra_credit=allow_extra_credit,
                max_extra_credit_points=max_extra_credit_points if allow_extra_credit else 0.0,
                late_penalty_enabled=late_penalty_enabled,
                late_penalty_per_day=late_penalty_per_day if late_penalty_enabled else 0.0,
                late_penalty_max_days=late_penalty_max_days if late_penalty_enabled else 0,
                created_by=creator_user_id
            )
            
            db.session.add(new_assignment)
            db.session.flush()

            # NOTE: We do NOT automatically create Grade records for enrolled students.
            # Grades are only created when a teacher explicitly enters scores via the grading interface.

            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
            os.makedirs(upload_dir, exist_ok=True)
            files_to_save = request.files.getlist('assignment_files') or []
            if not files_to_save or not (files_to_save[0] and files_to_save[0].filename):
                single = request.files.get('assignment_file')
                if single and single.filename:
                    files_to_save = [single]
            for idx, file in enumerate(files_to_save):
                if not file or not file.filename or not allowed_file(file.filename):
                    continue
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                unique_filename = timestamp + f"{idx}_{filename}"
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                # Store relative path (assignments/filename) so files resolve after redeploys
                attachment_file_path_stored = os.path.join('assignments', unique_filename)
                att = AssignmentAttachment(
                    assignment_id=new_assignment.id,
                    attachment_filename=unique_filename,
                    attachment_original_filename=filename,
                    attachment_file_path=attachment_file_path_stored,
                    attachment_file_size=os.path.getsize(filepath),
                    attachment_mime_type=file.content_type or None,
                    sort_order=idx,
                )
                db.session.add(att)
                if idx == 0:
                    new_assignment.attachment_filename = unique_filename
                    new_assignment.attachment_original_filename = filename
                    new_assignment.attachment_file_path = attachment_file_path_stored
                    new_assignment.attachment_file_size = os.path.getsize(filepath)
                    new_assignment.attachment_mime_type = file.content_type

            db.session.commit()
            flash('Assignment created successfully!', 'success')
            return redirect(url_for('teacher.dashboard.view_class', class_id=class_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating assignment: {str(e)}")
            flash(f'Error creating assignment: {str(e)}', 'danger')
            return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
    
    current_quarter = get_current_quarter()
    context = request.args.get('context', 'homework')
    # For in-class: default due date = today at 4:00 PM EST
    default_due_date = None
    in_class_due_date_str = None  # Always compute for JS (when user switches context)
    if context == 'in-class' and ZoneInfo:
        try:
            est = ZoneInfo('America/New_York')
            now_est = datetime.now(est)
            today_est = now_est.date()
            in_class_dt = datetime.combine(today_est, time(16, 0))
            in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
            default_due_date = in_class_dt
        except Exception:
            in_class_dt = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
            in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
            default_due_date = in_class_dt
    elif context == 'in-class':
        in_class_dt = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
        default_due_date = in_class_dt
    else:
        try:
            est = ZoneInfo('America/New_York')
            now_est = datetime.now(est)
            today_est = now_est.date()
            in_class_dt = datetime.combine(today_est, time(16, 0))
            in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
        except Exception:
            in_class_due_date_str = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M')
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    teacher = get_teacher_or_admin()
    
    return render_template('shared/add_assignment.html', 
                         class_obj=class_obj,
                         classes=[class_obj],
                         school_years=school_years,
                         current_quarter=current_quarter,
                         context=context,
                         default_due_date=default_due_date,
                         in_class_due_date_str=in_class_due_date_str,
                         teacher=teacher)

@bp.route('/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(assignment_id):
    """Edit an existing assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info

    # Quiz and discussion assignments use different edit flows - redirect to avoid errors
    if assignment.assignment_type == 'quiz':
        flash("Use the quiz editor to edit this assignment.", "info")
        return redirect(url_for('teacher.create_quiz_assignment') + f'?edit={assignment_id}')
    if assignment.assignment_type == 'discussion':
        return redirect(url_for('teacher.create_discussion_assignment') + f'?edit={assignment_id}')
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            due_date_str = request.form.get('due_date')
            quarter = request.form.get('quarter')
            status = request.form.get('status', 'Active')
            assignment_context = request.form.get('assignment_context', 'homework')
            total_points = request.form.get('total_points', type=float)
            
            if not all([title, due_date_str, quarter]):
                flash("Title, Due Date, and Quarter are required.", "danger")
                return redirect(url_for('teacher.assignments.edit_assignment', assignment_id=assignment_id))
            
            if total_points is None or total_points <= 0:
                total_points = 100.0
            
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            
            # Parse open_date and close_date if provided
            # IMPORTANT: close_date should default to due_date if not provided
            open_date_str = request.form.get('open_date', '').strip()
            close_date_str = request.form.get('close_date', '').strip()
            open_date = None
            close_date = None
            
            if open_date_str:
                try:
                    open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            
            if close_date_str:
                try:
                    close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            
            # If close_date not provided, default to due_date
            if not close_date:
                close_date = due_date
            
            assignment_category = request.form.get('assignment_category', '').strip() or None
            category_weight = request.form.get('category_weight', type=float)
            if category_weight is None:
                category_weight = 0.0

            allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
            max_extra_credit_points = request.form.get('max_extra_credit_points', type=float) or 0.0
            late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
            late_penalty_per_day = request.form.get('late_penalty_per_day', type=float) or 0.0
            late_penalty_max_days = request.form.get('late_penalty_max_days', type=int) or 0

            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.open_date = open_date
            assignment.close_date = close_date
            assignment.quarter = quarter
            assignment.assignment_context = assignment_context
            assignment.assignment_category = assignment_category
            assignment.category_weight = category_weight
            assignment.total_points = total_points
            assignment.allow_extra_credit = allow_extra_credit
            assignment.max_extra_credit_points = max_extra_credit_points if allow_extra_credit else 0.0
            assignment.late_penalty_enabled = late_penalty_enabled
            assignment.late_penalty_per_day = late_penalty_per_day if late_penalty_enabled else 0.0
            assignment.late_penalty_max_days = late_penalty_max_days if late_penalty_enabled else 0
            
            # Calculate status based on dates if status not explicitly set to Voided
            from teacher_routes.assignment_utils import calculate_assignment_status
            if status != 'Voided':
                # Calculate status based on dates
                calculated_status = calculate_assignment_status(assignment)
                assignment.status = calculated_status
            else:
                # Keep Voided status if explicitly set
                assignment.status = status
            
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
            files_to_save = request.files.getlist('assignment_files') or []
            if not files_to_save or not (files_to_save[0] and files_to_save[0].filename):
                single = request.files.get('assignment_file')
                if single and single.filename:
                    files_to_save = [single]
            if files_to_save:
                os.makedirs(upload_dir, exist_ok=True)
                for old_att in list(assignment.attachment_list or []):
                    db.session.delete(old_att)
                for idx, file in enumerate(files_to_save):
                    if not file or not file.filename or not allowed_file(file.filename):
                        continue
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    unique_filename = timestamp + f"{idx}_{filename}"
                    filepath = os.path.join(upload_dir, unique_filename)
                    file.save(filepath)
                    attachment_file_path_stored = os.path.join('assignments', unique_filename)
                    att = AssignmentAttachment(
                        assignment_id=assignment.id,
                        attachment_filename=unique_filename,
                        attachment_original_filename=filename,
                        attachment_file_path=attachment_file_path_stored,
                        attachment_file_size=os.path.getsize(filepath),
                        attachment_mime_type=file.content_type or None,
                        sort_order=idx,
                    )
                    db.session.add(att)
                    if idx == 0:
                        assignment.attachment_filename = unique_filename
                        assignment.attachment_original_filename = filename
                        assignment.attachment_file_path = attachment_file_path_stored
                        assignment.attachment_file_size = os.path.getsize(filepath)
                        assignment.attachment_mime_type = file.content_type

            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating assignment: {str(e)}")
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(url_for('teacher.assignments.edit_assignment', assignment_id=assignment_id))
    
    teacher = get_teacher_or_admin()
    current_quarter = get_current_quarter()
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    context = getattr(assignment, 'assignment_context', None) or 'homework'
    
    if not hasattr(assignment, 'total_points') or assignment.total_points is None:
        assignment.total_points = 100.0
    
    return render_template('shared/edit_assignment.html', 
                         assignment=assignment,
                         class_obj=class_obj,
                         classes=[class_obj],
                         school_years=school_years,
                         teacher=teacher,
                         current_quarter=current_quarter,
                         context=context)

@bp.route('/assignment/<int:assignment_id>/export-to-google-forms', methods=['POST'])
@login_required
@teacher_required
def export_quiz_to_google_forms(assignment_id):
    """Export a native quiz to Google Forms"""
    from google_forms_service import get_google_forms_service, export_quiz_to_google_form
    from models import QuizQuestion, QuizOption, User
    from sqlalchemy.orm import joinedload
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is a quiz
    if assignment.assignment_type != 'quiz':
        flash('This is not a quiz assignment.', 'warning')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    # Check if already linked to a Google Form
    if assignment.google_form_linked:
        flash('This quiz is already linked to a Google Form. Unlink it first if you want to export to a new form.', 'warning')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    # Get the current user and check if they have Google credentials
    user = User.query.get(current_user.id)
    if not user.google_refresh_token:
        flash('Please connect your Google account in Settings to export quizzes to Google Forms.', 'warning')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    try:
        # Get Google Forms service
        service = get_google_forms_service(user)
        if not service:
            flash('Failed to connect to Google Forms. Please check your Google account connection.', 'danger')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
        # Load quiz questions with options
        questions = QuizQuestion.query.options(joinedload(QuizQuestion.options)).filter_by(
            assignment_id=assignment_id
        ).order_by(QuizQuestion.order).all()
        
        if not questions:
            flash('This quiz has no questions. Please add questions before exporting.', 'warning')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
        # Export to Google Forms
        result = export_quiz_to_google_form(service, assignment, questions)
        
        if result:
            # Update assignment with Google Form link
            import re
            form_id_match = re.search(r'/forms/d/e/([A-Za-z0-9_-]+)/', result['form_url'])
            form_id = form_id_match.group(1) if form_id_match else result['form_id']
            
            assignment.google_form_id = form_id
            assignment.google_form_url = result['form_url']
            assignment.google_form_linked = True
            
            db.session.commit()
            
            flash(f'Quiz successfully exported to Google Forms! <a href="{result["form_url"]}" target="_blank">View Form</a>', 'success')
        else:
            flash('Failed to export quiz to Google Forms. Please try again.', 'danger')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error exporting quiz to Google Forms: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error exporting quiz to Google Forms: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))


@bp.route('/assignment/<int:assignment_id>/sync-google-forms', methods=['POST'])
@login_required
@teacher_required
def sync_google_forms_submissions(assignment_id):
    """Sync submissions from a linked Google Form"""
    from google_forms_service import get_google_forms_service, get_form_responses
    from models import Student, Submission, Grade, Enrollment, User
    from datetime import datetime
    import json
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is linked to Google Form
    if not assignment.google_form_linked or not assignment.google_form_id:
        flash('This assignment is not linked to a Google Form.', 'warning')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    # Get the current user and check if they have Google credentials
    user = User.query.get(current_user.id)
    if not user.google_refresh_token:
        flash('Please connect your Google account in Settings to sync Google Forms submissions.', 'warning')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    try:
        # Get Google Forms service
        service = get_google_forms_service(user)
        if not service:
            flash('Failed to connect to Google Forms. Please check your Google account connection.', 'danger')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
        # Get form responses
        responses = get_form_responses(service, assignment.google_form_id)
        if responses is None:
            flash('Failed to retrieve form responses from Google Forms.', 'danger')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
        students_dict = {student.email.lower(): student for enrollment in enrollments 
                        for student in [enrollment.student] if enrollment.student and enrollment.student.email}
        
        synced_count = 0
        created_submissions = 0
        
        # Process each response
        for response in responses:
            # Get respondent email from response
            # Google Forms responses may have respondentEmail if form collects emails
            # Otherwise, we need to extract from answers (first question asking for email)
            respondent_email = response.get('respondentEmail', '').lower()
            
            # If no direct email, try to extract from answers
            # Look for a question answer that matches an email pattern
            if not respondent_email:
                answers = response.get('answers', {})
                for question_id, answer_data in answers.items():
                    # Check text answers for email patterns
                    text_answers = answer_data.get('textAnswers', {}).get('answers', [])
                    for text_answer in text_answers:
                        value = text_answer.get('value', '').lower().strip()
                        # Simple email pattern check
                        if '@' in value and '.' in value.split('@')[1] if '@' in value else False:
                            respondent_email = value
                            break
                    if respondent_email:
                        break
            
            if not respondent_email or respondent_email not in students_dict:
                # Skip if we can't match to a student
                current_app.logger.warning(f"Could not match Google Form response to a student: {respondent_email}")
                continue
            
            student = students_dict[respondent_email]
            
            # Get submission timestamp
            create_time = response.get('createTime', '')
            submitted_at = datetime.fromisoformat(create_time.replace('Z', '+00:00')) if create_time else datetime.utcnow()
            
            # Check if submission already exists
            existing_submission = Submission.query.filter_by(
                student_id=student.id,
                assignment_id=assignment_id
            ).first()
            
            if not existing_submission:
                # Create new submission
                submission = Submission(
                    student_id=student.id,
                    assignment_id=assignment_id,
                    submitted_at=submitted_at,
                    submission_type='online',
                    comments=f'Synced from Google Form on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}'
                )
                db.session.add(submission)
                created_submissions += 1
            else:
                submission = existing_submission
            
            # Try to extract grade/score from response if available
            # Google Forms quiz responses may have a score
            answers = response.get('answers', {})
            score = None
            total_points = assignment.total_points or 100.0
            
            # Check if this is a quiz with grading
            # Google Forms stores grades in a specific format - we'd need to check the form structure
            # For now, we'll just create submissions and let teachers grade manually
            
            synced_count += 1
        
        db.session.commit()
        
        flash(f'Successfully synced {synced_count} submission(s) from Google Forms ({created_submissions} new).', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error syncing Google Forms submissions: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error syncing Google Forms submissions: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))


@bp.route('/assignment/view/<int:assignment_id>')
@login_required
@teacher_required
def view_assignment(assignment_id):
    """View an assignment"""
    from datetime import date
    from models import Submission, Grade, Enrollment

    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    # For discussion assignments, use specialized view
    if assignment.assignment_type == 'discussion':
        from models import DiscussionThread, DiscussionPost, Student
        from collections import defaultdict
        
        teacher = get_teacher_or_admin()
        
        # Get all threads for this assignment
        threads = DiscussionThread.query.filter_by(assignment_id=assignment_id).order_by(
            DiscussionThread.is_pinned.desc(),
            DiscussionThread.created_at.desc()
        ).all()
        
        # Get all posts
        all_posts = DiscussionPost.query.filter(
            DiscussionPost.thread_id.in_([t.id for t in threads])
        ).all()
        
        # Get all participants (students who posted)
        participant_ids = set()
        for thread in threads:
            participant_ids.add(thread.student_id)
        for post in all_posts:
            participant_ids.add(post.student_id)
        
        # Get enrolled students
        enrollments = Enrollment.query.filter_by(class_id=class_obj.id, is_active=True).all()
        enrolled_students = [e.student for e in enrollments if e.student]
        
        # Get participant details
        participants = []
        for student_id in participant_ids:
            student = Student.query.get(student_id)
            if student:
                threads_count = sum(1 for t in threads if t.student_id == student_id)
                replies_count = sum(1 for p in all_posts if p.student_id == student_id)
                
                participants.append({
                    'student': student,
                    'threads': threads_count,
                    'replies': replies_count,
                    'total_posts': threads_count + replies_count
                })
        
        # Sort participants by total posts (descending)
        participants.sort(key=lambda x: x['total_posts'], reverse=True)
        
        # Get grades for this assignment
        grades = {}
        grade_records = Grade.query.filter_by(assignment_id=assignment_id).all()
        for g in grade_records:
            try:
                if g.grade_data:
                    import json
                    grade_data = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
                    grades[g.student_id] = grade_data
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Extract participation requirements from assignment description
        min_initial_posts = 1
        min_replies = 2
        import re
        if assignment.description:
            initial_posts_match = re.search(r'Minimum (\d+) initial post', assignment.description)
            if initial_posts_match:
                min_initial_posts = int(initial_posts_match.group(1))
            replies_match = re.search(r'Minimum (\d+) reply/replies', assignment.description)
            if replies_match:
                min_replies = int(replies_match.group(1))
        
        return render_template('management/view_discussion_assignment.html',
                             assignment=assignment,
                             class_info=class_obj,
                             teacher=teacher,
                             threads=threads,
                             participants=participants,
                             enrolled_students=enrolled_students,
                             grades=grades,
                             min_initial_posts=min_initial_posts,
                             min_replies=min_replies,
                             role_prefix='teacher')
    
    teacher = get_teacher_or_admin()
    today = date.today()
    
    # Calculate statistics
    total_students = Enrollment.query.filter_by(
        class_id=class_obj.id,
        is_active=True
    ).count()

    # Count unique student submissions for this assignment
    submissions_count = db.session.query(Submission.student_id).filter_by(
        assignment_id=assignment_id
    ).distinct().count()

    non_voided_grades = Grade.query.filter_by(
        assignment_id=assignment_id,
        is_voided=False
    ).all()
    graded_count = len(non_voided_grades)

    assignment_points = assignment.total_points if hasattr(assignment, 'total_points') and assignment.total_points else (assignment.points if assignment.points else 0)
    assignment_points = float(assignment_points or 0)

    # Calculate average percentage from grade data (0 is valid and included)
    average_score = None
    if graded_count > 0:
        total_percentage = 0.0
        count = 0
        for grade in non_voided_grades:
            try:
                if not grade.grade_data:
                    continue
                import json
                grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                if not isinstance(grade_data, dict):
                    continue

                score_raw = grade_data.get('points_earned', grade_data.get('score'))
                if score_raw is None:
                    continue
                points_earned = float(score_raw)
                if assignment_points > 0:
                    percentage = (points_earned / assignment_points) * 100
                else:
                    percentage = float(grade_data.get('percentage', 0))
                total_percentage += percentage
                count += 1
            except (ValueError, TypeError, json.JSONDecodeError):
                continue

        if count > 0:
            average_score = round(total_percentage / count, 1)

    submission_rate = round((submissions_count / total_students * 100) if total_students > 0 else 0, 1)
    grading_rate = round((graded_count / total_students * 100) if total_students > 0 else 0, 1)
    pending_count = max(total_students - graded_count, 0)
    
    # Get voided grades for the unvoid modal
    voided_grades = Grade.query.filter_by(assignment_id=assignment_id, is_voided=True).all()
    voided_student_ids = {g.student_id for g in voided_grades}
    
    return render_template('shared/view_assignment.html', 
                         assignment=assignment,
                         class_info=class_obj,
                         teacher=teacher,
                         today=today,
                         submissions_count=submissions_count,
                         assignment_points=assignment_points,
                         total_students=total_students,
                         graded_count=graded_count,
                         average_score=average_score,
                         submission_rate=submission_rate,
                         grading_rate=grading_rate,
                         pending_count=pending_count,
                         voided_student_ids=voided_student_ids)


@bp.route('/discussion/thread/<int:thread_id>')
@login_required
@teacher_required
def view_discussion_thread(thread_id):
    """View a discussion thread (for teachers)"""
    thread = DiscussionThread.query.get_or_404(thread_id)
    assignment = thread.assignment
    if not assignment or assignment.assignment_type != 'discussion':
        flash("Discussion thread not found.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to view this discussion.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    posts = DiscussionPost.query.filter_by(thread_id=thread_id).order_by(
        DiscussionPost.created_at.asc()
    ).all()
    back_url = url_for('teacher.assignments.view_assignment', assignment_id=assignment.id)
    return render_template('shared/view_discussion_thread.html',
                         assignment=assignment,
                         thread=thread,
                         posts=posts,
                         back_url=back_url,
                         show_reply_form=False)


@bp.route('/assignment/<int:assignment_id>/void', methods=['POST'])
@login_required
@teacher_required
def void_assignment(assignment_id):
    """Void an assignment for all students or a selected subset."""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to void this assignment.", "danger")
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    void_type = request.form.get('void_type', 'all')
    reason = request.form.get('reason', 'Voided by teacher')
    selected_student_ids = request.form.getlist('student_ids')
    
    # Determine which grades to void
    try:
        if void_type == 'selected' and selected_student_ids:
            student_ids = [int(sid) for sid in selected_student_ids]
            grades = Grade.query.filter(
                Grade.assignment_id == assignment_id,
                Grade.student_id.in_(student_ids),
                Grade.is_voided == False
            ).all()
        else:
            grades = Grade.query.filter_by(
                assignment_id=assignment_id,
                is_voided=False
            ).all()
        
        if not grades:
            flash("No grades found to void for this assignment.", "warning")
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
        now = datetime.utcnow()
        voided_count = 0
        affected_students = set()
        
        for grade in grades:
            grade.is_voided = True
            grade.voided_by = current_user.id
            grade.voided_at = now
            grade.voided_reason = reason
            affected_students.add(grade.student_id)
            voided_count += 1
        
        db.session.commit()
        
        # Update quarter grades for affected students
        for student_id in affected_students:
            if student_id:
                try:
                    update_quarter_grade(
                        student_id=student_id,
                        class_id=assignment.class_id,
                        school_year_id=assignment.school_year_id,
                        quarter=assignment.quarter,
                        force=True
                    )
                except Exception as e:
                    current_app.logger.warning(f"Failed to update quarter grade for student {student_id}: {e}")
        
        flash(f'Voided assignment for {voided_count} grade(s).', 'success')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error voiding assignment {assignment_id}: {e}")
        flash(f"Error voiding assignment: {str(e)}", "danger")
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))

@bp.route('/unvoid-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def unvoid_assignment_for_students(assignment_id):
    """Un-void an assignment (restore grades) for all students or specific students."""
    try:
        assignment_type = request.form.get('assignment_type', 'individual')
        student_ids = request.form.getlist('student_ids')
        unvoid_all = request.form.get('unvoid_all', 'false').lower() == 'true'
        
        unvoided_count = 0
        
        if assignment_type == 'group':
            group_assignment = GroupAssignment.query.get_or_404(assignment_id)
            
            if unvoid_all or not student_ids:
                from models import StudentGroupMember, StudentGroup
                
                groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id).all()
                for group in groups:
                    members = StudentGroupMember.query.filter_by(student_group_id=group.id).all()
                    for member in members:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=member.student_id,
                            is_voided=True
                        ).first()
                        
                        if group_grade:
                            group_grade.is_voided = False
                            group_grade.voided_by = None
                            group_grade.voided_at = None
                            group_grade.voided_reason = None
                            unvoided_count += 1
                
                message = f'Restored group assignment "{group_assignment.title}" for all students ({unvoided_count} grades)'
            else:
                from models import StudentGroupMember
                for student_id in student_ids:
                    member = StudentGroupMember.query.filter_by(student_id=int(student_id)).first()
                    if member:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=int(student_id),
                            is_voided=True
                        ).first()
                        
                        if group_grade:
                            group_grade.is_voided = False
                            group_grade.voided_by = None
                            group_grade.voided_at = None
                            group_grade.voided_reason = None
                            unvoided_count += 1
                
                message = f'Restored group assignment "{group_assignment.title}" for {unvoided_count} student(s)'
        else:
            assignment = Assignment.query.get_or_404(assignment_id)
            class_obj = assignment.class_info
            
            if not class_obj:
                flash("Assignment class information not found.", "danger")
                return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            
            if not is_authorized_for_class(class_obj):
                flash("You are not authorized to unvoid this assignment.", "danger")
                return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            
            if unvoid_all or not student_ids:
                # Unvoid for all students
                enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
                
                for enrollment in enrollments:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=enrollment.student_id,
                        is_voided=True
                    ).first()
                    
                    if grade:
                        # Restore grade data from history if available
                        history_entry = GradeHistory.query.filter_by(
                            grade_id=grade.id
                        ).order_by(GradeHistory.changed_at.desc()).first()
                        
                        if history_entry and history_entry.previous_grade_data:
                            # Restore original grade data from history
                            try:
                                grade.grade_data = history_entry.previous_grade_data
                            except Exception as e:
                                current_app.logger.warning(f"Could not restore grade data from history: {e}")
                        
                        grade.is_voided = False
                        grade.voided_by = None
                        grade.voided_at = None
                        grade.voided_reason = None
                        unvoided_count += 1
                
                message = f'Restored assignment "{assignment.title}" for all students ({unvoided_count} grades)'
            else:
                # Unvoid for specific students
                for student_id in student_ids:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=int(student_id),
                        is_voided=True
                    ).first()
                    
                    if grade:
                        # Restore grade data from history if available
                        history_entry = GradeHistory.query.filter_by(
                            grade_id=grade.id
                        ).order_by(GradeHistory.changed_at.desc()).first()
                        
                        if history_entry and history_entry.previous_grade_data:
                            # Restore original grade data from history
                            try:
                                grade.grade_data = history_entry.previous_grade_data
                            except Exception as e:
                                current_app.logger.warning(f"Could not restore grade data from history: {e}")
                        
                        grade.is_voided = False
                        grade.voided_by = None
                        grade.voided_at = None
                        grade.voided_reason = None
                        unvoided_count += 1
                
                message = f'Restored assignment "{assignment.title}" for {unvoided_count} student(s)'
        
        db.session.commit()
        
        # Update quarter grades for affected students (force recalculation)
        if assignment_type == 'individual':
            quarter = assignment.quarter
            school_year_id = assignment.school_year_id
            class_id = assignment.class_id
        else:
            quarter = group_assignment.quarter
            school_year_id = group_assignment.school_year_id
            class_id = group_assignment.class_id
        
        # Refresh quarter grades for affected students
        students_to_update = []
        if student_ids:
            students_to_update = student_ids
        else:
            if assignment_type == 'individual':
                students_to_update = [g.student_id for g in Grade.query.filter_by(assignment_id=assignment_id).all()]
            else:
                students_to_update = [g.student_id for g in GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()]
        
        for sid in students_to_update:
            try:
                update_quarter_grade(
                    student_id=int(sid),
                    class_id=class_id,
                    school_year_id=school_year_id,
                    quarter=quarter,
                    force=True
                )
            except Exception as e:
                current_app.logger.warning(f"Could not update quarter grade for student {sid}: {e}")
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        
        if is_ajax:
            return jsonify({'success': True, 'message': message, 'unvoided_count': unvoided_count})
        else:
            flash(message, 'success')
            if assignment_type == 'individual':
                return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            else:
                return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
    except Exception as e:
        db.session.rollback()
        error_message = f'Error unvoiding assignment: {str(e)}'
        current_app.logger.error(error_message)
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        
        if is_ajax:
            return jsonify({'success': False, 'message': error_message}), 500
        else:
            flash(error_message, 'danger')
            assignment_type = request.form.get('assignment_type', 'individual')
            if assignment_type == 'individual':
                return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            else:
                return redirect(url_for('teacher.dashboard.assignments_and_grades'))

@bp.route('/class/<int:class_id>/enrolled-students-json', methods=['GET'])
@login_required
@teacher_required
def get_enrolled_students_json(class_id):
    """Get enrolled students for a class as JSON (for void/bulk-void modal). Teacher must be authorized for the class."""
    from models import Class
    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        return jsonify({'success': False, 'message': 'Not authorized for this class.'}), 403
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students_data = []
    for enrollment in enrollments:
        if enrollment.student:
            students_data.append({
                'id': enrollment.student.id,
                'first_name': enrollment.student.first_name,
                'last_name': enrollment.student.last_name,
                'grade_level': enrollment.student.grade_level,
                'student_id': enrollment.student.student_id
            })
    return jsonify({'success': True, 'students': students_data})

@bp.route('/bulk-void-assignments', methods=['POST'])
@login_required
@teacher_required
def bulk_void_assignments():
    """Void multiple assignments at once for all or selected students (teacher-authorized classes only)."""
    try:
        from management_routes.students import _void_one_assignment_impl
        data = request.get_json(force=True, silent=True) or {}
        assignment_specs = data.get('assignment_specs', [])
        if not assignment_specs:
            assignment_ids = data.get('assignment_ids', [])
            assignment_types = data.get('assignment_types', [])
            if not assignment_ids or len(assignment_types) != len(assignment_ids):
                return jsonify({'success': False, 'message': 'Provide assignment_specs or assignment_ids and assignment_types.'}), 400
            assignment_specs = [{'id': int(aid), 'type': t} for aid, t in zip(assignment_ids, assignment_types)]
        else:
            assignment_specs = [{'id': int(s['id']), 'type': s.get('type', 'individual')} for s in assignment_specs]
        if not assignment_specs:
            return jsonify({'success': False, 'message': 'No assignments selected.'}), 400
        void_all = data.get('void_all', True)
        student_ids = data.get('student_ids', [])
        if isinstance(student_ids, str):
            student_ids = [student_ids] if student_ids else []
        student_ids = [int(s) for s in student_ids]
        reason = data.get('reason', 'Voided by teacher')
        total_voided = 0
        all_affected = []
        errors = []
        for spec in assignment_specs:
            aid, atype = spec['id'], spec['type']
            try:
                if atype == 'group':
                    ga = GroupAssignment.query.get(aid)
                    if not ga:
                        errors.append(f"Group assignment {aid} not found.")
                        continue
                    if not is_authorized_for_class(ga.class_info):
                        errors.append(f"Not authorized for class of assignment {aid}.")
                        continue
                else:
                    a = Assignment.query.get(aid)
                    if not a:
                        errors.append(f"Assignment {aid} not found.")
                        continue
                    if not is_authorized_for_class(a.class_info):
                        errors.append(f"Not authorized for class of assignment {aid}.")
                        continue
                voided_count, affected = _void_one_assignment_impl(aid, atype, student_ids, void_all, reason)
                total_voided += voided_count
                all_affected.extend(affected)
            except Exception as e:
                errors.append(f"Assignment {aid} ({atype}): {str(e)}")
                current_app.logger.warning(f"Bulk void failed for assignment {aid}: {e}")
        db.session.commit()
        seen = set()
        for (sid, cid, syid, q) in all_affected:
            key = (sid, cid, q)
            if key not in seen:
                seen.add(key)
                try:
                    update_quarter_grade(student_id=int(sid), class_id=cid, school_year_id=syid, quarter=q, force=True)
                except Exception as e:
                    current_app.logger.warning(f"Could not update quarter grade for student {sid}: {e}")
        message = f'Bulk void complete: {total_voided} grade(s) voided across {len(assignment_specs)} assignment(s).'
        if errors:
            message += ' Partial errors: ' + '; '.join(errors[:3])
        return jsonify({
            'success': True,
            'message': message,
            'voided_count': total_voided,
            'assignments_processed': len(assignment_specs),
            'errors': errors
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/extension-requests')
@login_required
@teacher_required
def view_extension_requests():
    """View all extension requests for teacher's assignments"""
    from models import ExtensionRequest, Class
    from datetime import datetime
    
    teacher = get_teacher_or_admin()
    
    if is_admin():
        # Administrators see all extension requests
        extension_requests = ExtensionRequest.query.order_by(ExtensionRequest.requested_at.desc()).all()
    else:
        # Teachers see extension requests for their classes only
        if teacher is None:
            extension_requests = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            class_ids = [c.id for c in classes]
            assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
            assignment_ids = [a.id for a in assignments]
            extension_requests = ExtensionRequest.query.filter(
                ExtensionRequest.assignment_id.in_(assignment_ids)
            ).order_by(ExtensionRequest.requested_at.desc()).all()
    
    # Group requests by status
    pending_requests = [req for req in extension_requests if req.status == 'Pending']
    approved_requests = [req for req in extension_requests if req.status == 'Approved']
    rejected_requests = [req for req in extension_requests if req.status == 'Rejected']
    
    return render_template('teachers/extension_requests.html',
                         pending_requests=pending_requests,
                         approved_requests=approved_requests,
                         rejected_requests=rejected_requests,
                         total_count=len(extension_requests))

@bp.route('/extension-request/<int:request_id>/review', methods=['POST'])
@login_required
@teacher_required
def review_extension_request(request_id):
    """Approve or reject an extension request"""
    from models import ExtensionRequest, AssignmentExtension
    from datetime import datetime
    
    extension_request = ExtensionRequest.query.get_or_404(request_id)
    assignment = extension_request.assignment
    
    # Authorization check
    teacher = get_teacher_or_admin()
    if not is_admin():
        if teacher is None:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        if assignment.class_info.teacher_id != teacher.id:
            return jsonify({'success': False, 'message': 'You are not authorized to review this request'}), 403
    
    action = request.form.get('action')  # 'approve' or 'reject'
    review_notes = request.form.get('review_notes', '').strip()
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    try:
        if action == 'approve':
            # Update extension request status
            extension_request.status = 'Approved'
            extension_request.reviewed_at = datetime.utcnow()
            extension_request.reviewed_by = teacher.id if teacher else None
            extension_request.review_notes = review_notes if review_notes else None
            
            # Create or update AssignmentExtension
            existing_extension = AssignmentExtension.query.filter_by(
                assignment_id=assignment.id,
                student_id=extension_request.student_id,
                is_active=True
            ).first()
            
            if existing_extension:
                # Update existing extension
                existing_extension.extended_due_date = extension_request.requested_due_date
                existing_extension.reason = review_notes if review_notes else 'Extension granted'
            else:
                # Create new extension
                new_extension = AssignmentExtension(
                    assignment_id=assignment.id,
                    student_id=extension_request.student_id,
                    extended_due_date=extension_request.requested_due_date,
                    reason=review_notes if review_notes else 'Extension granted',
                    granted_by=teacher.id if teacher else None,
                    is_active=True
                )
                db.session.add(new_extension)
            
            message = f'Extension request approved. New due date: {extension_request.requested_due_date.strftime("%Y-%m-%d %I:%M %p")}'
        else:
            # Reject extension request
            extension_request.status = 'Rejected'
            extension_request.reviewed_at = datetime.utcnow()
            extension_request.reviewed_by = teacher.id if teacher else None
            extension_request.review_notes = review_notes if review_notes else 'Extension request rejected'

            message = 'Extension request rejected'

        db.session.commit()

        # Notify the student that their extension request was accepted or rejected (don't fail the request if this fails)
        try:
            student_user = getattr(extension_request.student, 'user', None)
            if student_user and student_user.id:
                from app import create_notification
                assign_title = extension_request.assignment.title
                if action == 'approve':
                    create_notification(
                        student_user.id,
                        'extension_request',
                        'Extension request approved',
                        f'Your extension request for "{assign_title}" was approved. New due date: {extension_request.requested_due_date.strftime("%B %d, %Y at %I:%M %p")}.',
                        link=url_for('student.student_assignments')
                    )
                else:
                    create_notification(
                        student_user.id,
                        'extension_request',
                        'Extension request not approved',
                        f'Your extension request for "{assign_title}" was not approved.' + (f' Note: {review_notes}' if review_notes else ''),
                        link=url_for('student.student_assignments')
                    )
        except Exception as notify_err:
            current_app.logger.warning(f"Could not create extension notification for student: {notify_err}")

        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reviewing extension request: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing request: {str(e)}'}), 500

@bp.route('/assignment/grant-extensions', methods=['POST'])
@login_required
@teacher_required
def grant_extensions():
    """Grant extensions to students for an assignment"""
    try:
        assignment_id = request.form.get('assignment_id', type=int)
        class_id = request.form.get('class_id', type=int)
        extended_due_date_str = request.form.get('extended_due_date')
        reason = request.form.get('reason', '')
        student_ids = request.form.getlist('student_ids')
        
        if not all([assignment_id, class_id, extended_due_date_str, student_ids]):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Parse the extended due date
        try:
            extended_due_date = datetime.strptime(extended_due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            extended_due_date = datetime.strptime(extended_due_date_str, '%Y-%m-%d')
        
        # Get the assignment
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = assignment.class_info
        
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class information not found.'})
        
        # Authorization check - teachers can grant extensions for their own classes
        if not is_authorized_for_class(class_obj):
            return jsonify({'success': False, 'message': 'You are not authorized to grant extensions for this assignment.'})
        
        # Get the teacher_staff_id for granted_by field
        teacher = get_teacher_or_admin()
        granter_id = teacher.id if teacher else None
        
        if not granter_id:
            return jsonify({'success': False, 'message': 'Cannot grant extensions: No teacher found.'})
        
        granted_count = 0
        
        for student_id in student_ids:
            try:
                student_id = int(student_id)
                
                # Deactivate any existing active extensions for this student and assignment
                existing_extensions = AssignmentExtension.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    is_active=True
                ).all()
                
                for ext in existing_extensions:
                    ext.is_active = False
                
                # Create new extension
                extension = AssignmentExtension(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    extended_due_date=extended_due_date,
                    reason=reason,
                    granted_by=granter_id,
                    is_active=True
                )
                
                db.session.add(extension)
                granted_count += 1
                
            except (ValueError, TypeError):
                continue  # Skip invalid student IDs
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully granted extensions to {granted_count} student(s).',
            'granted_count': granted_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error granting extensions: {str(e)}")
        return jsonify({'success': False, 'message': f'Error granting extensions: {str(e)}'})

@bp.route('/assignment/<int:assignment_id>/reopen', methods=['POST'])
@login_required
@teacher_required
def reopen_assignment(assignment_id):
    """Reopen an assignment for selected students (allows access to inactive/closed assignments and grants additional attempts for quizzes)"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = assignment.class_info
        
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class information not found.'})
        
        if not is_authorized_for_class(class_obj):
            return jsonify({'success': False, 'message': 'You are not authorized to reopen this assignment.'})
        
        # Get form data
        student_ids = request.form.getlist('student_ids')
        reason = request.form.get('reason', '')
        additional_attempts = request.form.get('additional_attempts', type=int, default=0)
        
        if not student_ids:
            return jsonify({'success': False, 'message': 'Please select at least one student.'})
        
        # For quizzes, additional_attempts is required
        if assignment.assignment_type == 'quiz' and additional_attempts <= 0:
            return jsonify({'success': False, 'message': 'For quiz assignments, you must specify the number of additional attempts to grant.'})
        
        # Get the teacher_staff_id
        teacher = get_teacher_or_admin()
        reopened_by_id = teacher.id if teacher else None
        
        if not reopened_by_id:
            return jsonify({'success': False, 'message': 'Cannot reopen assignment: No teacher found.'})
        
        reopened_count = 0
        skipped_voided_grade = 0
        
        for student_id in student_ids:
            try:
                student_id = int(student_id)
                
                # Check if student is enrolled
                enrollment = Enrollment.query.filter_by(
                    student_id=student_id,
                    class_id=class_obj.id,
                    is_active=True
                ).first()
                
                if not enrollment:
                    continue  # Skip if not enrolled

                st_grade = Grade.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                ).first()
                if st_grade and st_grade.is_voided:
                    skipped_voided_grade += 1
                    continue
                
                # Deactivate any existing active reopenings for this student and assignment
                existing_reopenings = AssignmentReopening.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    is_active=True
                ).all()
                
                for reopening in existing_reopenings:
                    reopening.is_active = False
                
                # Create new reopening
                reopening = AssignmentReopening(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    reopened_by=reopened_by_id,
                    reason=reason,
                    additional_attempts=additional_attempts if assignment.assignment_type == 'quiz' else 0,
                    is_active=True
                )
                
                db.session.add(reopening)
                reopened_count += 1
                
            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Invalid student ID in reopen request: {student_id}, error: {e}")
                continue
        
        db.session.commit()
        
        if reopened_count == 0 and skipped_voided_grade > 0:
            return jsonify({
                'success': False,
                'message': (
                    f'No students were reopened. {skipped_voided_grade} selected student(s) have a voided grade. '
                    'Un-void the grade (Restore assignment) first; then reopen or grant attempts will apply.'
                ),
                'reopened_count': 0,
                'skipped_voided_grade': skipped_voided_grade,
            })
        
        message = f'Successfully reopened assignment for {reopened_count} student(s).'
        if assignment.assignment_type == 'quiz' and additional_attempts > 0:
            message += f' Each student has been granted {additional_attempts} additional attempt(s).'
        if skipped_voided_grade:
            message += (
                f' Skipped {skipped_voided_grade} student(s) with voided grades '
                '(un-void those grades first).'
            )
        
        return jsonify({
            'success': True,
            'message': message,
            'reopened_count': reopened_count,
            'skipped_voided_grade': skipped_voided_grade,
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reopening assignment: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error reopening assignment: {str(e)}'})

@bp.route('/assignment/<int:assignment_id>/reopen-status', methods=['GET'])
@login_required
@teacher_required
def get_reopen_status(assignment_id):
    """Get reopening status for all students in the assignment's class"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = assignment.class_info
        
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class information not found.'})
        
        if not is_authorized_for_class(class_obj):
            return jsonify({'success': False, 'message': 'You are not authorized to view this assignment.'})
        
        # Get all enrolled students
        enrollments = Enrollment.query.filter_by(
            class_id=class_obj.id,
            is_active=True
        ).all()
        
        from models import Student
        from teacher_routes.assignment_utils import is_assignment_open_for_student
        student_data = []
        
        for enrollment in enrollments:
            if not enrollment.student:
                continue
            
            student = enrollment.student
            
            st_grade = Grade.query.filter_by(
                assignment_id=assignment_id,
                student_id=student.id,
            ).first()
            grade_is_voided = bool(st_grade and st_grade.is_voided)
            
            # Get active reopening if any
            reopening = AssignmentReopening.query.filter_by(
                assignment_id=assignment_id,
                student_id=student.id,
                is_active=True
            ).first()
            
            # Get submission count (for quizzes)
            submissions_count = 0
            if assignment.assignment_type == 'quiz':
                submissions_count = Submission.query.filter_by(
                    student_id=student.id,
                    assignment_id=assignment_id
                ).count()
            
            # Determine if student needs reopening
            needs_reopening = False
            reason_needs_reopening = []
            
            # For quizzes: status-based + max attempts
            if assignment.assignment_type == 'quiz':
                if assignment.status not in ['Active']:
                    needs_reopening = True
                    reason_needs_reopening.append(f'Assignment is {assignment.status.lower()}')
                if assignment.max_attempts and submissions_count >= assignment.max_attempts:
                    needs_reopening = True
                    reason_needs_reopening.append(f'Max attempts ({assignment.max_attempts}) reached')
            else:
                # PDF/Paper, discussion, etc.: use canonical can_submit check
                can_submit = is_assignment_open_for_student(assignment, student.id)
                needs_reopening = not can_submit
                if needs_reopening and assignment.status not in ['Active']:
                    reason_needs_reopening.append(f'Assignment is {assignment.status.lower()}')
                elif needs_reopening and not reason_needs_reopening:
                    reason_needs_reopening.append('Cannot submit (closed or outside access window)')
            
            if grade_is_voided:
                reason_needs_reopening.insert(
                    0,
                    'Grade voided for this student (un-void first or reopen will not apply on the student side)',
                )
            
            student_data.append({
                'student_id': student.id,
                'name': f'{student.first_name} {student.last_name}',
                'has_reopening': reopening is not None,
                'additional_attempts': reopening.additional_attempts if reopening else 0,
                'reopened_at': reopening.reopened_at.isoformat() if reopening and reopening.reopened_at else None,
                'needs_reopening': needs_reopening,
                'reason_needs_reopening': ', '.join(reason_needs_reopening) if reason_needs_reopening else None,
                'submissions_count': submissions_count,
                'max_attempts': assignment.max_attempts if assignment.assignment_type == 'quiz' else None,
                'grade_is_voided': grade_is_voided,
            })
        
        return jsonify({
            'success': True,
            'students': student_data,
            'assignment_type': assignment.assignment_type,
            'assignment_status': assignment.status,
            'max_attempts': assignment.max_attempts if assignment.assignment_type == 'quiz' else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting reopen status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error getting reopen status: {str(e)}'})

@bp.route('/assignment/<int:assignment_id>/revoke-reopen', methods=['POST'])
@login_required
@teacher_required
def revoke_reopen(assignment_id):
    """Revoke (deactivate) reopenings for selected students"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = assignment.class_info
        
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class information not found.'})
        
        if not is_authorized_for_class(class_obj):
            return jsonify({'success': False, 'message': 'You are not authorized to revoke reopenings for this assignment.'})
        
        student_ids = request.form.getlist('student_ids')
        
        if not student_ids:
            return jsonify({'success': False, 'message': 'Please select at least one student.'})
        
        revoked_count = 0
        
        for student_id in student_ids:
            try:
                student_id = int(student_id)
                
                # Find and deactivate active reopenings
                reopenings = AssignmentReopening.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    is_active=True
                ).all()
                
                for reopening in reopenings:
                    reopening.is_active = False
                    revoked_count += 1
                
            except (ValueError, TypeError):
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully revoked reopenings for {revoked_count} student(s).',
            'revoked_count': revoked_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error revoking reopenings: {str(e)}")
        return jsonify({'success': False, 'message': f'Error revoking reopenings: {str(e)}'})

@bp.route('/assignment/<int:assignment_id>/change-status', methods=['POST'])
@login_required
@teacher_required
def change_assignment_status(assignment_id):
    """Change the status of an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to change the status of this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    new_status = request.form.get('status')
    if not new_status:
        flash("Status is required.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    # Validate status value
    valid_statuses = ['Active', 'Inactive', 'Upcoming', 'Voided', 'Overdue']
    if new_status not in valid_statuses:
        flash(f"Invalid status: {new_status}. Must be one of {', '.join(valid_statuses)}", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    try:
        assignment.status = new_status
        # When reopening (Inactive -> Active): extend close_date if it's in the past (or set if missing)
        # so update_assignment_statuses() won't immediately revert the status
        if new_status == 'Active':
            from datetime import timezone
            now = datetime.now(timezone.utc)
            need_extend = False
            if assignment.close_date:
                close_dt = assignment.close_date
                if hasattr(close_dt, 'tzinfo') and close_dt.tzinfo is None:
                    close_dt = close_dt.replace(tzinfo=timezone.utc)
                need_extend = close_dt < now
            else:
                need_extend = True
            if need_extend:
                import pytz
                tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
                school_tz = pytz.timezone(tz_name)
                end_of_today = datetime.now(school_tz).replace(hour=23, minute=59, second=59, microsecond=999999)
                assignment.close_date = end_of_today.astimezone(pytz.UTC)
        db.session.commit()
        flash(f'Assignment status changed to {new_status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing assignment status: {str(e)}")
        flash(f'Error changing assignment status: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.dashboard.assignments_and_grades'))

@bp.route('/assignment/<int:assignment_id>/submissions')
@login_required
@teacher_required
def view_assignment_submissions(assignment_id):
    """View all submissions for an assignment"""
    from models import Submission, Enrollment, Student, Grade
    from datetime import datetime
    from collections import defaultdict
    from teacher_routes.assignment_utils import parse_quiz_submission_auto_score

    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view submissions for this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    # Get all enrolled students
    enrollments = Enrollment.query.filter_by(
        class_id=class_obj.id,
        is_active=True
    ).all()
    
    student_ids = [e.student_id for e in enrollments if e.student_id]
    students = Student.query.filter(Student.id.in_(student_ids)).order_by(
        Student.last_name, Student.first_name
    ).all()
    
    # All submissions (quizzes may have multiple rows per student — one per completed attempt)
    submissions = Submission.query.filter_by(assignment_id=assignment_id).order_by(
        Submission.submitted_at.asc()
    ).all()
    submissions_by_student = defaultdict(list)
    for sub in submissions:
        submissions_by_student[sub.student_id].append(sub)

    # Latest grade row per student (quiz retakes consolidate to one authoritative grade)
    grades_ordered = Grade.query.filter_by(assignment_id=assignment_id).order_by(
        Grade.graded_at.desc()
    ).all()
    grades_dict = {}
    for g in grades_ordered:
        if g.student_id not in grades_dict:
            grades_dict[g.student_id] = g

    # Get extensions
    extensions = AssignmentExtension.query.filter_by(
        assignment_id=assignment_id,
        is_active=True
    ).all()
    extensions_dict = {ext.student_id: ext for ext in extensions}

    # Calculate statistics
    total_students = len(students)
    students_with_submission = set(submissions_by_student.keys())
    submitted_count = len(students_with_submission)
    quiz_total_attempts = len(submissions) if assignment.assignment_type == 'quiz' else None
    graded_count = len([g for g in grades_dict.values() if not g.is_voided])
    late_count = 0
    on_time_count = 0
    
    for submission in submissions:
        due_date = assignment.due_date
        if submission.student_id in extensions_dict:
            due_date = extensions_dict[submission.student_id].extended_due_date
        
        if submission.submitted_at > due_date:
            late_count += 1
        else:
            on_time_count += 1
    
    # Prepare student data with submission status
    student_data = []
    for student in students:
        subs_for_student = submissions_by_student.get(student.id, [])
        submission = subs_for_student[-1] if subs_for_student else None
        grade = grades_dict.get(student.id)

        quiz_attempts = []
        if assignment.assignment_type == 'quiz' and subs_for_student:
            for sub in subs_for_student:
                quiz_attempts.append({
                    'attempt_num': len(quiz_attempts) + 1,
                    'submission': sub,
                    'parsed_score': parse_quiz_submission_auto_score(sub.comments),
                })

        # Determine submission status (based on most recent attempt)
        if submission:
            due_date = assignment.due_date
            if student.id in extensions_dict:
                due_date = extensions_dict[student.id].extended_due_date
            
            is_late = submission.submitted_at > due_date
            status = 'late' if is_late else 'on_time'
            submission_type = submission.submission_type or 'online'
        else:
            status = 'not_submitted'
            submission_type = None
        
        # Get grade info (active) or void metadata for display
        grade_info = None
        void_info = None
        if grade and grade.is_voided:
            void_info = {
                'reason': grade.voided_reason or '',
                'voided_at': grade.voided_at,
            }
            if grade.grade_data:
                try:
                    import json
                    grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                    void_info['score_snapshot'] = grade_data.get('percentage', grade_data.get('score'))
                except (json.JSONDecodeError, TypeError):
                    pass
        elif grade and not grade.is_voided:
            try:
                import json
                grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                grade_info = {
                    'score': grade_data.get('score', 0),
                    'percentage': grade_data.get('percentage', 0),
                    'comment': grade_data.get('comment', '') or grade_data.get('feedback', ''),
                    'graded_at': grade.graded_at
                }
            except (json.JSONDecodeError, TypeError):
                grade_info = {'score': 0, 'percentage': 0, 'comment': '', 'graded_at': None}
        
        has_grade_record = grade is not None
        
        student_data.append({
            'student': student,
            'submission': submission,
            'grade': grade_info,
            'void_info': void_info,
            'has_grade_record': has_grade_record,
            'status': status,
            'submission_type': submission_type,
            'extension': extensions_dict.get(student.id),
            'quiz_attempts': quiz_attempts,
        })
    
    # Sort by status: submitted first, then not submitted
    student_data.sort(key=lambda x: (
        0 if x['status'] != 'not_submitted' else 1,
        x['student'].last_name,
        x['student'].first_name
    ))
    
    return render_template('teachers/teacher_view_submissions.html',
                         assignment=assignment,
                         class_obj=class_obj,
                         students=student_data,
                         total_students=total_students,
                         submitted_count=submitted_count,
                         quiz_total_attempts=quiz_total_attempts,
                         graded_count=graded_count,
                         late_count=late_count,
                         on_time_count=on_time_count,
                         submission_rate=round((submitted_count / total_students * 100) if total_students > 0 else 0, 1))

@bp.route('/assignment/<int:assignment_id>/submission/<int:submission_id>/download')
@login_required
@teacher_required
def download_submission(assignment_id, submission_id):
    """Download a student submission file"""
    from flask import send_file
    from models import Submission
    import os
    
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = Submission.query.get_or_404(submission_id)
    
    # Verify submission belongs to assignment
    if submission.assignment_id != assignment_id:
        flash("Invalid submission.", "danger")
        return redirect(url_for('teacher.assignments.view_assignment_submissions', assignment_id=assignment_id))
    
    # Check authorization
    class_obj = assignment.class_info
    if not class_obj or not is_authorized_for_class(class_obj):
        flash("You are not authorized to download this submission.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
    # Get file path
    if not submission.file_path:
        flash("No file found for this submission.", "warning")
        return redirect(url_for('teacher.assignments.view_assignment_submissions', assignment_id=assignment_id))
    
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], submission.file_path)
    
    if not os.path.exists(file_path):
        flash("Submission file not found on server.", "warning")
        return redirect(url_for('teacher.assignments.view_assignment_submissions', assignment_id=assignment_id))
    
    # Get student name for filename
    student = submission.student
    student_name = f"{student.last_name}_{student.first_name}" if student else "student"
    file_ext = os.path.splitext(submission.file_path)[1]
    download_filename = f"{assignment.title}_{student_name}{file_ext}"
    
    return send_file(file_path, as_attachment=True, download_name=download_filename)

@bp.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    import os
    import traceback
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = assignment.class_info
        
        if not class_obj:
            error_msg = 'Assignment class information not found.'
            current_app.logger.error(f"Remove assignment error: {error_msg}")
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
        # Check authorization
        if not is_authorized_for_class(class_obj):
            error_msg = 'You are not authorized to remove this assignment.'
            current_app.logger.warning(f"Unauthorized attempt to remove assignment {assignment_id} by user {current_user.id}")
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 403
            flash(error_msg, "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
        # Delete associated extensions first
        from models import AssignmentExtension
        AssignmentExtension.query.filter_by(assignment_id=assignment_id).delete()
        
        # Delete associated deadline reminders (use direct query to avoid loading relationship)
        from models import DeadlineReminder
        # Use raw SQL directly to avoid ORM trying to load columns that may not exist
        # Must delete BEFORE deleting assignment to avoid relationship access
        try:
            db.session.execute(
                db.text("DELETE FROM deadline_reminder WHERE assignment_id = :assignment_id"),
                {"assignment_id": assignment_id}
            )
            # Flush to ensure deletion is processed before assignment deletion
            db.session.flush()
        except Exception as e:
            current_app.logger.warning(f"Could not delete deadline reminders: {e}")
        
        # Delete associated file if it exists
        if assignment.attachment_filename:
            # Check if it's in the assignments subfolder
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments', assignment.attachment_filename)
            if not os.path.exists(filepath):
                # Try the root upload folder
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.attachment_filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    current_app.logger.info(f"Deleted assignment file: {filepath}")
                except Exception as e:
                    current_app.logger.warning(f"Could not delete assignment file {filepath}: {e}")
        
        # Delete the assignment
        db.session.delete(assignment)
        db.session.commit()
        
        current_app.logger.info(f"Successfully removed assignment {assignment_id} by user {current_user.id}")
        
        # Return JSON for AJAX requests
        if is_ajax:
            return jsonify({'success': True, 'message': 'Assignment removed successfully.'})
        
        flash('Assignment removed successfully.', 'success')
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
    except Exception as e:
        db.session.rollback()
        error_message = f'Error removing assignment: {str(e)}'
        error_traceback = traceback.format_exc()
        current_app.logger.error(f"Remove assignment exception: {error_message}\n{error_traceback}")
        
        # Return JSON for AJAX requests
        if is_ajax:
            return jsonify({'success': False, 'message': error_message}), 500
        
        flash(error_message, 'danger')
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))


@bp.route('/group-assignment/<int:assignment_id>/view')
@login_required
@teacher_required
def view_group_assignment(assignment_id):
    """View details of a specific group assignment - Teacher view."""
    import json
    from datetime import datetime, timedelta
    
    try:
        from types import SimpleNamespace
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        
        # Check authorization - teacher must be authorized for this class
        if not is_authorized_for_class(group_assignment.class_info):
            flash("You are not authorized to view this group assignment.", "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
        # Get submissions for this assignment
        submissions = GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all()
        
        # Get groups for this class - filter by selected groups if specified
        if group_assignment.selected_group_ids:
            # Parse the selected group IDs
            try:
                selected_ids = json.loads(group_assignment.selected_group_ids) if isinstance(group_assignment.selected_group_ids, str) else group_assignment.selected_group_ids
                # Filter to only selected groups
                groups = StudentGroup.query.filter(
                    StudentGroup.class_id == group_assignment.class_id,
                    StudentGroup.is_active == True,
                    StudentGroup.id.in_(selected_ids)
                ).all()
            except:
                # If parsing fails, get all groups
                groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
        else:
            # If no specific groups selected, get all groups
            groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
        
        # Get extensions for this group assignment
        try:
            from models import GroupAssignmentExtension
            extensions = GroupAssignmentExtension.query.filter_by(group_assignment_id=assignment_id, is_active=True).all()
        except Exception:
            extensions = []
        
        # Calculate enhanced statistics
        # Get all group grades (including voided ones for the unvoid button check)
        all_group_grades = GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()
        non_voided_grades = [g for g in all_group_grades if not g.is_voided]  # Non-voided for graded count
        graded_count = len(non_voided_grades)

        # Preserve visibility for grades from deleted/inactive groups.
        student_ids_in_groups = set()
        for group in groups:
            for member in getattr(group, 'members', []):
                if getattr(member, 'student_id', None):
                    student_ids_in_groups.add(member.student_id)
        orphan_student_ids = [
            g.student_id for g in all_group_grades
            if g.student_id and g.student_id not in student_ids_in_groups
        ]
        if orphan_student_ids:
            orphan_students = Student.query.filter(Student.id.in_(set(orphan_student_ids))).all()
            if orphan_students:
                virtual_group = SimpleNamespace(
                    id=0,
                    name='Students from deleted group',
                    members=[SimpleNamespace(student=s, student_id=s.id) for s in orphan_students]
                )
                groups.append(virtual_group)
        
        # Calculate total students in groups
        from models import StudentGroupMember
        total_students = 0
        for group in groups:
            if getattr(group, 'id', None) == 0:
                total_students += len(getattr(group, 'members', []))
            else:
                members = StudentGroupMember.query.filter_by(group_id=group.id).all()
                total_students += len(members)
        
        # Calculate submission statistics
        submitted_group_ids = {s.group_id for s in submissions if getattr(s, 'group_id', None)}
        group_submission_count = len(submitted_group_ids)

        # Student-level submissions from GroupSubmission + GroupGrade(in_person/online)
        import json
        submission_student_ids = set()
        for gs in submissions:
            if (getattr(gs, 'attachment_file_path', None) or getattr(gs, 'attachment_filename', None)) and getattr(gs, 'group_id', None):
                group_obj = gs.group if hasattr(gs, 'group') else None
                if group_obj and hasattr(group_obj, 'members'):
                    for m in group_obj.members:
                        submission_student_ids.add(m.student_id)
        for gg in all_group_grades:
            if gg.grade_data and not gg.is_voided:
                try:
                    gd = json.loads(gg.grade_data) if isinstance(gg.grade_data, str) else gg.grade_data
                    if gd.get('submission_type') in ('in_person', 'online'):
                        submission_student_ids.add(gg.student_id)
                except (json.JSONDecodeError, TypeError):
                    pass
        submission_count = len(submission_student_ids)
        late_submissions = len([s for s in submissions if getattr(s, 'is_late', False)])
        on_time_submissions = max(0, group_submission_count - late_submissions)
        
        # Group-level submission rate (submitted groups / total groups)
        submission_rate = (group_submission_count / len(groups) * 100) if groups else 0
        
        # Calculate time remaining/overdue
        now = datetime.utcnow()
        time_info = {}
        if group_assignment.due_date:
            if group_assignment.due_date > now:
                time_diff = group_assignment.due_date - now
                days_remaining = time_diff.days
                hours_remaining = time_diff.seconds // 3600
                time_info = {
                    'status': 'upcoming',
                    'days': days_remaining,
                    'hours': hours_remaining,
                    'is_overdue': False
                }
            else:
                time_diff = now - group_assignment.due_date
                days_overdue = time_diff.days
                hours_overdue = time_diff.seconds // 3600
                time_info = {
                    'status': 'overdue',
                    'days': days_overdue,
                    'hours': hours_overdue,
                    'is_overdue': True
                }
        else:
            time_info = {
                'status': 'no_due_date',
                'is_overdue': False
            }
        
        # Determine assignment status badge
        if non_voided_grades and len(non_voided_grades) > 0:
            assignment_status = 'Graded'
            status_class = 'success'
        elif group_assignment.status == 'Inactive':
            assignment_status = 'Inactive'
            status_class = 'secondary'
        else:
            assignment_status = 'Active'
            status_class = 'primary'
        
        return render_template('teachers/teacher_view_group_assignment.html',
                             group_assignment=group_assignment,
                             submissions=submissions,
                             groups=groups,
                             extensions=extensions,
                             group_grades=all_group_grades,  # Pass all grades (including voided) for void check
                             graded_count=graded_count,
                             total_students=total_students,
                             group_submission_count=group_submission_count,
                             submission_count=submission_count,
                             late_submissions=late_submissions,
                             on_time_submissions=on_time_submissions,
                             submission_rate=submission_rate,
                             time_info=time_info,
                             assignment_status=assignment_status,
                             status_class=status_class,
                             admin_view=False)
    except Exception as e:
        print(f"Error viewing group assignment: {e}")
        flash('Error accessing group assignment details.', 'error')
        try:
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        except:
            return redirect(url_for('teacher.dashboard.teacher_dashboard'))


# --- Student assistant proposals: teacher / school admin must approve before students see assignments ---

@bp.route('/class/<int:class_id>/assistant-assignments/pending')
@login_required
@teacher_required
def pending_assistant_assignments(class_id):
    """Review assignments created by a student assistant (awaiting approval)."""
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_PENDING

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        flash('You are not authorized to access this class.', 'danger')
        return redirect(url_for('teacher.dashboard.my_classes'))

    pending_individual = Assignment.query.filter(
        Assignment.class_id == class_id,
        Assignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
    ).order_by(Assignment.created_at.desc()).all()

    pending_group = GroupAssignment.query.filter(
        GroupAssignment.class_id == class_id,
        GroupAssignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
    ).order_by(GroupAssignment.created_at.desc()).all()

    return render_template(
        'teachers/teacher_pending_assistant_assignments.html',
        class_obj=class_obj,
        pending_individual=pending_individual,
        pending_group=pending_group,
    )


@bp.route('/class/<int:class_id>/assistant-assignments/<int:assignment_id>/approve', methods=['POST'])
@login_required
@teacher_required
def approve_assistant_assignment(class_id, assignment_id):
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_APPROVED, ASSISTANT_APPROVAL_PENDING

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        flash('You are not authorized.', 'danger')
        return redirect(url_for('teacher.dashboard.my_classes'))

    a = Assignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()
    if a.assistant_approval_status != ASSISTANT_APPROVAL_PENDING:
        flash('This assignment is not pending approval.', 'warning')
        return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))

    publish_status = request.form.get('publish_status', 'Active')
    if publish_status not in ('Active', 'Inactive', 'Upcoming'):
        publish_status = 'Active'

    a.assistant_approval_status = ASSISTANT_APPROVAL_APPROVED
    a.assistant_approval_reviewed_by_user_id = current_user.id
    a.assistant_approval_reviewed_at = datetime.utcnow()
    a.assistant_approval_review_notes = None
    a.status = publish_status
    db.session.commit()
    flash('Assignment approved. Students in the class can now see it (per the status you chose).', 'success')
    return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))


@bp.route('/class/<int:class_id>/assistant-assignments/<int:assignment_id>/reject', methods=['POST'])
@login_required
@teacher_required
def reject_assistant_assignment(class_id, assignment_id):
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_REJECTED, ASSISTANT_APPROVAL_PENDING

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        flash('You are not authorized.', 'danger')
        return redirect(url_for('teacher.dashboard.my_classes'))

    a = Assignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()
    if a.assistant_approval_status != ASSISTANT_APPROVAL_PENDING:
        flash('This assignment is not pending approval.', 'warning')
        return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))

    notes = request.form.get('review_notes', '').strip()
    a.assistant_approval_status = ASSISTANT_APPROVAL_REJECTED
    a.assistant_approval_reviewed_by_user_id = current_user.id
    a.assistant_approval_reviewed_at = datetime.utcnow()
    a.assistant_approval_review_notes = notes or None
    db.session.commit()
    flash('Proposal rejected. The student assistant was notified via the review notes (shown on their hub).', 'info')
    return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))


@bp.route('/class/<int:class_id>/assistant-group-assignments/<int:group_assignment_id>/approve', methods=['POST'])
@login_required
@teacher_required
def approve_assistant_group_assignment(class_id, group_assignment_id):
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_APPROVED, ASSISTANT_APPROVAL_PENDING

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        flash('You are not authorized.', 'danger')
        return redirect(url_for('teacher.dashboard.my_classes'))

    ga = GroupAssignment.query.filter_by(id=group_assignment_id, class_id=class_id).first_or_404()
    if ga.assistant_approval_status != ASSISTANT_APPROVAL_PENDING:
        flash('This assignment is not pending approval.', 'warning')
        return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))

    publish_status = request.form.get('publish_status', 'Active')
    if publish_status not in ('Active', 'Inactive', 'Upcoming'):
        publish_status = 'Active'

    ga.assistant_approval_status = ASSISTANT_APPROVAL_APPROVED
    ga.assistant_approval_reviewed_by_user_id = current_user.id
    ga.assistant_approval_reviewed_at = datetime.utcnow()
    ga.assistant_approval_review_notes = None
    ga.status = publish_status
    db.session.commit()
    flash('Group assignment approved.', 'success')
    return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))


@bp.route('/class/<int:class_id>/assistant-group-assignments/<int:group_assignment_id>/reject', methods=['POST'])
@login_required
@teacher_required
def reject_assistant_group_assignment(class_id, group_assignment_id):
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_REJECTED, ASSISTANT_APPROVAL_PENDING

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        flash('You are not authorized.', 'danger')
        return redirect(url_for('teacher.dashboard.my_classes'))

    ga = GroupAssignment.query.filter_by(id=group_assignment_id, class_id=class_id).first_or_404()
    if ga.assistant_approval_status != ASSISTANT_APPROVAL_PENDING:
        flash('This assignment is not pending approval.', 'warning')
        return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))

    notes = request.form.get('review_notes', '').strip()
    ga.assistant_approval_status = ASSISTANT_APPROVAL_REJECTED
    ga.assistant_approval_reviewed_by_user_id = current_user.id
    ga.assistant_approval_reviewed_at = datetime.utcnow()
    ga.assistant_approval_review_notes = notes or None
    db.session.commit()
    flash('Group assignment proposal rejected.', 'info')
    return redirect(url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id))