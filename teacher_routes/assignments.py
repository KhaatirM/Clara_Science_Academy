"""
Assignment management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class, allowed_file, get_current_quarter
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
    return render_template('shared/assignment_type_selector.html')

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
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('teacher.assignments.add_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment'))
            
            # Check if user is authorized for this class
            class_obj = Class.query.get(class_id)
            if not is_authorized_for_class(class_obj):
                flash("You are not authorized to create assignments for this class.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment'))
            
            # Get assignment context from form or query parameter
            assignment_context = request.form.get('assignment_context', 'homework')
            
            # Get total points from form (default to 100 if not provided)
            total_points = request.form.get('total_points', type=float)
            if total_points is None or total_points <= 0:
                total_points = 100.0
            
            # Get advanced grading options
            allow_extra_credit = 'allow_extra_credit' in request.form
            max_extra_credit_points = request.form.get('max_extra_credit_points', type=float) or 0.0
            
            late_penalty_enabled = 'late_penalty_enabled' in request.form
            late_penalty_per_day = request.form.get('late_penalty_per_day', type=float) or 0.0
            late_penalty_max_days = request.form.get('late_penalty_max_days', type=int) or 0
            
            assignment_category = request.form.get('assignment_category', '').strip() or None
            category_weight = request.form.get('category_weight', type=float) or 0.0
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status='Active',
                assignment_context=assignment_context,
                total_points=total_points,
                allow_extra_credit=allow_extra_credit,
                max_extra_credit_points=max_extra_credit_points if allow_extra_credit else 0.0,
                late_penalty_enabled=late_penalty_enabled,
                late_penalty_per_day=late_penalty_per_day if late_penalty_enabled else 0.0,
                late_penalty_max_days=late_penalty_max_days if late_penalty_enabled else 0,
                assignment_category=assignment_category,
                category_weight=category_weight,
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
            return redirect(url_for('teacher.dashboard.my_assignments'))
            
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
    
    # Get current quarter for pre-selection
    current_quarter = get_current_quarter()
    return render_template('shared/add_assignment.html', classes=classes, teacher=teacher, current_quarter=current_quarter)

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
        
        if not all([title, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('teacher.assignments.add_assignment_for_class', class_id=class_id))
            
            # Get assignment context from form or query parameter
            assignment_context = request.form.get('assignment_context', 'homework')
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status='Active',
                assignment_context=assignment_context,
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
    current_quarter = get_current_quarter()
    return render_template('shared/add_assignment.html', classes=[class_obj], teacher=get_teacher_or_admin(), selected_class=class_obj, current_quarter=current_quarter)

@bp.route('/assignment/view/<int:assignment_id>')
@login_required
@teacher_required
def view_assignment(assignment_id):
    """View detailed information for a specific assignment"""
    from datetime import datetime
    
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Check if assignment has class_info relationship
        if not assignment.class_info:
            flash("Assignment class information not found.", "danger")
            return redirect(url_for('teacher.dashboard.my_assignments'))
        
        # Check authorization for this assignment's class
        if not is_authorized_for_class(assignment.class_info):
            flash("You are not authorized to view this assignment.", "danger")
            return redirect(url_for('teacher.dashboard.my_assignments'))
        
        # Get submissions for this assignment - safely handle missing columns
        try:
            submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
        except Exception as e:
            print(f"Error getting submissions: {e}")
            submissions = []
        
        # Get grades for this assignment
        try:
            grades = Grade.query.filter_by(assignment_id=assignment_id).all()
        except Exception as e:
            print(f"Error getting grades: {e}")
            grades = []
        
        # Get today's date for deadline calculations
        today = datetime.now()
        
        # Get class information safely
        class_info = assignment.class_info
        teacher = None
        if class_info:
            # Try to get teacher through relationship
            try:
                if hasattr(class_info, 'teacher') and class_info.teacher:
                    teacher = class_info.teacher
                elif class_info.teacher_id:
                    from models import TeacherStaff
                    teacher = TeacherStaff.query.get(class_info.teacher_id)
            except Exception as e:
                print(f"Error getting teacher: {e}")
                teacher = None
        
        # Get submission count
        submissions_count = len(submissions) if submissions else 0
        
        # Get assignment points safely
        assignment_points = 0
        if hasattr(assignment, 'total_points') and assignment.total_points:
            assignment_points = assignment.total_points
        elif hasattr(assignment, 'points') and assignment.points:
            assignment_points = assignment.points
        
        return render_template('shared/view_assignment.html', 
                             assignment=assignment, 
                             submissions=submissions, 
                             grades=grades,
                             class_info=class_info,
                             teacher=teacher,
                             submissions_count=submissions_count,
                             assignment_points=assignment_points,
                             today=today)
    except Exception as e:
        current_app.logger.error(f"Error in view_assignment route: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading assignment: {str(e)}', 'danger')
        return redirect(url_for('teacher.dashboard.my_assignments'))

@bp.route('/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(assignment_id):
    """Edit an existing assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if request.method == 'POST':
        # Handle assignment update
        assignment.title = request.form.get('title')
        assignment.description = request.form.get('description', '')
        assignment.quarter = request.form.get('quarter')
        
        due_date_str = request.form.get('due_date')
        if due_date_str:
            try:
                assignment.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "danger")
                return redirect(url_for('teacher.assignments.edit_assignment', assignment_id=assignment_id))
        
        try:
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating assignment: {str(e)}")
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(url_for('teacher.assignments.edit_assignment', assignment_id=assignment_id))
    
    # GET request - show the edit form
    return render_template('shared/edit_assignment.html', assignment=assignment)

