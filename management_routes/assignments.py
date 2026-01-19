"""
Assignments routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Assignment, Grade, Submission, Student, Class, Enrollment, AssignmentExtension,
    AssignmentRedo, AssignmentReopening, QuizQuestion, QuizOption, QuizAnswer, DiscussionThread, DiscussionPost,
    GroupAssignment, TeacherStaff, SchoolYear, ExtensionRequest
)
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta, timezone
import os
import json
from .utils import allowed_file, update_assignment_statuses, get_current_quarter

bp = Blueprint('assignments', __name__)


# ============================================================
# Route: /assignment/type-selector
# Function: assignment_type_selector
# ============================================================

@bp.route('/assignment/type-selector')
@login_required
@management_required
def assignment_type_selector():
    """Assignment type selection page for management"""
    return render_template('shared/assignment_type_selector.html')



# ============================================================
# Route: /group-assignment/type-selector
# Function: group_assignment_type_selector
# ============================================================

@bp.route('/group-assignment/type-selector')
@login_required
@management_required
def group_assignment_type_selector():
    """General group assignment type selector for management"""
    classes = Class.query.all()
    return render_template('management/group_assignment_class_selector.html', classes=classes)



# ============================================================
# Route: /assignment/create/quiz', methods=['GET', 'POST']
# Function: create_quiz_assignment
# ============================================================

@bp.route('/assignment/create/quiz', methods=['GET', 'POST'])
@login_required
@management_required
def create_quiz_assignment():
    """Create a quiz assignment - management version"""
    if request.method == 'POST':
        # Handle quiz assignment creation
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('management.create_quiz_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Parse open_date and close_date if provided
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
            
            # Calculate status based on dates
            from teacher_routes.assignment_utils import calculate_assignment_status
            temp_assignment = type('obj', (object,), {
                'status': 'Active',
                'open_date': open_date,
                'close_date': close_date,
                'due_date': due_date
            })
            calculated_status = calculate_assignment_status(temp_assignment)
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('management.create_quiz_assignment'))
            
            # Get save and continue settings
            allow_save_and_continue = request.form.get('allow_save_and_continue') == 'on'
            max_save_attempts = int(request.form.get('max_save_attempts', 10))
            save_timeout_minutes = int(request.form.get('save_timeout_minutes', 30))
            
            # Get quiz time limit and max attempts
            time_limit_str = request.form.get('time_limit', '').strip()
            time_limit_minutes = int(time_limit_str) if time_limit_str else None
            max_attempts = int(request.form.get('attempts', 1))
            
            # Get quiz display and behavior settings
            shuffle_questions = request.form.get('shuffle_questions') == 'on'
            show_correct_answers = request.form.get('show_correct_answers') == 'on'
            
            # Get Google Forms link settings
            link_google_form = request.form.get('link_google_form') == 'on'
            google_form_url = request.form.get('google_form_url', '').strip()
            google_form_id = None
            
            if link_google_form and google_form_url:
                # Extract form ID from Google Forms URL
                # URL format: https://docs.google.com/forms/d/e/FORM_ID/viewform
                import re
                match = re.search(r'/forms/d/e/([A-Za-z0-9_-]+)/', google_form_url)
                if match:
                    google_form_id = match.group(1)
                else:
                    flash('Invalid Google Forms URL format. Please check the URL.', 'warning')
            
            # Get assignment context from form or query parameter
            assignment_context = request.form.get('assignment_context', 'homework')
            
            # Create the assignment (status already calculated above)
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                open_date=open_date,
                close_date=close_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                status=calculated_status,
                assignment_type='quiz',
                allow_save_and_continue=allow_save_and_continue,
                max_save_attempts=max_save_attempts,
                save_timeout_minutes=save_timeout_minutes,
                time_limit_minutes=time_limit_minutes,
                max_attempts=max_attempts,
                shuffle_questions=shuffle_questions,
                show_correct_answers=show_correct_answers,
                google_form_id=google_form_id,
                google_form_url=google_form_url if link_google_form else None,
                google_form_linked=link_google_form,
                assignment_context=assignment_context,
                created_by=current_user.id
            )
            
            db.session.add(new_assignment)
            db.session.flush()  # Get the assignment ID
            
            # Save quiz questions and calculate total points
            question_count = 0
            total_points = 0.0
            
            # Process questions - collect all question IDs first
            question_ids = set()
            for key in request.form.keys():
                if key.startswith('question_text_') and not key.endswith('[]'):
                    # Extract question ID (e.g., "question_text_1" -> "1")
                    question_id = key.split('_')[-1]
                    question_ids.add(question_id)
            
            for question_id in sorted(question_ids, key=lambda x: int(x) if x.isdigit() else 999):
                question_text = request.form.get(f'question_text_{question_id}', '').strip()
                if not question_text:
                    continue
                    
                question_type = request.form.get(f'question_type_{question_id}', 'multiple_choice')
                points = float(request.form.get(f'question_points_{question_id}', 1.0))
                total_points += points
                
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
                if question_type == 'multiple_choice':
                    option_count = 0
                    correct_answer = request.form.get(f'correct_answer_{question_id}', '')
                    
                    # Handle array format for options (option_text_1[])
                    option_values = request.form.getlist(f'option_text_{question_id}[]')
                    
                    for option_text in option_values:
                        option_text = option_text.strip()
                        if not option_text:
                            continue
                            
                        is_correct = str(option_count) == correct_answer
                        
                        option = QuizOption(
                            question_id=question.id,
                            option_text=option_text,
                            is_correct=is_correct,
                            order=option_count
                        )
                        db.session.add(option)
                        option_count += 1
                elif question_type == 'true_false':
                    correct_answer = request.form.get(f'correct_answer_{question_id}', '')
                    
                    # Create True option
                    true_option = QuizOption(
                        question_id=question.id,
                        option_text='True',
                        is_correct=(correct_answer == 'true'),
                        order=0
                    )
                    db.session.add(true_option)
                    
                    # Create False option
                    false_option = QuizOption(
                        question_id=question.id,
                        option_text='False',
                        is_correct=(correct_answer == 'false'),
                        order=1
                    )
                    db.session.add(false_option)
                
                question_count += 1
            
            # Update assignment total_points
            new_assignment.total_points = total_points if total_points > 0 else 100.0
            db.session.commit()
            flash('Quiz assignment created successfully!', 'success')
            return redirect(url_for('management.assignments_and_grades'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quiz assignment: {str(e)}', 'danger')
    
    # GET request - show form
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    return render_template('shared/create_quiz_assignment.html', classes=classes, current_quarter=current_quarter)



# ============================================================
# Route: /assignment/create/discussion', methods=['GET', 'POST']
# Function: create_discussion_assignment
# ============================================================

@bp.route('/assignment/create/discussion', methods=['GET', 'POST'])
@login_required
@management_required
def create_discussion_assignment():
    """Create a discussion assignment - management version"""
    from teacher_routes.assignment_utils import calculate_assignment_status
    
    # Get classes for dropdown
    if current_user.role in ['Director', 'School Administrator']:
        classes = Class.query.filter_by(is_active=True).order_by(Class.name).all()
    else:
        # For teachers, get their classes
        if current_user.teacher_staff_id:
            teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first()
        else:
            from models import User
            teacher = TeacherStaff.query.join(User).filter(User.id == current_user.id).first()
        if teacher:
            classes = Class.query.filter_by(teacher_id=teacher.id, is_active=True).order_by(Class.name).all()
        else:
            classes = []
    
    if request.method == 'POST':
        # Handle discussion assignment creation
        title = request.form.get('title', '').strip()
        class_id = request.form.get('class_id', type=int)
        discussion_prompt = request.form.get('discussion_prompt', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        quarter = request.form.get('quarter', '').strip()
        total_points = request.form.get('total_points', type=float) or 100.0
        assignment_context = request.form.get('assignment_context', 'homework')
        
        # Participation requirements
        min_initial_posts = request.form.get('min_initial_posts', type=int) or 1
        min_replies = request.form.get('min_replies', type=int) or 2
        require_peer_response = request.form.get('require_peer_response') == 'on'
        allow_student_threads = request.form.get('allow_student_threads') == 'on'
        
        # Rubric (optional)
        use_rubric = request.form.get('use_rubric') == 'on'
        rubric_criteria = request.form.get('rubric_criteria', '').strip() if use_rubric else None
        
        # Open/close dates
        open_date_str = request.form.get('open_date', '').strip()
        close_date_str = request.form.get('close_date', '').strip()
        
        if not all([title, class_id, discussion_prompt, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return render_template('shared/create_discussion_assignment.html', classes=classes)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            due_date = due_date.replace(tzinfo=timezone.utc)  # Make due_date timezone-aware
            open_date = None
            close_date = None
            
            if open_date_str:
                try:
                    open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M')
                    open_date = open_date.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            
            if close_date_str:
                try:
                    close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M')
                    close_date = close_date.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            
            # If close_date not provided, default to due_date
            if not close_date:
                close_date = due_date
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return render_template('shared/create_discussion_assignment.html', classes=classes)
            
            # Build description with prompt and instructions
            full_description = f"**Discussion Prompt:**\n{discussion_prompt}\n\n"
            if description:
                full_description += f"**Instructions:**\n{description}\n\n"
            if rubric_criteria:
                full_description += f"**Rubric:**\n{rubric_criteria}\n\n"
            full_description += f"**Participation Requirements:**\n- Minimum {min_initial_posts} initial post(s)\n- Minimum {min_replies} reply/replies to classmates"
            
            # Calculate status based on dates
            temp_assignment = type('obj', (object,), {
                'status': 'Active',
                'open_date': open_date,
                'close_date': close_date,
                'due_date': due_date
            })
            calculated_status = calculate_assignment_status(temp_assignment)
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=full_description,
                due_date=due_date,
                open_date=open_date,
                close_date=close_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                status=calculated_status,
                assignment_type='discussion',
                assignment_context=assignment_context,
                total_points=total_points,
                created_by=current_user.id
            )
            
            db.session.add(new_assignment)
            db.session.flush()
            
            # Store discussion-specific settings in a JSON field (we'll add this to Assignment model if needed)
            # For now, we'll store it in description or create a separate table later
            
            db.session.commit()
            
            # TODO: Save discussion settings, rubric, and prompts
            # This would require additional models for discussion settings, rubric criteria, etc.
            
            flash('Discussion assignment created successfully!', 'success')
            return redirect(url_for('management.assignments_and_grades'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating discussion assignment: {str(e)}', 'danger')
    
    # GET request - show form
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    return render_template('shared/create_discussion_assignment.html', classes=classes, current_quarter=current_quarter)



# ============================================================
# Route: /extension-requests
# Function: view_extension_requests
# ============================================================

@bp.route('/extension-requests')
@login_required
@management_required
def view_extension_requests():
    """View all extension requests for assignments"""
    from datetime import datetime
    
    # Administrators see all extension requests
    extension_requests = ExtensionRequest.query.order_by(ExtensionRequest.requested_at.desc()).all()
    
    # Group requests by status
    pending_requests = [req for req in extension_requests if req.status == 'Pending']
    approved_requests = [req for req in extension_requests if req.status == 'Approved']
    rejected_requests = [req for req in extension_requests if req.status == 'Rejected']
    
    return render_template('teachers/extension_requests.html',
                         pending_requests=pending_requests,
                         approved_requests=approved_requests,
                         rejected_requests=rejected_requests,
                         total_count=len(extension_requests))

# ============================================================
# Route: /extension-request/<int:request_id>/review
# Function: review_extension_request
# ============================================================

@bp.route('/extension-request/<int:request_id>/review', methods=['POST'])
@login_required
@management_required
def review_extension_request(request_id):
    """Approve or reject an extension request"""
    from models import AssignmentExtension
    from datetime import datetime
    
    extension_request = ExtensionRequest.query.get_or_404(request_id)
    assignment = extension_request.assignment
    
    action = request.form.get('action')  # 'approve' or 'reject'
    review_notes = request.form.get('review_notes', '').strip()
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    try:
        # Get teacher_staff_id for administrators (use current user if available)
        teacher_staff_id = None
        if current_user.role in ['Director', 'School Administrator']:
            # Try to get teacher_staff_id from current_user
            if hasattr(current_user, 'teacher_staff_id') and current_user.teacher_staff_id:
                teacher_staff_id = current_user.teacher_staff_id
        
        if action == 'approve':
            # Update extension request status
            extension_request.status = 'Approved'
            extension_request.reviewed_at = datetime.utcnow()
            extension_request.reviewed_by = teacher_staff_id
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
                    granted_by=teacher_staff_id,
                    is_active=True
                )
                db.session.add(new_extension)
            
            message = f'Extension request approved. New due date: {extension_request.requested_due_date.strftime("%Y-%m-%d %I:%M %p")}'
        else:
            # Reject extension request
            extension_request.status = 'Rejected'
            extension_request.reviewed_at = datetime.utcnow()
            extension_request.reviewed_by = teacher_staff_id
            extension_request.review_notes = review_notes if review_notes else 'Extension request rejected'
            
            message = 'Extension request rejected'
        
        db.session.commit()
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reviewing extension request: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing request: {str(e)}'}), 500

# ============================================================
# Route: /assignments-and-grades
# Function: assignments_and_grades
# ============================================================

@bp.route('/assignments-and-grades')
@login_required
@management_required
def assignments_and_grades():
    """Combined assignments and grades view for School Administrators and Directors"""
    import json
    try:
        from datetime import datetime
        
        # Get all classes with safety checks
        all_classes = Class.query.all()
        # Filter out any invalid class objects
        all_classes = [c for c in all_classes if c and hasattr(c, 'id') and c.id is not None]
        
        # Get current user's role and permissions with safety checks
        user_role = getattr(current_user, 'role', None) or 'unknown'
        user_id = getattr(current_user, 'id', None)
        
        # Ensure user_id is valid
        if user_id is None:
            flash('Invalid user session. Please log in again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Determine which classes the user can access
        if user_role == 'Director':
            # Directors can see all classes
            accessible_classes = all_classes
        elif user_role == 'School Administrator':
            # School Administrators can see all classes for assignment management
            accessible_classes = all_classes
        else:
            # Fallback - should not happen due to @management_required decorator
            accessible_classes = []
        
        # Get filter and sort parameters with safe defaults
        class_filter = request.args.get('class_id', '') or ''
        sort_by = request.args.get('sort', 'due_date') or 'due_date'
        sort_order = request.args.get('order', 'desc') or 'desc'
        view_mode = request.args.get('view', 'assignments') or 'assignments'
        
        # Ensure all parameters are safe
        if not isinstance(class_filter, str):
            class_filter = ''
        if not isinstance(sort_by, str):
            sort_by = 'due_date'
        if not isinstance(sort_order, str):
            sort_order = 'desc'
        if not isinstance(view_mode, str):
            view_mode = 'assignments'
        
        # If no class is selected, show the class selection interface (like /management/assignments)
        if not class_filter or not class_filter.strip():
            # Get assignment counts for each class (regular + group assignments)
            class_assignments = {}
            for class_obj in accessible_classes:
                if class_obj and hasattr(class_obj, 'id') and class_obj.id is not None:
                    regular_count = Assignment.query.filter_by(class_id=class_obj.id).count()
                    try:
                        try:
                            group_count = GroupAssignment.query.filter_by(class_id=class_obj.id).count()
                        except Exception as e:
                            current_app.logger.error(f"Error counting group assignments: {str(e)}")
                            group_count = 0
                    except:
                        group_count = 0
                    class_assignments[class_obj.id] = regular_count + group_count
            
            # Calculate unique student count across all accessible classes
            unique_student_ids = set()
            for class_obj in accessible_classes:
                if class_obj and hasattr(class_obj, 'enrollments'):
                    for enrollment in class_obj.enrollments:
                        if enrollment.is_active and enrollment.student_id:
                            unique_student_ids.add(enrollment.student_id)
            unique_student_count = len(unique_student_ids)
            
            # Get pending extension request count
            pending_extension_count = ExtensionRequest.query.filter_by(status='Pending').count()
            
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
                                 user_role=user_role,
                                 show_class_selection=True,
                                 extension_request_count=pending_extension_count)
        
        # Get assignment counts and grade data for each class
        class_data = {}
        for class_obj in accessible_classes:
            if not class_obj or not hasattr(class_obj, 'id') or class_obj.id is None:
                continue  # Skip invalid class objects
            assignments = Assignment.query.filter_by(class_id=class_obj.id).all()
            assignment_count = len(assignments)
            
            # Get grade statistics
            grade_stats = {
                'total_assignments': assignment_count,
                'total_submissions': 0,
                'graded_assignments': 0,
                'average_score': 0
            }
            
            if view_mode == 'grades':
                total_score = 0
                graded_count = 0
                for assignment in assignments:
                    grades = Grade.query.filter_by(assignment_id=assignment.id).all()
                    grade_stats['total_submissions'] += len(grades)
                    if grades:
                        grade_stats['graded_assignments'] += 1
                        for grade in grades:
                            if grade.grade_data:
                                try:
                                    # Handle both dict and JSON string cases
                                    if isinstance(grade.grade_data, dict):
                                        grade_dict = grade.grade_data
                                    else:
                                        grade_dict = json.loads(grade.grade_data)
                                    
                                    if 'score' in grade_dict and grade_dict['score'] is not None:
                                        score_value = grade_dict['score']
                                        try:
                                            total_score += float(score_value)
                                            graded_count += 1
                                        except (ValueError, TypeError):
                                            continue
                                except (json.JSONDecodeError, TypeError):
                                    # Skip invalid grade data
                                    continue
                
                if graded_count > 0:
                    grade_stats['average_score'] = round(total_score / graded_count, 1)
            
            # Only add to class_data if class_obj.id is valid
            if class_obj.id is not None:
                class_data[class_obj.id] = {
                    'class': class_obj,
                    'assignment_count': assignment_count,
                    'grade_stats': grade_stats
                }
        
        # If a specific class is selected, get detailed assignment and grade data
        selected_class = None
        class_assignments = []
        assignment_grades = {}
        
        # Handle class filter with comprehensive safety checks
        if class_filter and isinstance(class_filter, str) and class_filter.strip():
            try:
                # Additional safety: check if the string contains only digits
                clean_filter = class_filter.strip()
                if clean_filter.isdigit():
                    selected_class_id = int(clean_filter)
                    selected_class = next((c for c in accessible_classes if hasattr(c, 'id') and c.id == selected_class_id), None)
                else:
                    selected_class = None
                
                if selected_class:
                    # Get regular assignments for the selected class
                    assignments_query = Assignment.query.filter_by(class_id=selected_class_id)
                
                    # Apply sorting for regular assignments
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
                    
                    # Get group assignments for the selected class
                    try:
                        try:
                            group_assignments_query = GroupAssignment.query.filter_by(class_id=selected_class_id)
                        except Exception as e:
                            current_app.logger.error(f"Error querying group assignments: {str(e)}")
                            group_assignments_query = GroupAssignment.query.filter_by(class_id=0)  # Empty query
                        
                        # Apply sorting for group assignments
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
                
                # Get grade data for each individual assignment
                for assignment in class_assignments:
                    grades = Grade.query.filter_by(assignment_id=assignment.id).all()
                    
                    # Process grade data safely
                    graded_grades = []
                    total_score = 0
                    for g in grades:
                        if g.grade_data is not None:
                            try:
                                # Handle both dict and JSON string cases
                                if isinstance(g.grade_data, dict):
                                    grade_dict = g.grade_data
                                else:
                                    grade_dict = json.loads(g.grade_data)
                                
                                if 'score' in grade_dict and grade_dict['score'] is not None:
                                    graded_grades.append(grade_dict)
                                    score_value = grade_dict['score']
                                    try:
                                        total_score += float(score_value)
                                    except (ValueError, TypeError):
                                        continue
                            except (json.JSONDecodeError, TypeError):
                                # Skip invalid grade data
                                continue
                    
                    # Check if quiz is auto-gradeable (all questions are multiple_choice or true_false)
                    is_autogradeable = False
                    if assignment.assignment_type == 'quiz':
                        from models import QuizQuestion
                        quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment.id).all()
                        if quiz_questions:
                            # Check if all questions are auto-gradeable
                            auto_gradeable_types = ['multiple_choice', 'true_false']
                            is_autogradeable = all(q.question_type in auto_gradeable_types for q in quiz_questions)
                    
                    assignment_grades[assignment.id] = {
                        'grades': grades,
                        'total_submissions': len(grades),
                        'graded_count': len(graded_grades),
                        'average_score': round(total_score / len(graded_grades), 1) if graded_grades else 0,
                        'type': 'individual',
                        'is_autogradeable': is_autogradeable
                    }
                
                # Get grade data for each group assignment
                for group_assignment in group_assignments:
                    # Get group grades for this assignment
                    from models import GroupGrade
                    group_grades = GroupGrade.query.filter_by(group_assignment_id=group_assignment.id).all()
                    
                    # Process group grade data safely
                    graded_group_grades = []
                    total_score = 0
                    for gg in group_grades:
                        if gg.grade_data is not None:
                            try:
                                # Handle both dict and JSON string cases
                                if isinstance(gg.grade_data, dict):
                                    grade_dict = gg.grade_data
                                else:
                                    grade_dict = json.loads(gg.grade_data)
                                
                                if 'score' in grade_dict and grade_dict['score'] is not None:
                                    graded_group_grades.append(grade_dict)
                                    score_value = grade_dict['score']
                                    try:
                                        total_score += float(score_value)
                                    except (ValueError, TypeError):
                                        continue
                            except (json.JSONDecodeError, TypeError):
                                # Skip invalid grade data
                                continue
                    
                    # Use a special key format for group assignments
                    assignment_grades[f'group_{group_assignment.id}'] = {
                        'grades': group_grades,
                        'total_submissions': len(group_grades),
                        'graded_count': len(graded_group_grades),
                        'average_score': round(total_score / len(graded_group_grades), 1) if graded_group_grades else 0,
                        'type': 'group',
                        'assignment': group_assignment  # Store the assignment object for template use
                    }
            except (ValueError, TypeError, AttributeError) as e:
                # Handle any conversion errors gracefully
                selected_class = None
                pass
    
        # Get group_assignments if they exist (for passing to template)
        try:
            if not 'group_assignments' in locals():
                group_assignments = []
        except:
            group_assignments = []
        
        from datetime import date
        # Get pending extension request count
        pending_extension_count = ExtensionRequest.query.filter_by(status='Pending').count()
        
        # Create combined assignments list for grades and table views
        class_assignments_data = list(class_assignments) if class_assignments else []
        
        # Get enrolled students and all assignments for any view when class is selected
        enrolled_students = []
        all_assignments = []
        table_student_grades = {}
        table_student_averages = {}
        
        if selected_class:
            try:
                from models import Enrollment
                enrollments = Enrollment.query.filter_by(class_id=selected_class.id, is_active=True).all()
                enrolled_students = [e.student for e in enrollments if e.student]
                # Combine regular and group assignments for table view
                all_assignments = list(class_assignments) + list(group_assignments) if group_assignments else list(class_assignments)
                
                # Calculate student grades for table view
                if view_mode == 'table':
                    # Get grades for enrolled students (individual assignments)
                    for student in enrolled_students:
                        table_student_grades[student.id] = {}
                        for assignment in class_assignments:
                            grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
                            if grade:
                                try:
                                    grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                                    points_earned = grade_data.get('score') or grade_data.get('points_earned')
                                    # Always use assignment's total_points as source of truth
                                    total_points = assignment.total_points if assignment.total_points else 100.0
                                    
                                    # Calculate percentage from points
                                    if points_earned is not None:
                                        try:
                                            points_float = float(points_earned)
                                            percentage = (points_float / total_points * 100) if total_points > 0 else 0
                                            # Store percentage for display
                                            score = round(percentage, 1)
                                        except (ValueError, TypeError):
                                            score = 'N/A'
                                    else:
                                        score = 'N/A'
                                    
                                    table_student_grades[student.id][assignment.id] = {
                                        'grade': score,
                                        'comments': grade_data.get('comments', ''),
                                        'graded_at': grade.graded_at,
                                        'type': 'individual',
                                        'is_voided': getattr(grade, 'is_voided', False)
                                    }
                                except (json.JSONDecodeError, TypeError):
                                    table_student_grades[student.id][assignment.id] = {
                                        'grade': 'N/A',
                                        'comments': 'Error parsing grade data',
                                        'graded_at': grade.graded_at,
                                        'type': 'individual',
                                        'is_voided': getattr(grade, 'is_voided', False)
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
                            if hasattr(group_assignment, 'selected_groups') and group_assignment.selected_groups:
                                try:
                                    selected_group_ids = json.loads(group_assignment.selected_groups) if isinstance(group_assignment.selected_groups, str) else group_assignment.selected_groups
                                except:
                                    selected_group_ids = []
                            else:
                                selected_group_ids = []
                            
                            # Find which group this student belongs to for this assignment
                            student_group = None
                            if selected_group_ids:
                                # Check if student is in any of the selected groups
                                for group_id in selected_group_ids:
                                    group_member = StudentGroupMember.query.filter_by(
                                        student_id=student.id,
                                        group_id=group_id
                                    ).first()
                                    if group_member:
                                        student_group = StudentGroup.query.get(group_id)
                                        break
                            else:
                                # Check all groups in the class
                                groups = StudentGroup.query.filter_by(class_id=selected_class.id).all()
                                for group in groups:
                                    group_member = StudentGroupMember.query.filter_by(
                                        student_id=student.id,
                                        group_id=group.id
                                    ).first()
                                    if group_member:
                                        student_group = group
                                        break
                            
                            if student_group:
                                group_grade = GroupGrade.query.filter_by(
                                    group_assignment_id=group_assignment.id,
                                    group_id=student_group.id
                                ).first()
                                
                                if group_grade:
                                    try:
                                        grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else group_grade.grade_data
                                        points_earned = grade_data.get('score') or grade_data.get('points_earned')
                                        # Always use group_assignment's total_points as source of truth
                                        total_points = group_assignment.total_points if group_assignment.total_points else 100.0
                                        
                                        # Calculate percentage from points
                                        if points_earned is not None:
                                            try:
                                                points_float = float(points_earned)
                                                percentage = (points_float / total_points * 100) if total_points > 0 else 0
                                                # Store percentage for display
                                                score = round(percentage, 1)
                                            except (ValueError, TypeError):
                                                score = 'N/A'
                                        else:
                                            score = 'N/A'
                                        
                                        table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                            'grade': score,
                                            'comments': grade_data.get('comments', ''),
                                            'graded_at': group_grade.graded_at,
                                            'type': 'group',
                                            'is_voided': getattr(group_grade, 'is_voided', False)
                                        }
                                    except (json.JSONDecodeError, TypeError):
                                        table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                            'grade': 'N/A',
                                            'comments': 'Error parsing grade data',
                                            'graded_at': group_grade.graded_at,
                                            'type': 'group',
                                            'is_voided': getattr(group_grade, 'is_voided', False)
                                        }
                                else:
                                    table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                        'grade': 'Not Graded',
                                        'comments': '',
                                        'graded_at': None,
                                        'is_voided': False,
                                        'type': 'group'
                                    }
                            else:
                                table_student_grades[student.id][f'group_{group_assignment.id}'] = {
                                    'grade': 'Not in Group',
                                    'comments': '',
                                    'graded_at': None,
                                    'is_voided': False,
                                    'type': 'group'
                                }
                    
                    # Calculate student averages
                    for student_id, grades in table_student_grades.items():
                        total_score = 0
                        count = 0
                        for assignment_id, grade_info in grades.items():
                            # Skip voided grades
                            if grade_info.get('is_voided', False):
                                continue
                            grade = grade_info.get('grade')
                            # Only process valid numeric grades
                            if grade and grade != 'Not Graded' and grade != 'N/A' and grade != 'Not in Group' and grade != 'Not Assigned' and grade != 'No Group' and grade is not None:
                                try:
                                    grade_num = float(grade)
                                    total_score += grade_num
                                    count += 1
                                except (ValueError, TypeError):
                                    pass
                        if count > 0:
                            table_student_averages[student_id] = round(total_score / count, 1)
                        else:
                            table_student_averages[student_id] = None
            except Exception as e:
                current_app.logger.error(f"Error loading enrolled students: {e}")
                import traceback
                current_app.logger.error(traceback.format_exc())
                enrolled_students = []
                all_assignments = []
                table_student_grades = {}
                table_student_averages = {}
        
        return render_template('management/assignments_and_grades.html',
                             accessible_classes=accessible_classes,
                             class_data=class_data,
                             selected_class=selected_class,
                             class_assignments=class_assignments,
                             class_assignments_data=class_assignments_data,
                             group_assignments=group_assignments,
                             assignment_grades=assignment_grades,
                             class_filter=class_filter,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             view_mode=view_mode,
                             user_role=user_role,
                             show_class_selection=False,
                             today=date.today(),
                             extension_request_count=pending_extension_count,
                             enrolled_students=enrolled_students,
                             all_assignments=all_assignments,
                             student_grades=table_student_grades,
                             student_averages=table_student_averages)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        current_app.logger.error(f"Error in assignments_and_grades: {e}")
        current_app.logger.error(f"Traceback: {error_trace}")
        print(f"Error in assignments_and_grades: {e}")
        print(f"Traceback: {error_trace}")
        flash('Error loading assignments and grades. Please try again.', 'error')
        return redirect(url_for('management.management_dashboard'))





# ============================================================
# Route: /assignments/legacy
# Function: assignments_legacy
# ============================================================

@bp.route('/assignments/legacy')
@login_required
@management_required
def assignments_legacy():
    """Management assignment view - similar to teacher assignments with filtering and sorting"""
    from datetime import datetime
    
    # Get all classes
    all_classes = Class.query.all()
    
    # Get current user's role and permissions
    user_role = current_user.role
    user_id = current_user.id
    
    # Determine which classes the user can access
    if user_role == 'Director':
        # Directors can see all classes
        accessible_classes = all_classes
        assignments_query = Assignment.query
    elif user_role == 'School Administrator':
        # School Administrators can see classes they teach + all assignments for viewing
        # First, find the TeacherStaff record for this user
        teacher_staff = None
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
        
        if teacher_staff:
            teacher_classes = Class.query.filter_by(teacher_id=teacher_staff.id).all()
            # If no classes assigned, assign them to the first available class for testing
            if not teacher_classes and all_classes:
                first_class = all_classes[0]
                first_class.teacher_id = teacher_staff.id
                db.session.commit()
                teacher_classes = [first_class]
        else:
            teacher_classes = []
        accessible_classes = teacher_classes
        
        # For assignments, they can see all assignments but only edit their own class assignments
        assignments_query = Assignment.query
    else:
        # Fallback - should not happen due to @management_required decorator
        accessible_classes = []
        assignments_query = Assignment.query.none()
    
    # Get filter parameters
    selected_class_id = request.args.get('class_id', '')
    selected_status = request.args.get('status', '')
    sort_by = request.args.get('sort', 'due_date')
    sort_order = request.args.get('order', 'desc')
    
    # Ensure selected_class_id is a string for template comparison
    selected_class_id = str(selected_class_id) if selected_class_id else ''
    
    # Build assignments query
    assignments_query = assignments_query.join(Class, Assignment.class_id == Class.id)
    
    # Apply filters
    if selected_class_id:
        assignments_query = assignments_query.filter(Assignment.class_id == selected_class_id)
    
    if selected_status:
        assignments_query = assignments_query.filter(Assignment.status == selected_status)
    
    # Apply sorting
    if sort_by == 'due_date':
        if sort_order == 'asc':
            assignments_query = assignments_query.order_by(Assignment.due_date.asc())
        else:
            assignments_query = assignments_query.order_by(Assignment.due_date.desc())
    elif sort_by == 'title':
        if sort_order == 'asc':
            assignments_query = assignments_query.order_by(Assignment.title.asc())
        else:
            assignments_query = assignments_query.order_by(Assignment.title.desc())
    elif sort_by == 'class':
        if sort_order == 'asc':
            assignments_query = assignments_query.order_by(Class.name.asc())
        else:
            assignments_query = assignments_query.order_by(Class.name.desc())
    
    # Get assignments
    assignments = assignments_query.all()
    
    # Get current date for status updates
    today = datetime.now().date()
    
    # Update assignment statuses (past due assignments become inactive)
    update_assignment_statuses()
    
    # Get teacher_staff_id for template use
    teacher_staff_id = None
    if user_role == 'School Administrator':
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
            if teacher_staff:
                teacher_staff_id = teacher_staff.id
    
    return render_template('shared/assignments_list.html',
                         assignments=assignments,
                         classes=all_classes,
                         accessible_classes=accessible_classes,
                         user_role=user_role,
                         teacher_staff_id=teacher_staff_id,
                         today=today,
                         selected_class_id=selected_class_id,
                         selected_status=selected_status,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         active_tab='assignments')



# ============================================================
# Route: /debug-grades/<int:class_id>
# Function: debug_grades
# ============================================================

@bp.route('/debug-grades/<int:class_id>')
@login_required
@management_required
def debug_grades(class_id):
    """Debug route to check grades data"""
    import json
    from models import GroupGrade
    
    # Get class info
    class_obj = Class.query.get_or_404(class_id)
    
    # Get students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    # Get group assignments
    try:
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
    except Exception as e:
        current_app.logger.error(f"Error loading group assignments: {str(e)}")
        group_assignments = []
    
    # Get all group grades for this class
    group_grades = GroupGrade.query.join(GroupAssignment).filter(
        GroupAssignment.class_id == class_id
    ).all()
    
    debug_info = {
        'class_id': class_id,
        'class_name': class_obj.name,
        'students': [],
        'group_assignments': [],
        'group_grades': []
    }
    
    # Student info
    for student in students:
        student_group = StudentGroupMember.query.join(StudentGroup).filter(
            StudentGroup.class_id == class_id,
            StudentGroupMember.student_id == student.id
        ).first()
        
        debug_info['students'].append({
            'id': student.id,
            'name': f"{student.first_name} {student.last_name}",
            'group_id': student_group.group.id if student_group and student_group.group else None,
            'group_name': student_group.group.name if student_group and student_group.group else None
        })
    
    # Group assignments info
    for assignment in group_assignments:
        debug_info['group_assignments'].append({
            'id': assignment.id,
            'title': assignment.title,
            'selected_group_ids': assignment.selected_group_ids,
            'parsed_group_ids': json.loads(assignment.selected_group_ids) if assignment.selected_group_ids else None
        })
    
    # Group grades info
    for grade in group_grades:
        try:
            grade_data = json.loads(grade.grade_data) if grade.grade_data else {}
        except:
            grade_data = {}
            
        debug_info['group_grades'].append({
            'id': grade.id,
            'student_id': grade.student_id,
            'group_assignment_id': grade.group_assignment_id,
            'group_id': grade.group_id,
            'grade_data': grade_data,
            'comments': grade.comments
        })
    
    return jsonify(debug_info)







# ============================================================
# Route: /add-assignment', methods=['GET', 'POST']
# Function: add_assignment
# ============================================================

@bp.route('/add-assignment', methods=['GET', 'POST'])
@login_required
@management_required
def add_assignment():
    """Add a new assignment"""
    if request.method == 'POST':
        # Debug logging
        print(f"DEBUG: POST request to add_assignment")
        print(f"DEBUG: Form data: {dict(request.form)}")
        
        title = request.form.get('title')
        description = request.form.get('description')
        class_id = request.form.get('class_id', type=int)
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
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
        
        print(f"DEBUG: Parsed - title={title}, class_id={class_id}, due_date={due_date_str}, quarter={quarter}, status={status}, assignment_context={assignment_context}, total_points={total_points}")
        
        if not all([title, class_id, due_date_str, quarter]):
            print(f"DEBUG: Validation failed - title={title!r}, class_id={class_id!r}, due_date_str={due_date_str!r}, quarter={quarter!r}")
            flash("Title, Class, Due Date, and Quarter are required.", "danger")
            return redirect(request.url)
        
        print(f"DEBUG: Validation passed, proceeding to create assignment")

        # Type assertion for due_date_str
        assert due_date_str is not None
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        
        # Parse open_date and close_date if provided
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
        
        # Calculate status based on dates if status not explicitly set to Voided
        from teacher_routes.assignment_utils import calculate_assignment_status
        if status != 'Voided':
            temp_assignment = type('obj', (object,), {
                'status': 'Active',
                'open_date': open_date,
                'close_date': close_date,
                'due_date': due_date
            })
            calculated_status = calculate_assignment_status(temp_assignment)
            status = calculated_status
        
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            flash("Cannot create assignment: No active school year.", "danger")
            return redirect(request.url)

        # Type assertion for quarter
        assert quarter is not None
        
        # Create assignment using attribute assignment
        new_assignment = Assignment()
        new_assignment.title = title
        new_assignment.description = description
        new_assignment.due_date = due_date
        new_assignment.open_date = open_date
        new_assignment.close_date = close_date
        new_assignment.class_id = class_id
        new_assignment.school_year_id = current_school_year.id
        new_assignment.quarter = str(quarter)
        new_assignment.status = status
        new_assignment.assignment_context = assignment_context
        new_assignment.assignment_type = 'pdf_paper'  # Set assignment type for PDF/Paper assignments
        new_assignment.total_points = total_points
        new_assignment.allow_extra_credit = allow_extra_credit
        new_assignment.max_extra_credit_points = max_extra_credit_points if allow_extra_credit else 0.0
        new_assignment.late_penalty_enabled = late_penalty_enabled
        new_assignment.late_penalty_per_day = late_penalty_per_day if late_penalty_enabled else 0.0
        new_assignment.late_penalty_max_days = late_penalty_max_days if late_penalty_enabled else 0
        new_assignment.assignment_category = assignment_category
        new_assignment.category_weight = category_weight
        new_assignment.created_by = current_user.id
        
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
        
        try:
            db.session.add(new_assignment)
            db.session.commit()
            print(f"DEBUG: Assignment created successfully with ID: {new_assignment.id}")
            print(f"DEBUG: Assignment details - title={new_assignment.title}, class_id={new_assignment.class_id}, quarter={new_assignment.quarter}")
            
            flash('Assignment created successfully.', 'success')
            return redirect(url_for('management.assignments_and_grades'))
        except Exception as e:
            print(f"ERROR: Failed to create assignment: {e}")
            db.session.rollback()
            flash(f'Error creating assignment: {str(e)}', 'danger')
            return redirect(request.url)

    # For GET request, get all classes for the dropdown and current quarter
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    # Get assignment context from query parameter (in-class or homework)
    context = request.args.get('context', 'homework')
    return render_template('shared/add_assignment.html', classes=classes, current_quarter=current_quarter, context=context)




# ============================================================
# Route: /grade/assignment/<int:assignment_id>', methods=['GET', 'POST']
# Function: grade_assignment
# ============================================================

@bp.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@management_required
def grade_assignment(assignment_id):
    """Grade an assignment - Directors and School Administrators can grade assignments for classes they teach"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Check if assignment has class_info
        if not assignment.class_info:
            flash("This assignment is not associated with a class.", "danger")
            return redirect(url_for('management.assignments_and_grades'))
        
        class_obj = assignment.class_info
        
        # Authorization check - Directors and School Administrators can grade any assignment
        if current_user.role not in ['Director', 'School Administrator']:
            flash("You are not authorized to grade assignments.", "danger")
            return redirect(url_for('management.assignments_and_grades'))
        
        # Get only students enrolled in this specific class
        try:
            enrolled_students = db.session.query(Student).join(Enrollment).filter(
                Enrollment.class_id == class_obj.id,
                Enrollment.is_active == True
            ).order_by(Student.last_name, Student.first_name).all()
        except Exception as e:
            current_app.logger.error(f"Error fetching enrolled students: {str(e)}")
            enrolled_students = []
        
        if not enrolled_students:
            flash("No students are currently enrolled in this class.", "warning")
            return redirect(url_for('management.assignments_and_grades'))
        
        students = enrolled_students
        
        if request.method == 'POST':
            try:
                # Get teacher staff record
                teacher = None
                if current_user.teacher_staff_id:
                    teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
                
                for student in students:
                    score = request.form.get(f'score_{student.id}')
                    comment = request.form.get(f'comment_{student.id}')
                    submission_type = request.form.get(f'submission_type_{student.id}')
                    submission_notes = request.form.get(f'submission_notes_{student.id}')
                    
                    # Handle manual submission tracking
                    if submission_type:
                        submission = Submission.query.filter_by(
                            student_id=student.id,
                            assignment_id=assignment_id
                        ).first()
                        
                        if submission_type in ['in_person', 'online']:
                            # Create or update submission
                            if submission:
                                submission.submission_type = submission_type
                                submission.submission_notes = submission_notes
                                submission.marked_by = teacher.id if teacher else None
                                submission.marked_at = datetime.utcnow()
                            else:
                                # Create new manual submission
                                submission = Submission(
                                    student_id=student.id,
                                    assignment_id=assignment_id,
                                    submission_type=submission_type,
                                    submission_notes=submission_notes,
                                    marked_by=teacher.id if teacher else None,
                                    marked_at=datetime.utcnow(),
                                    submitted_at=datetime.utcnow(),
                                    file_path=None  # No file for in-person submissions
                                )
                                db.session.add(submission)
                        elif submission_type == 'not_submitted' and submission:
                            # Remove submission if marked as not submitted
                            db.session.delete(submission)
                    
                    if score is not None:
                        try:
                            points_earned = float(score) if score else 0.0
                            
                            # Get total points from assignment (default to 100 if not set)
                            total_points = assignment.total_points if hasattr(assignment, 'total_points') and assignment.total_points else 100.0
                            
                            # Calculate percentage based on points earned vs total points
                            percentage = (points_earned / total_points * 100) if total_points > 0 else 0
                            
                            grade_data_dict = {
                                'score': points_earned,
                                'points_earned': points_earned,
                                'total_points': total_points,
                                'max_score': total_points,  # Keep for backward compatibility
                                'percentage': round(percentage, 2),
                                'comment': comment or '',
                                'feedback': comment or '',  # Keep for backward compatibility
                                'graded_at': datetime.utcnow().isoformat()
                            }
                            grade_data = json.dumps(grade_data_dict)
                            
                            grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()
                            if grade:
                                # Don't update grades that are already voided (preserve void status)
                                if not grade.is_voided:
                                    grade.grade_data = grade_data
                                    grade.graded_at = datetime.utcnow()
                                    # Check if grade should be voided due to late enrollment (only if not already voided)
                                    from management_routes.late_enrollment_utils import check_and_void_grade
                                    check_and_void_grade(grade)
                            else:
                                # Create grade using attribute assignment
                                grade = Grade()
                                grade.student_id = student.id
                                grade.assignment_id = assignment_id
                                grade.grade_data = grade_data
                                grade.graded_at = datetime.utcnow()
                                db.session.add(grade)
                                # Check if grade should be voided due to late enrollment
                                from management_routes.late_enrollment_utils import check_and_void_grade
                                # Flush to get the grade ID, then check void status
                                db.session.flush()
                                check_and_void_grade(grade)
                            
                            # Check if this is a redo submission and calculate final grade
                            redo = AssignmentRedo.query.filter_by(
                                assignment_id=assignment_id,
                                student_id=student.id,
                                is_used=True
                            ).first()
                            
                            if redo:
                                # This is a redo - calculate final grade
                                redo.redo_grade = points_earned
                                
                                # Apply late penalty if redo was late
                                effective_redo_grade = points_earned
                                if redo.was_redo_late:
                                    effective_redo_grade = max(0, points_earned - 10)  # 10% penalty
                                
                                # Keep higher grade
                                if redo.original_grade:
                                    redo.final_grade = max(redo.original_grade, effective_redo_grade)
                                else:
                                    redo.final_grade = effective_redo_grade
                                
                                # Update the grade_data with final grade
                                final_percentage = (redo.final_grade / total_points * 100) if total_points > 0 else 0
                                grade_data_dict['score'] = redo.final_grade
                                grade_data_dict['points_earned'] = redo.final_grade
                                grade_data_dict['percentage'] = round(final_percentage, 2)
                                grade_data_dict['is_redo_final'] = True
                                if redo.was_redo_late:
                                    grade_data_dict['comment'] = f"{comment or ''}\n[REDO: Late submission, 10% penalty applied. Original: {redo.original_grade}%, Redo: {points_earned}% (-10%), Final: {redo.final_grade}%]"
                                else:
                                    grade_data_dict['comment'] = f"{comment or ''}\n[REDO: Higher grade kept. Original: {redo.original_grade}%, Redo: {points_earned}%, Final: {redo.final_grade}%]"
                                grade.grade_data = json.dumps(grade_data_dict)
                            
                            # Create notification for the student
                            if student.user:
                                from app import create_notification
                                if redo:
                                    message = f'Your redo for "{assignment.title}" has been graded. Final Score: {redo.final_grade}%'
                                else:
                                    message = f'Your grade for "{assignment.title}" has been posted. Score: {points_earned}%'
                                
                                create_notification(
                                    user_id=student.user.id,
                                    notification_type='grade',
                                    title=f'Grade posted for {assignment.title}',
                                    message=message,
                                    link=url_for('student.student_grades')
                                )
                                
                        except ValueError:
                            flash(f"Invalid score format for student {student.id}.", "warning")
                            continue # Skip this student and continue with others
                
                db.session.commit()
                flash('Grades updated successfully.', 'success')
                return redirect(url_for('management.grade_assignment', assignment_id=assignment_id))
            
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving grades in grade_assignment: {str(e)}")
                import traceback
                traceback.print_exc()
                flash(f'Error saving grades: {str(e)}', 'danger')
                return redirect(url_for('management.grade_assignment', assignment_id=assignment_id))
        
        # GET request - show grading interface
        # Get total points from assignment (default to 100 if not set)
        assignment_total_points = assignment.total_points if hasattr(assignment, 'total_points') and assignment.total_points else 100.0
        
        # Get existing grades for this assignment
        grades = {}
        try:
            grade_records = Grade.query.filter_by(assignment_id=assignment_id).all()
            for g in grade_records:
                try:
                    if g.grade_data:
                        grade_data = json.loads(g.grade_data)
                        # Ensure grade_data has the expected structure
                        points_earned = grade_data.get('points_earned') or grade_data.get('score', 0)
                        # Always use assignment's total_points as source of truth, not stored value
                        total_points = assignment_total_points
                        # Always recalculate percentage using assignment's actual total_points
                        percentage = (points_earned / total_points * 100) if total_points > 0 else 0
                        
                        grade_data['points_earned'] = points_earned
                        grade_data['total_points'] = total_points
                        grade_data['percentage'] = round(percentage, 2)
                        grade_data['grade_id'] = g.id  # Add grade_id for history link
                        grade_data['is_voided'] = g.is_voided  # Include void status
                        grades[g.student_id] = grade_data
                    else:
                        grades[g.student_id] = {
                            'score': 0, 
                            'points_earned': 0,
                            'total_points': assignment_total_points,
                            'percentage': 0,
                            'comment': '', 
                            'grade_id': g.id,
                            'is_voided': g.is_voided  # Include void status
                        }
                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    current_app.logger.error(f"Error parsing grade_data for grade {g.id}: {str(e)}")
                    grades[g.student_id] = {
                        'score': 0, 
                        'points_earned': 0,
                        'total_points': assignment_total_points,
                        'percentage': 0,
                        'comment': '', 
                        'grade_id': g.id,
                        'is_voided': g.is_voided  # Include void status
                    }
        except Exception as e:
            current_app.logger.error(f"Error fetching grades: {str(e)}")
            grades = {}
        
        # Also check for voided grades that might not have grade_data (placeholder voided grades)
        voided_grades = Grade.query.filter_by(assignment_id=assignment_id, is_voided=True).all()
        for g in voided_grades:
            if g.student_id not in grades:
                grades[g.student_id] = {
                    'score': 0,
                    'points_earned': 0,
                    'total_points': assignment_total_points,
                    'percentage': 0,
                    'comment': '',
                    'grade_id': g.id,
                    'is_voided': True
                }
        
        # Get submissions
        submissions = {}
        try:
            submission_records = Submission.query.filter_by(assignment_id=assignment_id).all()
            submissions = {s.student_id: s for s in submission_records}
        except Exception as e:
            current_app.logger.error(f"Error fetching submissions: {str(e)}")
            submissions = {}
        
        # Get active extensions for this assignment
        extensions_dict = {}
        try:
            extensions = AssignmentExtension.query.filter_by(
                assignment_id=assignment_id,
                is_active=True
            ).all()
            extensions_dict = {ext.student_id: ext for ext in extensions}
        except Exception as e:
            current_app.logger.error(f"Error fetching extensions: {str(e)}")
            extensions_dict = {}
        
        # For quiz assignments, check if there are open-ended questions that need manual grading
        quiz_questions = None
        quiz_answers_by_student = {}
        has_open_ended_questions = False
        
        if assignment.assignment_type == 'quiz':
            # Load questions with options eagerly
            from sqlalchemy.orm import joinedload
            quiz_questions = QuizQuestion.query.options(joinedload(QuizQuestion.options)).filter_by(assignment_id=assignment_id).order_by(QuizQuestion.order).all()
            
            # Check if quiz has open-ended questions (short_answer or essay) that need manual grading
            has_open_ended_questions = any(q.question_type in ['short_answer', 'essay'] for q in quiz_questions)
            
            # If quiz has no open-ended questions, all questions are auto-graded
            # Show a message and redirect back to assignment view
            if not has_open_ended_questions:
                flash('This quiz contains only auto-graded questions (Multiple Choice/True-False). All grades are automatically calculated when students submit their quizzes. No manual grading is required.', 'info')
                return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
            
            # Load answers for all students with selected_option relationship
            for student in students:
                answers = QuizAnswer.query.options(
                    joinedload(QuizAnswer.question),
                    joinedload(QuizAnswer.selected_option)
                ).filter_by(
                    student_id=student.id
                ).join(QuizQuestion).filter(
                    QuizQuestion.assignment_id == assignment_id
                ).all()
                quiz_answers_by_student[student.id] = {answer.question_id: answer for answer in answers}
        
        # For discussion assignments, get threads and posts
        discussion_threads_by_student = {}
        discussion_posts_by_student = {}
        min_initial_posts = 1
        min_replies = 2
        
        if assignment.assignment_type == 'discussion':
            from models import DiscussionThread, DiscussionPost
            import re
            
            # Extract participation requirements from assignment description
            if assignment.description:
                initial_posts_match = re.search(r'Minimum (\d+) initial post', assignment.description)
                if initial_posts_match:
                    min_initial_posts = int(initial_posts_match.group(1))
                replies_match = re.search(r'Minimum (\d+) reply/replies', assignment.description)
                if replies_match:
                    min_replies = int(replies_match.group(1))
            
            # Get all threads and posts for this assignment
            all_threads = DiscussionThread.query.filter_by(assignment_id=assignment_id).all()
            all_posts = DiscussionPost.query.filter(
                DiscussionPost.thread_id.in_([t.id for t in all_threads])
            ).all()
            
            # Organize by student
            for student in students:
                # Count threads created by this student
                student_threads = [t for t in all_threads if t.student_id == student.id]
                discussion_threads_by_student[student.id] = student_threads
                
                # Count replies by this student
                student_posts = [p for p in all_posts if p.student_id == student.id]
                discussion_posts_by_student[student.id] = student_posts
        
        # Use specialized template based on assignment type
        if assignment.assignment_type == 'discussion':
            template_name = 'management/grade_discussion_assignment.html'
        elif assignment.assignment_type == 'quiz' and has_open_ended_questions:
            template_name = 'teachers/teacher_grade_quiz.html'
        else:
            template_name = 'teachers/teacher_grade_assignment.html'
        
        return render_template(template_name, 
                             assignment=assignment, 
                             class_obj=class_obj,
                             students=students, 
                             grades=grades, 
                             submissions=submissions,
                             extensions=extensions_dict,
                             role_prefix='management',
                             total_points=assignment_total_points,
                             quiz_questions=quiz_questions,
                             quiz_answers_by_student=quiz_answers_by_student,
                             discussion_threads_by_student=discussion_threads_by_student,
                             discussion_posts_by_student=discussion_posts_by_student,
                             min_initial_posts=min_initial_posts,
                             min_replies=min_replies)
    
    except Exception as e:
        current_app.logger.error(f"Error in grade_assignment route: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f"Error loading assignment: {str(e)}", "danger")
        return redirect(url_for('management.assignments_and_grades'))




# ============================================================
# Route: /assignment/<int:assignment_id>/export-to-google-forms', methods=['POST']
# Function: export_quiz_to_google_forms
# ============================================================

@bp.route('/assignment/<int:assignment_id>/export-to-google-forms', methods=['POST'])
@login_required
@management_required
def export_quiz_to_google_forms(assignment_id):
    """Export a native quiz to Google Forms"""
    from google_forms_service import get_google_forms_service, export_quiz_to_google_form
    from models import QuizQuestion, QuizOption, User
    from sqlalchemy.orm import joinedload
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if assignment is a quiz
    if assignment.assignment_type != 'quiz':
        flash('This is not a quiz assignment.', 'warning')
        return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
    
    # Check if already linked to a Google Form
    if assignment.google_form_linked:
        flash('This quiz is already linked to a Google Form. Unlink it first if you want to export to a new form.', 'warning')
        return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
    
    # Get the current user and check if they have Google credentials
    user = User.query.get(current_user.id)
    if not user.google_refresh_token:
        flash('Please connect your Google account in Settings to export quizzes to Google Forms.', 'warning')
        return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
    
    try:
        # Get Google Forms service
        service = get_google_forms_service(user)
        if not service:
            flash('Failed to connect to Google Forms. Please check your Google account connection.', 'danger')
            return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
        
        # Load quiz questions with options
        questions = QuizQuestion.query.options(joinedload(QuizQuestion.options)).filter_by(
            assignment_id=assignment_id
        ).order_by(QuizQuestion.order).all()
        
        if not questions:
            flash('This quiz has no questions. Please add questions before exporting.', 'warning')
            return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
        
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
    
    return redirect(url_for('management.view_assignment', assignment_id=assignment_id))




# ============================================================
# Route: /assignment/<int:assignment_id>/sync-google-forms', methods=['POST']
# Function: sync_google_forms_submissions
# ============================================================

@bp.route('/assignment/<int:assignment_id>/sync-google-forms', methods=['POST'])
@login_required
@management_required
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
        return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
    
    # Get the current user and check if they have Google credentials
    user = User.query.get(current_user.id)
    if not user.google_refresh_token:
        flash('Please connect your Google account in Settings to sync Google Forms submissions.', 'warning')
        return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
    
    try:
        # Get Google Forms service
        service = get_google_forms_service(user)
        if not service:
            flash('Failed to connect to Google Forms. Please check your Google account connection.', 'danger')
            return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
        
        # Get form responses
        responses = get_form_responses(service, assignment.google_form_id)
        if responses is None:
            flash('Failed to retrieve form responses from Google Forms.', 'danger')
            return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
        students_dict = {student.email.lower(): student for enrollment in enrollments 
                        for student in [enrollment.student] if enrollment.student and enrollment.student.email}
        
        synced_count = 0
        created_submissions = 0
        
        # Process each response
        for response in responses:
            # Get respondent email from response
            # Google Forms responses have answers with respondentEmail field
            respondent_email = response.get('respondentEmail', '').lower()
            
            if not respondent_email or respondent_email not in students_dict:
                # Try to find by name or skip if not found
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
    
    return redirect(url_for('management.view_assignment', assignment_id=assignment_id))




# ============================================================
# Route: /view-assignment/<int:assignment_id>
# Function: view_assignment
# ============================================================

@bp.route('/view-assignment/<int:assignment_id>')
@login_required
@management_required
def view_assignment(assignment_id):
    """View assignment details"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # For discussion assignments, use specialized view
        if assignment.assignment_type == 'discussion':
            from models import DiscussionThread, DiscussionPost, Enrollment, Student
            from collections import defaultdict
            
            # Get class information
            class_info = Class.query.get(assignment.class_id) if assignment.class_id else None
            teacher = None
            if class_info and class_info.teacher_id:
                teacher = TeacherStaff.query.get(class_info.teacher_id)
            
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
            enrolled_students = []
            if class_info:
                enrollments = Enrollment.query.filter_by(class_id=class_info.id, is_active=True).all()
                enrolled_students = [e.student for e in enrollments if e.student]
            
            # Get participant details
            participants = []
            participant_stats = defaultdict(lambda: {'threads': 0, 'replies': 0})
            
            for student_id in participant_ids:
                student = Student.query.get(student_id)
                if student:
                    # Count threads and replies for this student
                    threads_count = sum(1 for t in threads if t.student_id == student_id)
                    replies_count = sum(1 for p in all_posts if p.student_id == student_id)
                    
                    participant_stats[student_id] = {
                        'threads': threads_count,
                        'replies': replies_count
                    }
                    
                    participants.append({
                        'student': student,
                        'threads': threads_count,
                        'replies': replies_count,
                        'total_posts': threads_count + replies_count
                    })
            
            # Sort participants by total posts (descending)
            participants.sort(key=lambda x: x['total_posts'], reverse=True)
            
            # Get grades for this assignment
            from models import Grade
            grades = {}
            grade_records = Grade.query.filter_by(assignment_id=assignment_id).all()
            for g in grade_records:
                try:
                    if g.grade_data:
                        grade_data = json.loads(g.grade_data)
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
                                 class_info=class_info,
                                 teacher=teacher,
                                 threads=threads,
                                 participants=participants,
                                 enrolled_students=enrolled_students,
                                 grades=grades,
                                 min_initial_posts=min_initial_posts,
                                 min_replies=min_replies,
                                 role_prefix='management')
        
        # Get class information
        class_info = Class.query.get(assignment.class_id) if assignment.class_id else None
        teacher = None
        if class_info and class_info.teacher_id:
            teacher = TeacherStaff.query.get(class_info.teacher_id)
        
        # Get submissions - check if it's a regular assignment or group assignment
        from models import Submission, GroupSubmission, GroupAssignment
        
        try:
            # Try to get regular submissions
            submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
            submissions_count = len(submissions) if submissions else 0
        except Exception as e:
            print(f"Error getting submissions: {e}")
            submissions_count = 0
        
        # Check if there's a group assignment with the same assignment
        try:
            try:
                group_assignments = GroupAssignment.query.filter_by(class_id=assignment.class_id if assignment.class_id else 0).all()
            except Exception as e:
                current_app.logger.error(f"Error loading group assignments: {str(e)}")
                group_assignments = []
            group_submissions_count = 0
            for ga in group_assignments:
                # Try to match by title or other identifier
                if ga.title == assignment.title or ga.id == assignment_id:
                    group_submissions = GroupSubmission.query.filter_by(group_assignment_id=ga.id).all()
                    group_submissions_count += len(group_submissions) if group_submissions else 0
        except Exception as e:
            print(f"Error getting group submissions: {e}")
            group_submissions_count = 0
        
        total_submissions_count = submissions_count + group_submissions_count
        
        # Get points from assignment - safely handle missing attributes
        assignment_points = 0
        if hasattr(assignment, 'total_points') and assignment.total_points:
            assignment_points = assignment.total_points
        elif hasattr(assignment, 'points') and assignment.points:
            assignment_points = assignment.points
        
        # Get current date for status calculations
        today = datetime.now().date()
        
        # Get voided grades for the unvoid modal
        from models import Grade
        voided_grades = Grade.query.filter_by(assignment_id=assignment_id, is_voided=True).all()
        voided_student_ids = {g.student_id for g in voided_grades}
        
        # For quiz assignments, check if there are open-ended questions that need manual grading
        has_open_ended_questions = False
        if assignment.assignment_type == 'quiz':
            from models import QuizQuestion
            quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).all()
            has_open_ended_questions = any(q.question_type in ['short_answer', 'essay'] for q in quiz_questions)
        
        return render_template('shared/view_assignment.html', 
                             assignment=assignment,
                             class_info=class_info,
                             teacher=teacher,
                             submissions_count=total_submissions_count,
                             assignment_points=assignment_points,
                             today=today,
                             voided_student_ids=voided_student_ids,
                             has_open_ended_questions=has_open_ended_questions)
    except Exception as e:
        current_app.logger.error(f"Error in view_assignment route: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading assignment: {str(e)}', 'danger')
        return redirect(url_for('management.assignments_and_grades'))




# ============================================================
# Route: /edit-assignment/<int:assignment_id>', methods=['GET', 'POST']
# Function: edit_assignment
# ============================================================

@bp.route('/edit-assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@management_required
def edit_assignment(assignment_id):
    """Edit an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors and School Administrators can edit any assignment
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('management.assignments_and_grades'))
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
        assignment_context = request.form.get('assignment_context', 'homework')
        total_points = request.form.get('total_points', type=float)
        
        if not all([title, due_date_str, quarter]):
            flash('Title, Due Date, and Quarter are required.', 'danger')
            return redirect(request.url)
        
        if total_points is None or total_points <= 0:
            total_points = 100.0
        
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
            assignment.assignment_context = assignment_context
            assignment.total_points = total_points
            
            # Handle file upload (only if a new file is provided)
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
                            assignment.attachment_file_path = filepath
                            assignment.attachment_file_size = os.path.getsize(filepath)
                            assignment.attachment_mime_type = file.content_type
                            
                        except Exception as e:
                            flash(f'Error saving file: {str(e)}', 'danger')
                            db.session.rollback()
                            return redirect(request.url)
                    else:
                        flash(f'File type not allowed.', 'danger')
                        db.session.rollback()
                        return redirect(request.url)
            
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
            
        except ValueError:
            flash("Invalid date format.", "danger")
            db.session.rollback()
            return redirect(request.url)
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(request.url)
    
    # For GET request, get all classes for the dropdown (for reference, but class will be pre-selected)
    classes = Class.query.all()
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    
    # Get current quarter for reference
    current_quarter = get_current_quarter()
    
    # Get context from assignment or default
    context = assignment.assignment_context if assignment.assignment_context else 'homework'
    
    return render_template('shared/edit_assignment.html', 
                         assignment=assignment,
                         class_obj=class_obj,
                         classes=classes,
                         school_years=school_years,
                         teacher=None,  # Not needed for management
                         current_quarter=current_quarter,
                         context=context)




