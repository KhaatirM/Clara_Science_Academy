"""
Assignment management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class, get_current_quarter
from models import (
    db, Class, Assignment, SchoolYear, Enrollment, TeacherStaff
)
from datetime import datetime
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
    """Add a new assignment - class selection page"""
    context = request.args.get('context', 'homework')
    
    if request.method == 'POST':
        class_id = request.form.get('class_id', type=int)
        if class_id:
            return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id, context=context))
        else:
            flash("Please select a class.", "danger")
    
    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.all()
    elif teacher is not None:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        classes = []
    
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
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    if not class_obj:
        flash("Assignment class information not found.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    teacher = get_teacher_or_admin()
    
    return render_template('shared/view_assignment.html', 
                         assignment=assignment,
                         class_info=class_obj,
                         teacher=teacher)

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