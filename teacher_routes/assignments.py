"""
Assignment management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class, get_current_quarter
from models import (
    db, Class, Assignment, SchoolYear, Enrollment, TeacherStaff, AssignmentExtension,
    Grade,
    class_additional_teachers, class_substitute_teachers
)
from sqlalchemy import or_
from datetime import datetime
from utils.quarter_grade_calculator import update_quarter_grade
from werkzeug.utils import secure_filename
import os

bp = Blueprint('assignments', __name__)

def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/assignment/type-selector')
@login_required
@teacher_required
def assignment_type_selector():
    """Assignment type selection page"""
    return render_template('shared/assignment_type_selector.html')

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
            
            if not all([title, due_date_str, quarter]):
                flash("Title, Due Date, and Quarter are required.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
            
            if total_points is None or total_points <= 0:
                total_points = 100.0
            
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
            
            teacher = get_teacher_or_admin()
            teacher_id = teacher.id if teacher else None
            
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status=status,
                assignment_context=assignment_context,
                total_points=total_points,
                created_by=teacher_id
            )
            
            db.session.add(new_assignment)
            db.session.flush()
            
            # NOTE: We do NOT automatically create Grade records for enrolled students.
            # Grades are only created when a teacher explicitly enters scores via the grading interface.
            
            if 'assignment_file' in request.files:
                file = request.files['assignment_file']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    unique_filename = timestamp + filename
                    
                    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, unique_filename)
                    file.save(filepath)
                    
                    new_assignment.attachment_filename = unique_filename
                    new_assignment.attachment_original_filename = filename
                    new_assignment.attachment_file_path = filepath
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
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    teacher = get_teacher_or_admin()
    
    return render_template('shared/add_assignment.html', 
                         class_obj=class_obj,
                         classes=[class_obj],
                         school_years=school_years,
                         current_quarter=current_quarter,
                         context=context,
                         teacher=teacher)

@bp.route('/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(assignment_id):
    """Edit an existing assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
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
            
            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.quarter = quarter
            assignment.status = status
            assignment.assignment_context = assignment_context
            assignment.total_points = total_points
            
            if 'assignment_file' in request.files:
                file = request.files['assignment_file']
                if file and file.filename and allowed_file(file.filename):
                    if assignment.attachment_file_path and os.path.exists(assignment.attachment_file_path):
                        try:
                            os.remove(assignment.attachment_file_path)
                        except OSError:
                            pass
                    
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    unique_filename = timestamp + filename
                    
                    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, unique_filename)
                    file.save(filepath)
                    
                    assignment.attachment_filename = unique_filename
                    assignment.attachment_original_filename = filename
                    assignment.attachment_file_path = filepath
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
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    teacher = get_teacher_or_admin()
    today = date.today()
    
    # Calculate statistics
    # Get total enrolled students
    total_students = Enrollment.query.filter_by(
        class_id=class_obj.id,
        is_active=True
    ).count()
    
    # Get submission count
    submissions_count = Submission.query.filter_by(
        assignment_id=assignment_id
    ).count()
    
    # Get graded count (grades that are not voided)
    graded_count = Grade.query.filter_by(
        assignment_id=assignment_id,
        is_voided=False
    ).count()
    
    # Get assignment points (use total_points if available, otherwise points)
    assignment_points = assignment.total_points if hasattr(assignment, 'total_points') and assignment.total_points else (assignment.points if assignment.points else 0)
    
    # Calculate average score if there are grades
    average_score = None
    if graded_count > 0:
        grades = Grade.query.filter_by(
            assignment_id=assignment_id,
            is_voided=False
        ).all()
        total_percentage = 0
        count = 0
        for grade in grades:
            try:
                if grade.grade_data:
                    import json
                    grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                    if isinstance(grade_data, dict) and 'score' in grade_data:
                        score = grade_data['score']
                        if isinstance(score, (int, float)):
                            total_percentage += score
                            count += 1
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        
        if count > 0:
            average_score = round(total_percentage / count, 1)
    
    # Calculate submission rate
    submission_rate = round((submissions_count / total_students * 100) if total_students > 0 else 0, 1)
    
    # Calculate grading completion rate
    grading_rate = round((graded_count / total_students * 100) if total_students > 0 else 0, 1)
    
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
                         grading_rate=grading_rate)


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

@bp.route('/assignment/<int:assignment_id>/change-status', methods=['POST'])
@login_required
@teacher_required
def change_assignment_status(assignment_id):
    """Change the status of an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to change the status of this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    new_status = request.form.get('status')
    if not new_status:
        flash("Status is required.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    # Validate status value
    valid_statuses = ['Active', 'Inactive', 'Voided', 'Overdue']
    if new_status not in valid_statuses:
        flash(f"Invalid status: {new_status}. Must be one of {', '.join(valid_statuses)}", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    try:
        assignment.status = new_status
        db.session.commit()
        flash(f'Assignment status changed to {new_status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing assignment status: {str(e)}")
        flash(f'Error changing assignment status: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.dashboard.my_assignments'))

@bp.route('/assignment/<int:assignment_id>/submissions')
@login_required
@teacher_required
def view_assignment_submissions(assignment_id):
    """View all submissions for an assignment"""
    from models import Submission, Enrollment, Student, Grade
    from datetime import datetime
    
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view submissions for this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    # Get all enrolled students
    enrollments = Enrollment.query.filter_by(
        class_id=class_obj.id,
        is_active=True
    ).all()
    
    student_ids = [e.student_id for e in enrollments if e.student_id]
    students = Student.query.filter(Student.id.in_(student_ids)).order_by(
        Student.last_name, Student.first_name
    ).all()
    
    # Get all submissions for this assignment
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    submissions_dict = {sub.student_id: sub for sub in submissions}
    
    # Get all grades for this assignment
    grades = Grade.query.filter_by(assignment_id=assignment_id).all()
    grades_dict = {g.student_id: g for g in grades}
    
    # Get extensions
    extensions = AssignmentExtension.query.filter_by(
        assignment_id=assignment_id,
        is_active=True
    ).all()
    extensions_dict = {ext.student_id: ext for ext in extensions}
    
    # Calculate statistics
    total_students = len(students)
    submitted_count = len(submissions)
    graded_count = len([g for g in grades if not g.is_voided])
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
        submission = submissions_dict.get(student.id)
        grade = grades_dict.get(student.id)
        
        # Determine submission status
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
        
        # Get grade info
        grade_info = None
        if grade and not grade.is_voided:
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
        
        student_data.append({
            'student': student,
            'submission': submission,
            'grade': grade_info,
            'status': status,
            'submission_type': submission_type,
            'extension': extensions_dict.get(student.id)
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
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
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
            return redirect(url_for('teacher.dashboard.my_assignments'))
        
        # Check authorization
        if not is_authorized_for_class(class_obj):
            error_msg = 'You are not authorized to remove this assignment.'
            current_app.logger.warning(f"Unauthorized attempt to remove assignment {assignment_id} by user {current_user.id}")
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 403
            flash(error_msg, "danger")
            return redirect(url_for('teacher.dashboard.my_assignments'))
        
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
        return redirect(url_for('teacher.dashboard.my_assignments'))
        
    except Exception as e:
        db.session.rollback()
        error_message = f'Error removing assignment: {str(e)}'
        error_traceback = traceback.format_exc()
        current_app.logger.error(f"Remove assignment exception: {error_message}\n{error_traceback}")
        
        # Return JSON for AJAX requests
        if is_ajax:
            return jsonify({'success': False, 'message': error_message}), 500
        
        flash(error_message, 'danger')
        return redirect(url_for('teacher.dashboard.my_assignments'))