# ============================================================
# Route: /assignment/remove/<int:assignment_id>', methods=['POST']
# Function: remove_assignment_alt
# ============================================================

@bp.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def remove_assignment_alt(assignment_id):
    """Remove an assignment - alternative route"""
    return remove_assignment(assignment_id)



# ============================================================
# Route: /remove-assignment/<int:assignment_id>', methods=['POST']
# Function: remove_assignment
# ============================================================

@bp.route('/remove-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get(assignment_id)
    
    # If assignment doesn't exist, it's already been deleted - return success
    if not assignment:
        # Check if this is an AJAX/fetch request
        wants_json = request.accept_mimetypes.accept_json or \
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                    'application/json' in request.headers.get('Accept', '')
        
        if wants_json:
            return jsonify({
                'success': True,
                'message': 'Assignment already removed.'
            })
        
        flash('Assignment already removed.', 'info')
        class_id_param = request.args.get('class_id')
        if class_id_param:
            return redirect(url_for('management.assignments_and_grades', class_id=class_id_param))
        else:
            return redirect(url_for('management.assignments_and_grades'))
    
    # Authorization check - Directors and School Administrators can remove any assignment
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to remove this assignment.", "danger")
        return redirect(url_for('management.assignments_and_grades'))
    
    # Store values we need before any operations that might trigger relationships
    class_id = assignment.class_id
    attachment_filename = assignment.attachment_filename
    
    try:
        from models import (
            QuizQuestion, QuizProgress, DiscussionThread, DiscussionPost, QuizAnswer, 
            DeadlineReminder, AssignmentExtension
        )
        
        # CRITICAL: Delete deadline reminders FIRST using raw SQL
        # This must happen before any other operations to avoid relationship access
        try:
            db.session.execute(
                db.text("DELETE FROM deadline_reminder WHERE assignment_id = :assignment_id"),
                {"assignment_id": assignment_id}
            )
            db.session.flush()
        except Exception as e:
            current_app.logger.warning(f"Could not delete deadline reminders: {e}")
        
        # Delete associated records in proper order to avoid foreign key constraint issues
        
        # 1. Delete quiz answers first (they reference quiz questions)
        quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).all()
        for question in quiz_questions:
            QuizAnswer.query.filter_by(question_id=question.id).delete()
        
        # 2. Delete quiz questions (they reference assignments)
        QuizQuestion.query.filter_by(assignment_id=assignment_id).delete()
        
        # 3. Delete quiz progress
        QuizProgress.query.filter_by(assignment_id=assignment_id).delete()
        
        # 4. Delete discussion threads and posts
        discussion_threads = DiscussionThread.query.filter_by(assignment_id=assignment_id).all()
        for thread in discussion_threads:
            # Delete posts first (they reference threads)
            DiscussionPost.query.filter_by(thread_id=thread.id).delete()
        DiscussionThread.query.filter_by(assignment_id=assignment_id).delete()
        
        # 5. Delete grades (they reference assignments)
        Grade.query.filter_by(assignment_id=assignment_id).delete()
        
        # 6. Delete submissions (they reference assignments)
        Submission.query.filter_by(assignment_id=assignment_id).delete()
        
        # 7. Delete extensions (they reference assignments)
        AssignmentExtension.query.filter_by(assignment_id=assignment_id).delete()
        
        # Delete the assignment file if it exists (using stored value to avoid accessing assignment)
        if attachment_filename:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete the assignment using raw SQL to avoid relationship access
        # This prevents SQLAlchemy from trying to lazy-load deadline_reminders relationship
        try:
            db.session.execute(
                db.text("DELETE FROM assignment WHERE id = :assignment_id"),
                {"assignment_id": assignment_id}
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        
        # Check if this is an AJAX/fetch request by checking Accept header or X-Requested-With
        wants_json = request.accept_mimetypes.accept_json or \
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                    'application/json' in request.headers.get('Accept', '')
        
        if wants_json:
            # Return JSON response for AJAX requests
            return jsonify({
                'success': True,
                'message': 'Assignment removed successfully.'
            })
        
        flash('Assignment removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        error_message = f'Error removing assignment: {str(e)}'
        
        # Log the full error for debugging
        print(f"ERROR REMOVING ASSIGNMENT {assignment_id}:")
        print(error_message)
        print(error_trace)
        current_app.logger.error(f'Error removing assignment {assignment_id}: {error_message}\n{error_trace}')
        
        # Check if this is an AJAX/fetch request
        wants_json = request.accept_mimetypes.accept_json or \
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                    'application/json' in request.headers.get('Accept', '')
        
        if wants_json:
            return jsonify({
                'success': False,
                'message': f'Error removing assignment: {str(e)}'
            }), 500
        
        flash(error_message, 'danger')
    
    # Redirect back to assignments page, preserving class_id if it was in the request
    class_id_param = request.args.get('class_id')
    if class_id_param:
        return redirect(url_for('management.assignments_and_grades', class_id=class_id_param))
    else:
        return redirect(url_for('management.assignments_and_grades'))




# ============================================================
# Route: /grades/statistics/<int:assignment_id>
# Function: admin_grade_statistics
# ============================================================

@bp.route('/grades/statistics/<int:assignment_id>')
@login_required
@management_required
def admin_grade_statistics(assignment_id):
    """Display grade statistics dashboard for an assignment with charts - Management view."""
    from models import Grade
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Get all grades for this assignment
    grades = Grade.query.filter_by(assignment_id=assignment_id, is_voided=False).all()
    
    # Calculate statistics
    stats = {
        'total_students': len(grades),
        'graded_count': 0,
        'ungraded_count': 0,
        'average_score': 0,
        'median_score': 0,
        'highest_score': 0,
        'lowest_score': 100,
        'passing_count': 0,
        'failing_count': 0
    }
    
    scores = []
    letter_grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    grade_distribution = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '0-59': 0}
    
    total_points = assignment.total_points if assignment.total_points else 100.0
    
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            score = grade_data.get('score') or grade_data.get('points_earned')
            
            if score is not None:
                stats['graded_count'] += 1
                score_float = float(score)
                scores.append(score_float)
                
                # Calculate percentage
                percentage = (score_float / total_points * 100) if total_points > 0 else 0
                
                # Update min/max
                if score_float > stats['highest_score']:
                    stats['highest_score'] = score_float
                if score_float < stats['lowest_score']:
                    stats['lowest_score'] = score_float
                
                # Passing/failing (70% threshold)
                if percentage >= 70:
                    stats['passing_count'] += 1
                else:
                    stats['failing_count'] += 1
                
                # Letter grade distribution
                if percentage >= 90:
                    letter_grades['A'] += 1
                    grade_distribution['90-100'] += 1
                elif percentage >= 80:
                    letter_grades['B'] += 1
                    grade_distribution['80-89'] += 1
                elif percentage >= 70:
                    letter_grades['C'] += 1
                    grade_distribution['70-79'] += 1
                elif percentage >= 60:
                    letter_grades['D'] += 1
                    grade_distribution['60-69'] += 1
                else:
                    letter_grades['F'] += 1
                    grade_distribution['0-59'] += 1
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
    
    # Calculate averages
    if scores:
        stats['average_score'] = round(sum(scores) / len(scores), 2)
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        stats['median_score'] = round((sorted_scores[mid] + sorted_scores[~mid]) / 2, 2) if len(sorted_scores) > 1 else round(sorted_scores[0], 2)
        stats['average_percentage'] = round((stats['average_score'] / total_points * 100) if total_points > 0 else 0, 2)
    else:
        stats['average_percentage'] = 0
    
    stats['ungraded_count'] = stats['total_students'] - stats['graded_count']
    
    return render_template('management/admin_grade_statistics.html',
                         assignment=assignment,
                         stats=stats,
                         letter_grades=letter_grades,
                         grade_distribution=grade_distribution,
                         total_points=total_points)



# ============================================================
# Route: /group-assignment/<int:assignment_id>/statistics
# Function: admin_group_grade_statistics
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/statistics')
@login_required
@management_required
def admin_group_grade_statistics(assignment_id):
    """Display grade statistics dashboard for a group assignment with charts - Management view."""
    from models import GroupGrade, GroupAssignment
    
    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    
    # Get all grades for this group assignment
    grades = GroupGrade.query.filter_by(group_assignment_id=assignment_id, is_voided=False).all()
    
    # Calculate statistics
    stats = {
        'total_students': len(grades),
        'graded_count': 0,
        'ungraded_count': 0,
        'average_score': 0,
        'median_score': 0,
        'highest_score': 0,
        'lowest_score': 100,
        'passing_count': 0,
        'failing_count': 0
    }
    
    scores = []
    letter_grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    grade_distribution = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '0-59': 0}
    
    total_points = group_assignment.total_points if group_assignment.total_points else 100.0
    
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            score = grade_data.get('score') or grade_data.get('points_earned')
            
            if score is not None:
                stats['graded_count'] += 1
                score_float = float(score)
                scores.append(score_float)
                
                # Calculate percentage
                percentage = (score_float / total_points * 100) if total_points > 0 else 0
                
                # Update min/max
                if score_float > stats['highest_score']:
                    stats['highest_score'] = score_float
                if score_float < stats['lowest_score']:
                    stats['lowest_score'] = score_float
                
                # Passing/failing (70% threshold)
                if percentage >= 70:
                    stats['passing_count'] += 1
                else:
                    stats['failing_count'] += 1
                
                # Letter grade distribution
                if percentage >= 90:
                    letter_grades['A'] += 1
                    grade_distribution['90-100'] += 1
                elif percentage >= 80:
                    letter_grades['B'] += 1
                    grade_distribution['80-89'] += 1
                elif percentage >= 70:
                    letter_grades['C'] += 1
                    grade_distribution['70-79'] += 1
                elif percentage >= 60:
                    letter_grades['D'] += 1
                    grade_distribution['60-69'] += 1
                else:
                    letter_grades['F'] += 1
                    grade_distribution['0-59'] += 1
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
    
    # Calculate averages
    if scores:
        stats['average_score'] = round(sum(scores) / len(scores), 2)
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        stats['median_score'] = round((sorted_scores[mid] + sorted_scores[~mid]) / 2, 2) if len(sorted_scores) > 1 else round(sorted_scores[0], 2)
        stats['average_percentage'] = round((stats['average_score'] / total_points * 100) if total_points > 0 else 0, 2)
    else:
        stats['average_percentage'] = 0
    
    stats['ungraded_count'] = stats['total_students'] - stats['graded_count']
    
    return render_template('management/admin_grade_statistics.html',
                         assignment=group_assignment,
                         stats=stats,
                         letter_grades=letter_grades,
                         grade_distribution=grade_distribution,
                         total_points=total_points,
                         is_group_assignment=True)



