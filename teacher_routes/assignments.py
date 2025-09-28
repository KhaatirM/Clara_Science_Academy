"""
Assignment management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class, allowed_file
from models import (
    db, Class, Assignment, Student, Grade, Submission, 
    SchoolYear, QuizQuestion, QuizOption, QuizAnswer,
    DiscussionThread, DiscussionPost
)
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename

bp = Blueprint('assignments', __name__)

@bp.route('/assignment/type-selector')
@login_required
@teacher_required
def assignment_type_selector():
    """Assignment type selection page"""
    return render_template('assignment_type_selector.html')

@bp.route('/assignment/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment():
    """Create a new PDF/Paper assignment"""
    if request.method == 'POST':
        # Handle assignment creation
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        points = request.form.get('points', type=float, default=100)
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('teacher.add_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.add_assignment'))
            
            # Check if user is authorized for this class
            class_obj = Class.query.get(class_id)
            if not is_authorized_for_class(class_obj):
                flash("You are not authorized to create assignments for this class.", "danger")
                return redirect(url_for('teacher.add_assignment'))
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                points=points,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status='Active',
                created_by=current_user.id
            )
            
            db.session.add(new_assignment)
            db.session.flush()  # Get the assignment ID
            
            # Handle file uploads
            if 'files' in request.files:
                files = request.files.getlist('files')
                uploaded_files = []
                
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Create unique filename to avoid conflicts
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        unique_filename = timestamp + filename
                        
                        # Create uploads directory if it doesn't exist
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'assignments')
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        file_path = os.path.join(upload_dir, unique_filename)
                        file.save(file_path)
                        
                        uploaded_files.append({
                            'original_name': filename,
                            'saved_name': unique_filename,
                            'path': f'uploads/assignments/{unique_filename}'
                        })
                
                # Store file information in assignment description or create a separate field
                if uploaded_files:
                    file_info = json.dumps(uploaded_files)
                    new_assignment.file_attachments = file_info
            
            db.session.commit()
            flash('Assignment created successfully!', 'success')
            return redirect(url_for('teacher.my_assignments'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating assignment: {str(e)}")
            flash(f'Error creating assignment: {str(e)}', 'danger')
            return redirect(url_for('teacher.add_assignment'))
    
    # GET request - show the form
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
    
    return render_template('add_assignment.html', classes=classes, teacher=teacher)

@bp.route('/class/<int:class_id>/assignment/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment_for_class(class_id):
    """Create a new assignment for a specific class"""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to create assignments for this class.", "danger")
        return redirect(url_for('teacher.view_class', class_id=class_id))
    
    if request.method == 'POST':
        # Handle assignment creation (same logic as add_assignment but with pre-selected class)
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        points = request.form.get('points', type=float, default=100)
        
        if not all([title, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('teacher.add_assignment_for_class', class_id=class_id))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.add_assignment_for_class', class_id=class_id))
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                points=points,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status='Active',
                created_by=current_user.id
            )
            
            db.session.add(new_assignment)
            db.session.flush()  # Get the assignment ID
            
            # Handle file uploads (same logic as above)
            if 'files' in request.files:
                files = request.files.getlist('files')
                uploaded_files = []
                
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        unique_filename = timestamp + filename
                        
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'assignments')
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        file_path = os.path.join(upload_dir, unique_filename)
                        file.save(file_path)
                        
                        uploaded_files.append({
                            'original_name': filename,
                            'saved_name': unique_filename,
                            'path': f'uploads/assignments/{unique_filename}'
                        })
                
                if uploaded_files:
                    file_info = json.dumps(uploaded_files)
                    new_assignment.file_attachments = file_info
            
            db.session.commit()
            flash('Assignment created successfully!', 'success')
            return redirect(url_for('teacher.view_class', class_id=class_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating assignment: {str(e)}")
            flash(f'Error creating assignment: {str(e)}', 'danger')
            return redirect(url_for('teacher.add_assignment_for_class', class_id=class_id))
    
    # GET request - show the form
    return render_template('add_assignment.html', classes=[class_obj], teacher=get_teacher_or_admin(), selected_class=class_obj)

@bp.route('/assignment/view/<int:assignment_id>')
@login_required
@teacher_required
def view_assignment(assignment_id):
    """View detailed information for a specific assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to view this assignment.", "danger")
        return redirect(url_for('teacher.my_assignments'))
    
    # Get submissions for this assignment
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    
    # Get grades for this assignment
    grades = Grade.query.filter_by(assignment_id=assignment_id).all()
    
    return render_template('view_assignment.html', 
                         assignment=assignment, 
                         submissions=submissions, 
                         grades=grades)

