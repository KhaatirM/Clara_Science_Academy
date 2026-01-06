"""
Quiz management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, SchoolYear, QuizQuestion, QuizOption, QuizAnswer
)
from datetime import datetime

bp = Blueprint('quizzes', __name__)

@bp.route('/assignment/create/quiz', methods=['GET', 'POST'])
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
                return redirect(url_for('teacher.create_quiz_assignment'))
            
            # Check if user is authorized for this class
            class_obj = Class.query.get(class_id)
            if not is_authorized_for_class(class_obj):
                flash("You are not authorized to create assignments for this class.", "danger")
                return redirect(url_for('teacher.create_quiz_assignment'))
            
            # Create the quiz assignment (total_points will be calculated from questions)
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                open_date=open_date,
                close_date=close_date,
                total_points=100.0,  # Will be calculated from questions
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='quiz',
                status=calculated_status,
                created_by=current_user.id
            )
            
            db.session.add(new_assignment)
            db.session.flush()  # Get the assignment ID
            
            # Debug: Print all form data
            print(f"DEBUG: Quiz creation form data:")
            for key, value in request.form.items():
                print(f"  {key}: {value}")
            
            print(f"DEBUG: Found {len([k for k in request.form.keys() if k.startswith('question_text_') and not k.endswith('[]')])} questions")
            
            # Save quiz questions
            question_count = 0
            total_points = 0
            
            for key, value in request.form.items():
                if key.startswith('question_text_') and not key.endswith('[]'):
                    # Extract question ID from the field name (e.g., question_text_1 -> 1)
                    question_id = key.split('_')[-1]
                    question_text = value
                    question_type = request.form.get(f'question_type_{question_id}')
                    points = float(request.form.get(f'question_points_{question_id}', 1.0))
                    
                    print(f"DEBUG: Processing question {question_count}:")
                    print(f"  ID: {question_id}")
                    print(f"  Text: {question_text}")
                    print(f"  Type: {question_type}")
                    print(f"  Points: {points}")
                    
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
                    
                    total_points += points
                    
                    # Save options for multiple choice and true/false
                    if question_type in ['multiple_choice', 'true_false']:
                        option_count = 0
                        # Collect all options for the current question
                        options_for_question = request.form.getlist(f'option_text_{question_id}[]')
                        correct_answer = request.form.get(f'correct_answer_{question_id}')
                        
                        print(f"DEBUG: Processing options for question {question_id}:")
                        print(f"  Correct answer: {correct_answer}")
                        print(f"  Options: {options_for_question}")
                        
                        for option_text in options_for_question:
                            if option_text and option_text.strip():
                                is_correct = str(option_count) == correct_answer
                                print(f"    Option {option_count}: '{option_text}' (correct: {is_correct})")
                                
                                option = QuizOption(
                                    question_id=question.id,
                                    option_text=option_text.strip(),
                                    is_correct=is_correct,
                                    order=option_count
                                )
                                db.session.add(option)
                                option_count += 1
                    
                    question_count += 1
            
            # Update assignment total_points to total from questions
            new_assignment.total_points = total_points if total_points > 0 else 100.0
            
            print(f"DEBUG: Successfully processed {question_count} questions")
            db.session.commit()
            flash('Quiz assignment created successfully!', 'success')
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Error creating quiz assignment: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error creating quiz assignment: {str(e)}', 'danger')
    
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
    
    return render_template('shared/create_quiz_assignment.html', classes=classes, teacher=teacher)

@bp.route('/assignment/create/discussion', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_discussion_assignment():
    """Create a discussion assignment"""
    from teacher_routes.assignment_utils import calculate_assignment_status
    from .utils import get_teacher_or_admin, is_authorized_for_class
    from datetime import timezone
    
    # Get classes for dropdown
    teacher = get_teacher_or_admin()
    if teacher:
        classes = Class.query.filter_by(teacher_id=teacher.id, is_active=True).order_by(Class.name).all()
    else:
        classes = []
    
    # Check if coming from a specific class
    class_id_param = request.args.get('class_id', type=int)
    class_obj = None
    if class_id_param:
        class_obj = Class.query.get(class_id_param)
        if class_obj and not is_authorized_for_class(class_obj):
            flash("You are not authorized to access this class.", "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
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
            return render_template('shared/create_discussion_assignment.html', classes=classes, class_obj=class_obj)
        
        # Check authorization
        class_obj = Class.query.get(class_id)
        if not class_obj or not is_authorized_for_class(class_obj):
            flash("You are not authorized to create assignments for this class.", "danger")
            return render_template('shared/create_discussion_assignment.html', classes=classes, class_obj=None)
        
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
                return render_template('shared/create_discussion_assignment.html', classes=classes, class_obj=class_obj)
            
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
            
            # Create the discussion assignment
            new_assignment = Assignment(
                title=title,
                description=full_description,
                due_date=due_date,
                open_date=open_date,
                close_date=close_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='discussion',
                status=calculated_status,
                assignment_context=assignment_context,
                total_points=total_points,
                created_by=current_user.id
            )
            
            db.session.add(new_assignment)
            db.session.commit()
            
            flash('Discussion assignment created successfully!', 'success')
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating discussion assignment: {str(e)}")
            flash(f'Error creating discussion assignment: {str(e)}', 'danger')
    
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
    
    return render_template('shared/create_discussion_assignment.html', classes=classes, teacher=teacher)