# ============================================================
# Route: /grades/history/<int:grade_id>
# Function: admin_grade_history
# ============================================================

@bp.route('/grades/history/<int:grade_id>')
@login_required
@management_required
def admin_grade_history(grade_id):
    """View grade history/audit trail for a specific grade - Management view."""
    from models import GradeHistory, User, Grade
    
    grade = Grade.query.get_or_404(grade_id)
    assignment = grade.assignment
    
    # Get all history entries for this grade
    history_entries = GradeHistory.query.filter_by(grade_id=grade_id).order_by(GradeHistory.changed_at.desc()).all()
    
    # Format history entries with user information
    formatted_history = []
    for entry in history_entries:
        try:
            changed_by_user = User.query.get(entry.changed_by)
            previous_data = json.loads(entry.previous_grade_data) if entry.previous_grade_data else None
            new_data = json.loads(entry.new_grade_data) if entry.new_grade_data else None
            
            formatted_history.append({
                'entry': entry,
                'changed_by': changed_by_user.username if changed_by_user else 'Unknown',
                'changed_at': entry.changed_at,
                'previous_data': previous_data,
                'new_data': new_data,
                'reason': entry.change_reason
            })
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Parse current grade data
    try:
        current_grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
    except (json.JSONDecodeError, TypeError):
        current_grade_data = {}
    
    return render_template('management/admin_grade_history.html',
                         grade=grade,
                         assignment=assignment,
                         current_grade_data=current_grade_data,
                         history=formatted_history)