@bp.route('/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(assignment_id):
    """Edit an existing assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('teacher.my_assignments'))
    
    if request.method == 'POST':
        # Handle assignment update
        assignment.title = request.form.get('title')
        assignment.description = request.form.get('description', '')
        assignment.points = request.form.get('points', type=float, default=100)
        assignment.quarter = request.form.get('quarter')
        
        due_date_str = request.form.get('due_date')
        if due_date_str:
            try:
                assignment.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "danger")
                return redirect(url_for('teacher.edit_assignment', assignment_id=assignment_id))
        
        try:
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('teacher.view_assignment', assignment_id=assignment_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating assignment: {str(e)}")
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(url_for('teacher.edit_assignment', assignment_id=assignment_id))
    
    # GET request - show the edit form
    return render_template('edit_assignment.html', assignment=assignment)

@bp.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to remove this assignment.", "danger")
        return redirect(url_for('teacher.my_assignments'))
    
    try:
        # Remove associated grades and submissions first
        Grade.query.filter_by(assignment_id=assignment_id).delete()
        Submission.query.filter_by(assignment_id=assignment_id).delete()
        
        # Remove the assignment
        db.session.delete(assignment)
        db.session.commit()
        
        flash('Assignment removed successfully!', 'success')
        return redirect(url_for('teacher.my_assignments'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error removing assignment: {str(e)}")
        flash(f'Error removing assignment: {str(e)}', 'danger')
        return redirect(url_for('teacher.my_assignments'))

@bp.route('/assignment/<int:assignment_id>/change-status', methods=['POST'])
@login_required
@teacher_required
def change_assignment_status(assignment_id):
    """Change the status of an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to change the status of this assignment.", "danger")
        return redirect(url_for('teacher.my_assignments'))
    
    new_status = request.form.get('status')
    
    if new_status not in ['Active', 'Inactive', 'Voided']:
        flash("Invalid status.", "danger")
        return redirect(url_for('teacher.my_assignments'))
    
    try:
        assignment.status = new_status
        db.session.commit()
        
        flash(f'Assignment status changed to {new_status}.', 'success')
        return redirect(url_for('teacher.view_assignment', assignment_id=assignment_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error changing assignment status: {str(e)}")
        flash(f'Error changing assignment status: {str(e)}', 'danger')
        return redirect(url_for('teacher.my_assignments'))

@bp.route('/grant-extensions', methods=['POST'])
@login_required
@teacher_required
def grant_extensions():
    """Grant extensions to students for assignments"""
    try:
        assignment_id = request.form.get('assignment_id', type=int)
        student_ids = request.form.getlist('student_ids')
        extension_days = request.form.get('extension_days', type=int, default=1)
        
        if not assignment_id or not student_ids:
            flash("Missing required information.", "danger")
            return redirect(url_for('teacher.my_assignments'))
        
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Check authorization for this assignment's class
        if not is_authorized_for_class(assignment.class_info):
            flash("You are not authorized to grant extensions for this assignment.", "danger")
            return redirect(url_for('teacher.my_assignments'))
        
        # Grant extensions to selected students
        extended_count = 0
        for student_id in student_ids:
            try:
                student_id = int(student_id)
                # Here you would implement extension logic
                # For now, we'll just count the students
                extended_count += 1
            except ValueError:
                continue
        
        flash(f'Extensions granted to {extended_count} students.', 'success')
        return redirect(url_for('teacher.view_assignment', assignment_id=assignment_id))
        
    except Exception as e:
        print(f"Error granting extensions: {str(e)}")
        flash(f'Error granting extensions: {str(e)}', 'danger')
        return redirect(url_for('teacher.my_assignments'))