@bp.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to remove this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    try:
        # Remove associated grades and submissions first
        Grade.query.filter_by(assignment_id=assignment_id).delete()
        Submission.query.filter_by(assignment_id=assignment_id).delete()
        
        # Remove the assignment
        db.session.delete(assignment)
        db.session.commit()
        
        flash('Assignment removed successfully!', 'success')
        return redirect(url_for('teacher.dashboard.my_assignments'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error removing assignment: {str(e)}")
        flash(f'Error removing assignment: {str(e)}', 'danger')
        return redirect(url_for('teacher.dashboard.my_assignments'))

@bp.route('/assignment/<int:assignment_id>/change-status', methods=['POST'])
@login_required
@teacher_required
def change_assignment_status(assignment_id):
    """Change the status of an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to change the status of this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    new_status = request.form.get('status')
    
    if new_status not in ['Active', 'Inactive', 'Voided']:
        flash("Invalid status.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    try:
        assignment.status = new_status
        db.session.commit()
        
        flash(f'Assignment status changed to {new_status}.', 'success')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error changing assignment status: {str(e)}")
        flash(f'Error changing assignment status: {str(e)}', 'danger')
        return redirect(url_for('teacher.dashboard.my_assignments'))

@bp.route('/assignment/<int:assignment_id>/void', methods=['POST'])
@login_required
@teacher_required
def void_assignment(assignment_id):
    """Void an assignment for all students or selected students"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to void this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    void_type = request.form.get('void_type')
    reason = request.form.get('reason', '').strip()
    
    try:
        if void_type == 'all':
            # Void for entire class
            assignment.status = 'Voided'
            db.session.commit()
            flash(f'Assignment "{assignment.title}" has been voided for the entire class.', 'success')
        else:
            # Void for selected students only
            student_ids = request.form.getlist('student_ids')
            
            if not student_ids:
                flash("Please select at least one student to void the assignment for.", "danger")
                return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
            
            # Create special grade records marking assignment as voided for these students
            for student_id in student_ids:
                # Check if grade already exists
                existing_grade = Grade.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=int(student_id)
                ).first()
                
                # Create void grade data
                void_grade_data = {
                    'score': 0,
                    'max_score': 0,
                    'percentage': 0,
                    'feedback': reason or 'Assignment voided by teacher',
                    'is_voided': True,
                    'voided_at': datetime.now().isoformat()
                }
                
                if existing_grade:
                    # Update existing grade to voided
                    existing_grade.grade_data = json.dumps(void_grade_data)
                    existing_grade.graded_at = datetime.now()
                else:
                    # Create new voided grade
                    new_grade = Grade(
                        assignment_id=assignment_id,
                        student_id=int(student_id),
                        grade_data=json.dumps(void_grade_data),
                        graded_at=datetime.now()
                    )
                    db.session.add(new_grade)
            
            db.session.commit()
            flash(f'Assignment voided for {len(student_ids)} student(s). They will see 0/0 (no GPA impact).', 'success')
        
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error voiding assignment: {str(e)}")
        flash(f'Error voiding assignment: {str(e)}', 'danger')
        return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))

@bp.route('/grant-extensions', methods=['POST'])
@login_required
@teacher_required
def grant_extensions():
    """Grant extensions to students for assignments"""
    try:
        from models import AssignmentExtension, Student
        from datetime import datetime
        from flask import jsonify
        
        assignment_id = request.form.get('assignment_id', type=int)
        student_ids = request.form.getlist('student_ids')
        extended_due_date_str = request.form.get('extended_due_date')
        reason = request.form.get('reason', '')
        
        if not assignment_id or not student_ids or not extended_due_date_str:
            return jsonify({'success': False, 'error': 'Missing required information'}), 400
        
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Check authorization for this assignment's class
        if not is_authorized_for_class(assignment.class_info):
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        
        # Parse the extended due date
        try:
            extended_due_date = datetime.strptime(extended_due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        # Get teacher ID
        teacher = get_teacher_or_admin()
        if not teacher:
            return jsonify({'success': False, 'error': 'Teacher not found'}), 400
        
        # Grant extensions to selected students
        extended_count = 0
        for student_id_str in student_ids:
            try:
                student_id = int(student_id_str)
                
                # Check if student exists
                student = Student.query.get(student_id)
                if not student:
                    continue
                
                # Check if extension already exists for this student and assignment
                existing_extension = AssignmentExtension.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    is_active=True
                ).first()
                
                if existing_extension:
                    # Update existing extension
                    existing_extension.extended_due_date = extended_due_date
                    existing_extension.reason = reason
                    existing_extension.granted_at = datetime.utcnow()
                    existing_extension.granted_by = teacher.id
                else:
                    # Create new extension
                    new_extension = AssignmentExtension(
                        assignment_id=assignment_id,
                        student_id=student_id,
                        extended_due_date=extended_due_date,
                        reason=reason,
                        granted_by=teacher.id,
                        is_active=True
                    )
                    db.session.add(new_extension)
                
                extended_count += 1
            except ValueError:
                continue
        
        db.session.commit()
        return jsonify({'success': True, 'granted_count': extended_count})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error granting extensions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