# ============================================================
# Route: /void-grade/<int:grade_id>', methods=['POST']
# Function: void_grade
# ============================================================

@bp.route('/void-grade/<int:grade_id>', methods=['POST'])
@login_required
@management_required
def void_grade(grade_id):
    """Void a grade for an individual assignment"""
    from datetime import datetime
    
    grade = Grade.query.get_or_404(grade_id)
    reason = request.form.get('reason', 'No reason provided')
    
    try:
        grade.is_voided = True
        grade.voided_by = current_user.id
        grade.voided_at = datetime.utcnow()
        grade.voided_reason = reason
        
        db.session.commit()
        flash('Grade voided successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error voiding grade: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('management.assignments_and_grades'))




# ============================================================
# Route: /void-group-grade/<int:grade_id>', methods=['POST']
# Function: void_group_grade
# ============================================================

@bp.route('/void-group-grade/<int:grade_id>', methods=['POST'])
@login_required
@management_required
def void_group_grade(grade_id):
    """Void a grade for a group assignment"""
    from datetime import datetime
    from models import GroupGrade
    
    grade = GroupGrade.query.get_or_404(grade_id)
    reason = request.form.get('reason', 'No reason provided')
    
    try:
        grade.is_voided = True
        grade.voided_by = current_user.id
        grade.voided_at = datetime.utcnow()
        grade.voided_reason = reason
        
        db.session.commit()
        flash('Group grade voided successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error voiding group grade: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('management.assignments_and_grades'))


# ============================================================
# Route: /group-assignment/<int:assignment_id>/void', methods=['POST']
# Function: void_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/void', methods=['POST'])
@login_required
@management_required
def void_group_assignment(assignment_id):
    """Void a group assignment for all groups, specific groups, or specific students."""
    from datetime import datetime
    from models import GroupAssignment, GroupGrade, StudentGroup, StudentGroupMember
    import json
    
    try:
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        void_scope = request.form.get('void_scope', 'all_groups')
        reason = request.form.get('reason', 'Voided by administrator')
        group_ids = request.form.getlist('group_ids')
        student_ids = request.form.getlist('student_ids')
        
        voided_count = 0
        
        if void_scope == 'all_groups':
            # Void for all groups and all students
            groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
            for group in groups:
                members = StudentGroupMember.query.filter_by(group_id=group.id).all()
                for member in members:
                    group_grade = GroupGrade.query.filter_by(
                        group_assignment_id=assignment_id,
                        student_id=member.student_id
                    ).first()
                    
                    if group_grade:
                        if not group_grade.is_voided:
                            group_grade.is_voided = True
                            group_grade.voided_by = current_user.id
                            group_grade.voided_at = datetime.utcnow()
                            group_grade.voided_reason = reason
                            voided_count += 1
                    else:
                        # Create voided grade placeholder
                        new_grade = GroupGrade(
                            student_id=member.student_id,
                            group_assignment_id=assignment_id,
                            student_group_id=group.id,
                            grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                            is_voided=True,
                            voided_by=current_user.id,
                            voided_at=datetime.utcnow(),
                            voided_reason=reason
                        )
                        db.session.add(new_grade)
                        voided_count += 1
            
            flash(f'Voided assignment for all groups ({voided_count} students).', 'success')
            
        elif void_scope == 'specific_groups':
            # Void for specific groups
            if not group_ids:
                flash('Please select at least one group.', 'warning')
                return redirect(request.referrer or url_for('management.admin_view_group_assignment', assignment_id=assignment_id))
            
            for group_id in group_ids:
                group = StudentGroup.query.get(int(group_id))
                if group:
                    members = StudentGroupMember.query.filter_by(group_id=group.id).all()
                    for member in members:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=member.student_id
                        ).first()
                        
                        if group_grade:
                            if not group_grade.is_voided:
                                group_grade.is_voided = True
                                group_grade.voided_by = current_user.id
                                group_grade.voided_at = datetime.utcnow()
                                group_grade.voided_reason = reason
                                voided_count += 1
                        else:
                            new_grade = GroupGrade(
                                student_id=member.student_id,
                                group_assignment_id=assignment_id,
                                student_group_id=group.id,
                                grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                                is_voided=True,
                                voided_by=current_user.id,
                                voided_at=datetime.utcnow(),
                                voided_reason=reason
                            )
                            db.session.add(new_grade)
                            voided_count += 1
            
            flash(f'Voided assignment for selected groups ({voided_count} students).', 'success')
            
        elif void_scope == 'specific_students':
            # Void for specific students
            if not student_ids:
                flash('Please select at least one student.', 'warning')
                return redirect(request.referrer or url_for('management.admin_view_group_assignment', assignment_id=assignment_id))
            
            for student_id in student_ids:
                # Find student's group
                member = StudentGroupMember.query.filter_by(
                    student_id=int(student_id),
                    group_id=StudentGroup.query.filter_by(class_id=group_assignment.class_id).subquery().c.id
                ).first()
                
                # Alternative: find by checking all groups
                groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
                student_group = None
                for group in groups:
                    member_check = StudentGroupMember.query.filter_by(group_id=group.id, student_id=int(student_id)).first()
                    if member_check:
                        student_group = group
                        break
                
                if student_group:
                    group_grade = GroupGrade.query.filter_by(
                        group_assignment_id=assignment_id,
                        student_id=int(student_id)
                    ).first()
                    
                    if group_grade:
                        if not group_grade.is_voided:
                            group_grade.is_voided = True
                            group_grade.voided_by = current_user.id
                            group_grade.voided_at = datetime.utcnow()
                            group_grade.voided_reason = reason
                            voided_count += 1
                    else:
                        new_grade = GroupGrade(
                            student_id=int(student_id),
                            group_assignment_id=assignment_id,
                            student_group_id=student_group.id,
                            grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                            is_voided=True,
                            voided_by=current_user.id,
                            voided_at=datetime.utcnow(),
                            voided_reason=reason
                        )
                        db.session.add(new_grade)
                        voided_count += 1
            
            flash(f'Voided assignment for selected students ({voided_count} students).', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error voiding group assignment: {str(e)}', 'danger')
        print(f"Error voiding group assignment: {e}")
    
    return redirect(request.referrer or url_for('management.admin_view_group_assignment', assignment_id=assignment_id))


# ============================================================
# Route: /group-assignment/<int:assignment_id>/unvoid', methods=['POST']
# Function: unvoid_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/unvoid', methods=['POST'])
@login_required
@management_required
def unvoid_group_assignment(assignment_id):
    """Unvoid a group assignment - restore all voided grades."""
    from models import GroupAssignment, GroupGrade
    
    try:
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        unvoid_scope = request.form.get('unvoid_scope', 'all')
        
        voided_grades = GroupGrade.query.filter_by(
            group_assignment_id=assignment_id,
            is_voided=True
        ).all()
        
        unvoided_count = 0
        for grade in voided_grades:
            grade.is_voided = False
            grade.voided_by = None
            grade.voided_at = None
            grade.voided_reason = None
            unvoided_count += 1
        
        db.session.commit()
        flash(f'Restored assignment for {unvoided_count} students.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error restoring group assignment: {str(e)}', 'danger')
        print(f"Error unvoiding group assignment: {e}")
    
    return redirect(request.referrer or url_for('management.admin_view_group_assignment', assignment_id=assignment_id))


# ============================================================
# Route: /group-assignment/<int:assignment_id>/change-status', methods=['POST']
# Function: admin_change_group_assignment_status
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/change-status', methods=['POST'])
@login_required
@management_required
def admin_change_group_assignment_status(assignment_id):
    """Change the status of a group assignment."""
    from models import GroupAssignment
    
    try:
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        new_status = request.form.get('status')
        
        if new_status in ['Active', 'Inactive', 'Upcoming', 'Voided']:
            group_assignment.status = new_status
            db.session.commit()
            flash(f'Assignment status changed to {new_status}.', 'success')
        else:
            flash('Invalid status.', 'danger')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing assignment status: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('management.admin_view_group_assignment', assignment_id=assignment_id))


# ============================================================================
# ASSIGNMENT REDO SYSTEM
# ============================================================================



# ============================================================
# Route: /grant-redo/<int:assignment_id>', methods=['POST']
# Function: grant_assignment_redo
# ============================================================

@bp.route('/grant-redo/<int:assignment_id>', methods=['POST'])
@login_required
def grant_assignment_redo(assignment_id):
    """Grant redo permission for an assignment to selected students"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Only allow redos for PDF/Paper assignments
    if assignment.assignment_type not in ['PDF', 'Paper', 'pdf', 'paper']:
        return jsonify({'success': False, 'message': 'Redos are only available for PDF/Paper assignments.'})
    
    # Authorization check - Teachers, School Admins, and Directors
    from decorators import is_teacher_role
    from sqlalchemy import or_
    from models import class_additional_teachers, class_substitute_teachers
    
    is_teacher = is_teacher_role(current_user.role)
    is_admin = current_user.role in ['Director', 'School Administrator']
    
    if is_teacher:
        # Teachers can only grant redos for their own classes (primary, additional, or substitute)
        if not current_user.teacher_staff_id:
            return jsonify({'success': False, 'message': 'Teacher record not found.'})
        
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        if not teacher:
            return jsonify({'success': False, 'message': 'Teacher record not found.'})
        
        class_obj = assignment.class_info
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class not found.'})
        
        # Check if teacher is authorized for this class
        is_authorized = (
            class_obj.teacher_id == teacher.id or
            db.session.query(class_additional_teachers).filter(
                class_additional_teachers.c.class_id == class_obj.id,
                class_additional_teachers.c.teacher_id == teacher.id
            ).count() > 0 or
            db.session.query(class_substitute_teachers).filter(
                class_substitute_teachers.c.class_id == class_obj.id,
                class_substitute_teachers.c.teacher_id == teacher.id
            ).count() > 0
        )
        
        if not is_authorized:
            return jsonify({'success': False, 'message': 'You can only grant redos for your own classes.'})
    elif not is_admin:
        return jsonify({'success': False, 'message': 'You are not authorized to grant redos.'})
    
    # Get form data
    student_ids = request.form.getlist('student_ids[]')
    redo_deadline_str = request.form.get('redo_deadline')
    reason = request.form.get('reason', '').strip()
    
    if not student_ids:
        return jsonify({'success': False, 'message': 'Please select at least one student.'})
    
    if not redo_deadline_str:
        return jsonify({'success': False, 'message': 'Please provide a redo deadline.'})
    
    try:
        # Parse redo deadline
        redo_deadline = datetime.strptime(redo_deadline_str, '%Y-%m-%d')
        
        # Get teacher staff record
        teacher = None
        if current_user.teacher_staff_id:
            teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        
        granted_count = 0
        already_granted_count = 0
        redo_count = 0
        reopen_count = 0
        
        for student_id in student_ids:
            student_id = int(student_id)
            
            # Check if student is enrolled in this class
            enrollment = Enrollment.query.filter_by(
                student_id=student_id,
                class_id=assignment.class_id,
                is_active=True
            ).first()
            
            if not enrollment:
                continue
            
            # Check if student has already submitted this assignment
            # This determines if it's a "redo" (has submission) or "reopen" (no submission)
            submission = Submission.query.filter_by(
                student_id=student_id,
                assignment_id=assignment_id
            ).first()
            
            has_submitted = submission is not None and submission.submission_type != 'not_submitted'
            
            # Check if redo already exists (for students who have submitted)
            existing_redo = None
            if has_submitted:
                existing_redo = AssignmentRedo.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id
                ).first()
            
            # Check if reopening already exists (for students who haven't submitted)
            existing_reopening = None
            if not has_submitted:
                existing_reopening = AssignmentReopening.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    is_active=True
                ).first()
            
            if existing_redo:
                # Update existing redo
                existing_redo.redo_deadline = redo_deadline
                existing_redo.reason = reason if reason else existing_redo.reason
                existing_redo.granted_at = datetime.utcnow()
                if teacher:
                    existing_redo.granted_by = teacher.id
                already_granted_count += 1
                
                # Notify student of updated redo
                student = Student.query.get(student_id)
                if student and student.user:
                    from app import create_notification
                    create_notification(
                        user_id=student.user.id,
                        notification_type='assignment',
                        title=f'Redo Updated: {assignment.title}',
                        message=f'Your redo opportunity for "{assignment.title}" has been updated. New deadline: {redo_deadline.strftime("%m/%d/%Y")}',
                        link=url_for('student.student_assignments')
                    )
            elif existing_reopening:
                # Update existing reopening - convert to redo if they've now submitted
                if has_submitted:
                    # Student has now submitted, so convert reopening to redo
                    existing_reopening.is_active = False
                    
                    # Get original grade if it exists
                    grade = Grade.query.filter_by(
                        student_id=student_id,
                        assignment_id=assignment_id
                    ).first()
                    
                    original_grade = None
                    if grade and grade.grade_data:
                        try:
                            grade_data = json.loads(grade.grade_data)
                            original_grade = grade_data.get('score')
                        except:
                            pass
                    
                    # Create redo
                    redo = AssignmentRedo(
                        assignment_id=assignment_id,
                        student_id=student_id,
                        granted_by=teacher.id if teacher else None,
                        redo_deadline=redo_deadline,
                        reason=reason,
                        original_grade=original_grade
                    )
                    db.session.add(redo)
                    granted_count += 1
                    redo_count += 1
                    
                    # Notify student of conversion from reopening to redo
                    student = Student.query.get(student_id)
                    if student and student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='assignment',
                            title=f'Redo Opportunity: {assignment.title}',
                            message=f'You have been granted permission to redo "{assignment.title}". New deadline: {redo_deadline.strftime("%m/%d/%Y")}',
                            link=url_for('student.student_assignments')
                        )
                else:
                    # Still no submission, just update reopening
                    existing_reopening.reason = reason if reason else existing_reopening.reason
                    existing_reopening.reopened_at = datetime.utcnow()
                    if teacher:
                        existing_reopening.reopened_by = teacher.id
                    already_granted_count += 1
                    
                    # Notify student of updated reopening
                    student = Student.query.get(student_id)
                    if student and student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='assignment',
                            title=f'Reopening Updated: {assignment.title}',
                            message=f'Your reopening for "{assignment.title}" has been updated.',
                            link=url_for('student.student_assignments')
                        )
            else:
                # Create new record based on whether student has submitted
                if has_submitted:
                    # Student has submitted - create a REDO
                    grade = Grade.query.filter_by(
                        student_id=student_id,
                        assignment_id=assignment_id
                    ).first()
                    
                    original_grade = None
                    if grade and grade.grade_data:
                        try:
                            grade_data = json.loads(grade.grade_data)
                            original_grade = grade_data.get('score')
                        except:
                            pass
                    
                    redo = AssignmentRedo(
                        assignment_id=assignment_id,
                        student_id=student_id,
                        granted_by=teacher.id if teacher else None,
                        redo_deadline=redo_deadline,
                        reason=reason,
                        original_grade=original_grade
                    )
                    db.session.add(redo)
                    granted_count += 1
                    redo_count += 1
                    
                    # Create notification for redo
                    student = Student.query.get(student_id)
                    if student and student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='assignment',
                            title=f'Redo Opportunity: {assignment.title}',
                            message=f'You have been granted permission to redo "{assignment.title}". New deadline: {redo_deadline.strftime("%m/%d/%Y")}',
                            link=url_for('student.student_assignments')
                        )
                else:
                    # Student hasn't submitted - create a REOPENING
                    # Deactivate any existing reopenings first
                    existing_reopenings = AssignmentReopening.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=student_id,
                        is_active=True
                    ).all()
                    for reopening in existing_reopenings:
                        reopening.is_active = False
                    
                    reopening = AssignmentReopening(
                        assignment_id=assignment_id,
                        student_id=student_id,
                        reopened_by=teacher.id if teacher else None,
                        reason=reason,
                        additional_attempts=0,  # Not applicable for PDF/Paper
                        is_active=True
                    )
                    db.session.add(reopening)
                    granted_count += 1
                    reopen_count += 1
                    
                    # Create notification for reopen
                    student = Student.query.get(student_id)
                    if student and student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='assignment',
                            title=f'Assignment Reopened: {assignment.title}',
                            message=f'"{assignment.title}" has been reopened for you. New deadline: {redo_deadline.strftime("%m/%d/%Y")}',
                            link=url_for('student.student_assignments')
                        )
        
        db.session.commit()
        
        # Build message based on what was granted
        message_parts = []
        if redo_count > 0:
            message_parts.append(f'{redo_count} redo(s) granted')
        if reopen_count > 0:
            message_parts.append(f'{reopen_count} reopening(s) granted')
        if already_granted_count > 0:
            message_parts.append(f'{already_granted_count} existing record(s) updated')
        
        message = f'Successfully processed {granted_count} student(s). ' + ', '.join(message_parts) + '.'
        
        return jsonify({'success': True, 'message': message})
        
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error granting redo: {str(e)}')
        return jsonify({'success': False, 'message': f'Error granting redo: {str(e)}'})




# ============================================================
# Route: /revoke-redo/<int:redo_id>', methods=['POST']
# Function: revoke_assignment_redo
# ============================================================

@bp.route('/revoke-redo/<int:redo_id>', methods=['POST'])
@login_required
def revoke_assignment_redo(redo_id):
    """Revoke a redo permission"""
    redo = AssignmentRedo.query.get_or_404(redo_id)
    
    # Authorization check - Teachers, School Admins, and Directors
    if current_user.role == 'Teacher':
        # Teachers can only revoke redos for their own classes
        if current_user.teacher_staff_id:
            teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
            if redo.assignment.class_info.teacher_id != teacher.id:
                return jsonify({'success': False, 'message': 'You can only revoke redos for your own classes.'})
        else:
            return jsonify({'success': False, 'message': 'Teacher record not found.'})
    elif current_user.role not in ['Director', 'School Administrator']:
        return jsonify({'success': False, 'message': 'You are not authorized to revoke redos.'})
    
    # Don't allow revoking if student has already used the redo
    if redo.is_used:
        return jsonify({'success': False, 'message': 'Cannot revoke a redo that has already been used.'})
    
    try:
        # Notify student
        if redo.student and redo.student.user:
            create_notification(
                user_id=redo.student.user.id,
                notification_type='assignment',
                title=f'Redo Revoked: {redo.assignment.title}',
                message=f'Your redo permission for "{redo.assignment.title}" has been revoked.',
                link=url_for('student.student_assignments')
            )
        
        db.session.delete(redo)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Redo permission revoked successfully.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error revoking redo: {str(e)}'})




# ============================================================
# Route: /assignment/<int:assignment_id>/redos
# Function: view_assignment_redos
# ============================================================

@bp.route('/assignment/<int:assignment_id>/redos')
@login_required
def view_assignment_redos(assignment_id):
    """View all redo permissions for an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Authorization check - Teachers can only view redos for their own classes
    if current_user.role == 'Teacher':
        if current_user.teacher_staff_id:
            teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
            if assignment.class_info.teacher_id != teacher.id:
                return jsonify({'success': False, 'message': 'You can only view redos for your own classes.'}), 403
        else:
            return jsonify({'success': False, 'message': 'Teacher record not found.'}), 403
    elif current_user.role not in ['Director', 'School Administrator']:
        return jsonify({'success': False, 'message': 'You are not authorized to view redos.'}), 403
    
    # Get all redos for this assignment
    redos = AssignmentRedo.query.filter_by(assignment_id=assignment_id).all()
    
    redo_data = []
    for redo in redos:
        redo_data.append({
            'id': redo.id,
            'student_name': f"{redo.student.first_name} {redo.student.last_name}",
            'student_id': redo.student_id,
            'granted_at': redo.granted_at.strftime('%m/%d/%Y %I:%M %p'),
            'redo_deadline': redo.redo_deadline.strftime('%m/%d/%Y'),
            'reason': redo.reason or 'No reason provided',
            'is_used': redo.is_used,
            'redo_submitted_at': redo.redo_submitted_at.strftime('%m/%d/%Y %I:%M %p') if redo.redo_submitted_at else None,
            'original_grade': redo.original_grade,
            'redo_grade': redo.redo_grade,
            'final_grade': redo.final_grade,
            'was_redo_late': redo.was_redo_late
        })
    
    return jsonify({'success': True, 'redos': redo_data})




# ============================================================
# Route: /assignment/change-status/<int:assignment_id>', methods=['POST']
# Function: change_assignment_status
# ============================================================

@bp.route('/assignment/change-status/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def change_assignment_status(assignment_id):
    """Change assignment status"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Authorization check - Directors and School Administrators can change any assignment status
    if current_user.role not in ['Director', 'School Administrator']:
        return jsonify({'success': False, 'message': 'You are not authorized to change assignment status.'})
    
    new_status = request.form.get('status')
    
    # Validate status
    valid_statuses = ['Active', 'Inactive', 'Voided']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid status selected.'})
    
    try:
        assignment.status = new_status
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Assignment status changed to {new_status} successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error changing assignment status: {str(e)}'})



# ============================================================
# Route: /assignment/grant-extensions', methods=['POST']
# Function: grant_extensions
# ============================================================

@bp.route('/assignment/grant-extensions', methods=['POST'])
@login_required
@management_required
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
        extended_due_date = datetime.strptime(extended_due_date_str, '%Y-%m-%dT%H:%M')
        
        # Get the assignment
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Authorization check - Directors and School Administrators can grant extensions for any assignment
        if current_user.role not in ['Director', 'School Administrator']:
            return jsonify({'success': False, 'message': 'You are not authorized to grant extensions.'})
        
        # Get the teacher_staff_id for granted_by field
        # Try to get from current_user, otherwise use class teacher
        granter_id = None
        if current_user.teacher_staff_id:
            granter_id = current_user.teacher_staff_id
        else:
            # Use the class teacher as fallback for admin granting
            class_obj = assignment.class_info
            if class_obj and class_obj.teacher_id:
                granter_id = class_obj.teacher_id
        
        if not granter_id:
            return jsonify({'success': False, 'message': 'Cannot grant extensions: No teacher found for assignment.'})
        
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
        return jsonify({'success': False, 'message': str(e)})



# ============================================================
# Route: /group-assignment/<int:assignment_id>/view
# Function: admin_view_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/view')
@login_required
@management_required
def admin_view_group_assignment(assignment_id):
    """View details of a specific group assignment - Management view."""
    from models import GroupAssignment, GroupSubmission, StudentGroup, AssignmentExtension, Assignment
    import json
    
    try:
        # First check if this is actually a group assignment
        group_assignment = GroupAssignment.query.get(assignment_id)
        if not group_assignment:
            # Not a group assignment - redirect to regular assignment view
            flash('This is not a group assignment.', 'info')
            return redirect(url_for('management.view_assignment', assignment_id=assignment_id))
        
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
        
        # Get extensions for this assignment
        try:
            extensions = AssignmentExtension.query.filter_by(assignment_id=assignment_id).all()
        except:
            extensions = []
        
        # Calculate enhanced statistics
        from models import GroupGrade
        from datetime import datetime, timedelta
        
        # Get all group grades (including voided ones for the unvoid button check)
        all_group_grades = GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()
        non_voided_grades = [g for g in all_group_grades if not g.is_voided]  # Non-voided for graded count
        graded_count = len(non_voided_grades)
        
        # Calculate total students in groups
        total_students = sum(len(group.members) for group in groups)
        
        # Calculate submission statistics
        submission_count = len(submissions)
        late_submissions = len([s for s in submissions if s.is_late])
        on_time_submissions = submission_count - late_submissions
        
        # Calculate submission rate
        submission_rate = (submission_count / len(groups) * 100) if groups else 0
        
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
        if group_grades and len(group_grades) > 0:
            assignment_status = 'Graded'
            status_class = 'success'
        elif group_assignment.status == 'Inactive':
            assignment_status = 'Inactive'
            status_class = 'secondary'
        else:
            assignment_status = 'Active'
            status_class = 'primary'
        
        return render_template('management/admin_view_group_assignment.html',
                             group_assignment=group_assignment,
                             submissions=submissions,
                             groups=groups,
                             extensions=extensions,
                             group_grades=all_group_grades,  # Pass all grades (including voided) for void check
                             graded_count=graded_count,
                             total_students=total_students,
                             submission_count=submission_count,
                             late_submissions=late_submissions,
                             on_time_submissions=on_time_submissions,
                             submission_rate=submission_rate,
                             time_info=time_info,
                             assignment_status=assignment_status,
                             status_class=status_class)
    except Exception as e:
        print(f"Error viewing group assignment: {e}")
        flash('Error accessing group assignment details.', 'error')
        return redirect(url_for('management.admin_class_group_assignments', class_id=group_assignment.class_id))



# ============================================================
# Route: /group-assignment/<int:assignment_id>/grade', methods=['GET', 'POST']
# Function: admin_grade_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/grade', methods=['GET', 'POST'])
@login_required
def admin_grade_group_assignment(assignment_id):
    """Grade a group assignment - Allows teachers and administrators."""
    from models import GroupAssignment, StudentGroup, GroupGrade, AssignmentExtension, TeacherStaff
    from teacher_routes.utils import is_authorized_for_class
    import json
    
    try:
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        
        # Authorization check - Teachers can grade assignments for their classes, Admins can grade any
        if current_user.role not in ['Director', 'School Administrator']:
            # Check if teacher is authorized for this class
            if not is_authorized_for_class(group_assignment.class_info):
                flash("You are not authorized to grade this assignment.", "danger")
                return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
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
        
        # Collect all students from all groups
        all_students = []
        students_by_id = {}
        for group in groups:
            for member in group.members:
                if member.student and member.student.id not in students_by_id:
                    all_students.append(member.student)
                    students_by_id[member.student.id] = member.student
        
        # Get existing grades
        grades_by_student = {}
        try:
            existing_grades = GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()
            for grade in existing_grades:
                if grade.grade_data:
                    try:
                        grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                        # Add comments from the separate field
                        grade_data['comment'] = grade.comments or ''
                        grade_data['comments'] = grade.comments or ''
                        grades_by_student[grade.student_id] = grade_data
                    except:
                        grades_by_student[grade.student_id] = {'score': 0, 'comments': '', 'comment': ''}
        except:
            pass
        
        # Get active extensions for this assignment
        extensions = AssignmentExtension.query.filter_by(
            assignment_id=assignment_id,
            is_active=True
        ).all()
        extensions_dict = {ext.student_id: ext for ext in extensions}
        
        # Calculate statistics
        total_students = len(all_students)
        graded_count = len([g for g in grades_by_student.values() if g.get('score', 0) > 0])
        total_score = sum([g.get('score', 0) for g in grades_by_student.values() if g.get('score', 0) > 0])
        average_score = (total_score / graded_count) if graded_count > 0 else 0
        
        if request.method == 'POST':
            try:
                saved_count = 0
                for group in groups:
                    for member in group.members:
                        student_id = member.student.id
                        score_key = f"score_{group.id}_{student_id}"
                        comments_key = f"comments_{group.id}_{student_id}"
                        
                        if score_key in request.form:
                            score = request.form.get(score_key)
                            comments = request.form.get(comments_key, '')
                            
                            if score:
                                try:
                                    points_earned = float(score)
                                    # Get total points from assignment (default to 100 if not set)
                                    total_points = group_assignment.total_points if group_assignment.total_points else 100.0
                                    
                                    if 0 <= points_earned <= total_points:
                                        # Calculate percentage and letter grade
                                        percentage = (points_earned / total_points * 100) if total_points > 0 else 0
                                        if percentage >= 90:
                                            letter_grade = 'A'
                                        elif percentage >= 80:
                                            letter_grade = 'B'
                                        elif percentage >= 70:
                                            letter_grade = 'C'
                                        elif percentage >= 60:
                                            letter_grade = 'D'
                                        else:
                                            letter_grade = 'F'
                                        
                                        grade_data = {
                                            'score': points_earned,
                                            'points_earned': points_earned,
                                            'total_points': total_points,
                                            'max_score': total_points,  # Keep for backward compatibility
                                            'percentage': round(percentage, 2),
                                            'letter_grade': letter_grade
                                        }
                                        
                                        # Get teacher_staff_id for graded_by field
                                        # Try to get from current_user, otherwise use class teacher
                                        graded_by_id = None
                                        if current_user.teacher_staff_id:
                                            graded_by_id = current_user.teacher_staff_id
                                        else:
                                            # Use the class teacher as fallback for admin grading
                                            class_obj = group_assignment.class_info
                                            if class_obj and class_obj.teacher_id:
                                                graded_by_id = class_obj.teacher_id
                                        
                                        # Update or create grade
                                        existing_grade = GroupGrade.query.filter_by(
                                            group_assignment_id=assignment_id,
                                            group_id=group.id,
                                            student_id=student_id
                                        ).first()
                                        
                                        if existing_grade:
                                            existing_grade.grade_data = json.dumps(grade_data)
                                            existing_grade.comments = comments
                                            if graded_by_id:
                                                existing_grade.graded_by = graded_by_id
                                        else:
                                            if not graded_by_id:
                                                # If we still don't have a teacher_staff_id, we can't create the grade
                                                flash(f'Cannot create grade: No teacher found for assignment.', 'danger')
                                                continue
                                            new_grade = GroupGrade(
                                                group_assignment_id=assignment_id,
                                                group_id=group.id,
                                                student_id=student_id,
                                                grade_data=json.dumps(grade_data),
                                                graded_by=graded_by_id,
                                                comments=comments
                                            )
                                            db.session.add(new_grade)
                                        
                                        saved_count += 1
                                except ValueError:
                                    flash(f'Invalid score for {member.student.first_name} {member.student.last_name}', 'warning')
                
                db.session.commit()
                
                # Check if this is an AJAX request
                wants_json = request.accept_mimetypes.accept_json or \
                            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                            'application/json' in request.headers.get('Accept', '')
                
                if wants_json:
                    return jsonify({
                        'success': True,
                        'message': 'Grades saved successfully!',
                        'graded_count': saved_count
                    })
                
                flash('Grades saved successfully!', 'success')
                return redirect(url_for('management.admin_grade_group_assignment', assignment_id=assignment_id))
                
            except Exception as e:
                db.session.rollback()
                print(f"Error saving grades: {e}")
                flash('Error saving grades. Please try again.', 'error')
        
        # Get total points from assignment (default to 100 if not set)
        assignment_total_points = group_assignment.total_points if group_assignment.total_points else 100.0
        
        return render_template('management/admin_grade_group_assignment.html',
                             group_assignment=group_assignment,
                             class_obj=group_assignment.class_info,
                             groups=groups,
                             students=all_students,
                             grades=grades_by_student,
                             extensions=extensions_dict,
                             total_students=total_students,
                             graded_count=graded_count,
                             average_score=average_score,
                             total_points=assignment_total_points,
                             today=datetime.now().date())
    except Exception as e:
        print(f"Error grading group assignment: {e}")
        flash('Error accessing group assignment grading.', 'error')
        return redirect(url_for('management.admin_class_group_assignments', class_id=group_assignment.class_id))



# ============================================================
# Route: /group-assignment/<int:assignment_id>/delete', methods=['POST']
# Function: admin_delete_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/delete', methods=['POST'])
@login_required
@management_required
def admin_delete_group_assignment(assignment_id):
    """Delete a group assignment - Management view."""
    try:
        from models import GroupAssignment, GroupGrade, GroupSubmission, DeadlineReminder
        
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        
        # Delete related grades first
        GroupGrade.query.filter_by(group_assignment_id=assignment_id).delete()
        
        # Delete related submissions
        GroupSubmission.query.filter_by(group_assignment_id=assignment_id).delete()
        
        # Delete deadline reminders (they reference group assignments)
        # Use raw SQL directly to avoid ORM trying to load columns that may not exist
        try:
            db.session.execute(
                db.text("DELETE FROM deadline_reminder WHERE group_assignment_id = :assignment_id"),
                {"assignment_id": assignment_id}
            )
        except Exception as e:
            current_app.logger.warning(f"Could not delete deadline reminders: {e}")
        
        # Delete the assignment itself
        db.session.delete(group_assignment)
        db.session.commit()
        
        flash('Group assignment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting assignment: {str(e)}', 'danger')
    
    # Redirect back to the appropriate page
    return redirect(url_for('management.admin_class_group_assignments', class_id=group_assignment.class_id))



# ============================================================
# Route: /group-assignment/<int:assignment_id>/edit', methods=['GET', 'POST']
# Function: admin_edit_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
@management_required
def admin_edit_group_assignment(assignment_id):
    """Edit a group assignment - Management view."""
    try:
        from models import GroupAssignment
        
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        
        if request.method == 'POST':
            try:
                # Update assignment fields
                group_assignment.title = request.form.get('title', group_assignment.title)
                group_assignment.description = request.form.get('description', group_assignment.description)
                
                # Update due date
                due_date_str = request.form.get('due_date')
                if due_date_str:
                    try:
                        from datetime import datetime
                        group_assignment.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        flash('Invalid due date format.', 'error')
                        return render_template('management/admin_edit_group_assignment.html', 
                                             group_assignment=group_assignment)
                
                # Update group size constraints
                min_size = request.form.get('min_group_size')
                max_size = request.form.get('max_group_size')
                if min_size and max_size:
                    try:
                        group_assignment.min_group_size = int(min_size)
                        group_assignment.max_group_size = int(max_size)
                    except ValueError:
                        flash('Invalid group size values.', 'error')
                        return render_template('management/admin_edit_group_assignment.html', 
                                             group_assignment=group_assignment)
                
                group_assignment.assignment_type = request.form.get('assignment_type', group_assignment.assignment_type)
                group_assignment.collaboration_type = request.form.get('collaboration_type', group_assignment.collaboration_type)
                
                db.session.commit()
                flash('Assignment updated successfully!', 'success')
                return redirect(url_for('management.admin_view_group_assignment', assignment_id=assignment_id))
                
            except Exception as e:
                db.session.rollback()
                print(f"Error updating assignment: {e}")
                flash('Error updating assignment. Please try again.', 'error')
        
        return render_template('management/admin_edit_group_assignment.html', 
                             group_assignment=group_assignment)
    except Exception as e:
        print(f"Error editing group assignment: {e}")
        flash('Error accessing group assignment editing.', 'error')
        return redirect(url_for('management.admin_class_group_assignments', class_id=group_assignment.class_id))



# ============================================================
# Route: /assignment/<int:assignment_id>/extensions
# Function: admin_grant_extensions
# ============================================================

@bp.route('/assignment/<int:assignment_id>/extensions')
@login_required
@management_required
def admin_grant_extensions(assignment_id):
    """View and manage extensions for an assignment - Management view."""
    try:
        from models import Assignment, AssignmentExtension, Class, Student, Enrollment
        
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = Class.query.get_or_404(assignment.class_id)
        
        # Get existing extensions for this assignment
        extensions = AssignmentExtension.query.filter_by(assignment_id=assignment_id).all()
        
        # Get students in this class for granting new extensions (using Enrollment, not Class.students)
        enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
        students = [e.student for e in enrollments if e.student]
        
        return render_template('management/admin_grant_extensions.html',
                             assignment=assignment,
                             class_obj=class_obj,
                             extensions=extensions,
                             students=students)
    except Exception as e:
        print(f"Error viewing extensions: {e}")
        import traceback
        traceback.print_exc()
        flash('Error accessing extensions management.', 'error')
        return redirect(url_for('management.view_assignment', assignment_id=assignment_id))

@bp.route('/assignment/<int:assignment_id>/reopen', methods=['POST'])
@login_required
@management_required
def admin_reopen_assignment(assignment_id):
    """Reopen an assignment for selected students - Management view."""
    try:
        from models import Assignment, AssignmentReopening, Enrollment, TeacherStaff, Submission
        from flask_login import current_user
        
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = Class.query.get_or_404(assignment.class_id)
        
        # Get form data
        student_ids = request.form.getlist('student_ids')
        reason = request.form.get('reason', '')
        additional_attempts = request.form.get('additional_attempts', type=int, default=0)
        
        if not student_ids:
            return jsonify({'success': False, 'message': 'Please select at least one student.'})
        
        # For quizzes, additional_attempts is required
        if assignment.assignment_type == 'quiz' and additional_attempts <= 0:
            return jsonify({'success': False, 'message': 'For quiz assignments, you must specify the number of additional attempts to grant.'})
        
        # Get the teacher_staff_id for the current user (admin/director)
        # For management users, we need to find or create a TeacherStaff record
        teacher_staff = None
        if current_user.role in ['Director', 'School Administrator']:
            # Try to find existing TeacherStaff record
            if current_user.teacher_staff_id:
                teacher_staff = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first()
            if not teacher_staff:
                from models import User
                teacher_staff = TeacherStaff.query.join(User).filter(User.id == current_user.id).first()
            # If not found, we'll use a system/admin ID or create a placeholder
            if not teacher_staff:
                # For now, use the first available teacher or system ID
                # In production, you might want to create a system admin TeacherStaff record
                teacher_staff = TeacherStaff.query.first()
        
        reopened_by_id = teacher_staff.id if teacher_staff else None
        
        if not reopened_by_id:
            return jsonify({'success': False, 'message': 'Cannot reopen assignment: No teacher record found.'})
        
        reopened_count = 0
        
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
        
        message = f'Successfully reopened assignment for {reopened_count} student(s).'
        if assignment.assignment_type == 'quiz' and additional_attempts > 0:
            message += f' Each student has been granted {additional_attempts} additional attempt(s).'
        
        return jsonify({
            'success': True,
            'message': message,
            'reopened_count': reopened_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reopening assignment: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error reopening assignment: {str(e)}'})

@bp.route('/assignment/<int:assignment_id>/reopen-status', methods=['GET'])
@login_required
@management_required
def admin_get_reopen_status(assignment_id):
    """Get reopening status for all students in the assignment's class - Management view."""
    try:
        from models import Assignment, AssignmentReopening, Student, Submission
        
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = Class.query.get_or_404(assignment.class_id)
        
        # Get all enrolled students
        enrollments = Enrollment.query.filter_by(
            class_id=class_obj.id,
            is_active=True
        ).all()
        
        student_data = []
        
        for enrollment in enrollments:
            if not enrollment.student:
                continue
            
            student = enrollment.student
            
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
            
            # Check if assignment is inactive/closed
            if assignment.status not in ['Active']:
                needs_reopening = True
                reason_needs_reopening.append(f'Assignment is {assignment.status.lower()}')
            
            # For quizzes, check if max attempts reached
            if assignment.assignment_type == 'quiz' and assignment.max_attempts:
                if submissions_count >= assignment.max_attempts:
                    needs_reopening = True
                    reason_needs_reopening.append(f'Max attempts ({assignment.max_attempts}) reached')
            
            student_data.append({
                'student_id': student.id,
                'name': f'{student.first_name} {student.last_name}',
                'has_reopening': reopening is not None,
                'additional_attempts': reopening.additional_attempts if reopening else 0,
                'reopened_at': reopening.reopened_at.isoformat() if reopening and reopening.reopened_at else None,
                'needs_reopening': needs_reopening,
                'reason_needs_reopening': ', '.join(reason_needs_reopening) if reason_needs_reopening else None,
                'submissions_count': submissions_count,
                'max_attempts': assignment.max_attempts if assignment.assignment_type == 'quiz' else None
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
@management_required
def admin_revoke_reopen(assignment_id):
    """Revoke (deactivate) reopenings for selected students - Management view."""
    try:
        from models import Assignment, AssignmentReopening
        
        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = Class.query.get_or_404(assignment.class_id)
        
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