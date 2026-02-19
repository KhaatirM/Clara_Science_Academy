"""
Quiz management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, SchoolYear, QuizQuestion, QuizOption, QuizAnswer, QuizSection,
    QuestionBank, QuestionBankQuestion, QuestionBankOption
)
from datetime import datetime

bp = Blueprint('quizzes', __name__)

def _build_quiz_data_for_edit(assignment):
    """Build quiz_data dict (blocks with sections and questions) for template pre-fill."""
    from models import QuizSection
    sections = QuizSection.query.filter_by(assignment_id=assignment.id).order_by(QuizSection.order).all()
    questions = QuizQuestion.query.filter_by(assignment_id=assignment.id).order_by(QuizQuestion.order).all()
    sections_by_id = {s.id: s for s in sections}
    blocks = []
    prev_section_id = None
    for q in questions:
        sec = sections_by_id.get(q.section_id) if q.section_id else None
        if sec and sec.id != prev_section_id:
            blocks.append({'type': 'section', 'title': sec.title or 'New Section'})
            prev_section_id = sec.id
        opts = QuizOption.query.filter_by(question_id=q.id).order_by(QuizOption.order).all()
        blocks.append({
            'type': 'question',
            'question_text': q.question_text,
            'question_type': q.question_type or 'multiple_choice',
            'points': float(q.points) if q.points is not None else 1.0,
            'options': [{'option_text': o.option_text, 'is_correct': bool(o.is_correct)} for o in opts]
        })
    return {'blocks': blocks}


@bp.route('/assignment/create/quiz', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_quiz_assignment():
    """Create or edit a quiz assignment"""
    if request.method == 'POST':
        assignment_id = request.form.get('assignment_id', type=int)
        is_edit = bool(assignment_id)
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            redirect_target = url_for('teacher.create_quiz_assignment')
            if is_edit:
                redirect_target += f'?edit={assignment_id}'
            return redirect(redirect_target)
        
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
                redirect_target = url_for('teacher.create_quiz_assignment')
                if is_edit:
                    redirect_target += f'?edit={assignment_id}'
                return redirect(redirect_target)
            
            if is_edit:
                existing = Assignment.query.get(assignment_id)
                if not existing or existing.assignment_type != 'quiz':
                    flash("Quiz assignment not found or invalid.", "danger")
                    return redirect(url_for('teacher.create_quiz_assignment'))
                if not is_authorized_for_class(existing.class_info):
                    flash("You are not authorized to edit this assignment.", "danger")
                    return redirect(url_for('teacher.create_quiz_assignment'))
                # Update assignment fields
                existing.title = title
                existing.description = description
                existing.due_date = due_date
                existing.open_date = open_date
                existing.close_date = close_date
                existing.quarter = str(quarter)
                existing.class_id = class_id
                existing.status = calculated_status
                new_assignment = existing
                # Delete old sections and questions (cascade will remove options)
                QuizSection.query.filter_by(assignment_id=assignment_id).delete()
                QuizQuestion.query.filter_by(assignment_id=assignment_id).delete()
            else:
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
            
            # Save sections and questions in block order (section_0, question_1, section_1, question_2, ...)
            block_order_str = request.form.get('block_order', '').strip()
            question_count = 0
            total_points = 0.0
            current_section_id = None
            section_order = 0
            
            if block_order_str:
                blocks = [b.strip() for b in block_order_str.split(',') if b.strip()]
                for block in blocks:
                    if block.startswith('section_'):
                        try:
                            section_idx = block.replace('section_', '')
                            title = request.form.get(f'section_title_{section_idx}', '').strip() or f'Part {section_order + 1}'
                            sec = QuizSection(
                                assignment_id=new_assignment.id,
                                title=title,
                                order=section_order
                            )
                            db.session.add(sec)
                            db.session.flush()
                            current_section_id = sec.id
                            section_order += 1
                        except Exception:
                            pass
                        continue
                    if block.startswith('question_'):
                        try:
                            question_id = block.replace('question_', '')
                        except Exception:
                            continue
                        question_text = request.form.get(f'question_text_{question_id}', '').strip()
                        if not question_text:
                            continue
                        question_type = request.form.get(f'question_type_{question_id}', 'multiple_choice')
                        points = float(request.form.get(f'question_points_{question_id}', 1.0))
                        total_points += points
                        question = QuizQuestion(
                            assignment_id=new_assignment.id,
                            section_id=current_section_id,
                            question_text=question_text,
                            question_type=question_type,
                            points=points,
                            order=question_count
                        )
                        db.session.add(question)
                        db.session.flush()
                        if question_type == 'multiple_choice':
                            option_count = 0
                            correct_answer = request.form.get(f'correct_answer_{question_id}', '')
                            option_values = request.form.getlist(f'option_text_{question_id}[]')
                            for option_text in option_values:
                                option_text = option_text.strip()
                                if not option_text:
                                    continue
                                is_correct = str(option_count) == correct_answer
                                db.session.add(QuizOption(
                                    question_id=question.id,
                                    option_text=option_text,
                                    is_correct=is_correct,
                                    order=option_count
                                ))
                                option_count += 1
                        elif question_type == 'true_false':
                            correct_answer = request.form.get(f'correct_answer_{question_id}', '')
                            db.session.add(QuizOption(
                                question_id=question.id,
                                option_text='True',
                                is_correct=(correct_answer == 'true'),
                                order=0
                            ))
                            db.session.add(QuizOption(
                                question_id=question.id,
                                option_text='False',
                                is_correct=(correct_answer == 'false'),
                                order=1
                            ))
                        question_count += 1
            else:
                # Fallback: no block_order
                for key, value in request.form.items():
                    if key.startswith('question_text_') and not key.endswith('[]'):
                        question_id = key.split('_')[-1]
                        question_text = value.strip()
                        if not question_text:
                            continue
                        question_type = request.form.get(f'question_type_{question_id}', 'multiple_choice')
                        points = float(request.form.get(f'question_points_{question_id}', 1.0))
                        total_points += points
                        question = QuizQuestion(
                            assignment_id=new_assignment.id,
                            section_id=None,
                            question_text=question_text,
                            question_type=question_type,
                            points=points,
                            order=question_count
                        )
                        db.session.add(question)
                        db.session.flush()
                        if question_type == 'multiple_choice':
                            option_count = 0
                            correct_answer = request.form.get(f'correct_answer_{question_id}', '')
                            option_values = request.form.getlist(f'option_text_{question_id}[]')
                            for option_text in option_values:
                                option_text = option_text.strip()
                                if not option_text:
                                    continue
                                is_correct = str(option_count) == correct_answer
                                db.session.add(QuizOption(
                                    question_id=question.id,
                                    option_text=option_text,
                                    is_correct=is_correct,
                                    order=option_count
                                ))
                                option_count += 1
                        elif question_type == 'true_false':
                            correct_answer = request.form.get(f'correct_answer_{question_id}', '')
                            db.session.add(QuizOption(
                                question_id=question.id,
                                option_text='True',
                                is_correct=(correct_answer == 'true'),
                                order=0
                            ))
                            db.session.add(QuizOption(
                                question_id=question.id,
                                option_text='False',
                                is_correct=(correct_answer == 'false'),
                                order=1
                            ))
                        question_count += 1
            
            # Update assignment total_points to total from questions
            new_assignment.total_points = total_points if total_points > 0 else 100.0
            db.session.commit()
            flash('Quiz assignment updated successfully!' if is_edit else 'Quiz assignment created successfully!', 'success')
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Error creating quiz assignment: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error creating quiz assignment: {str(e)}', 'danger')
    
    # GET request - show the form (create or edit)
    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all() if teacher else []
    
    assignment = None
    quiz_data = None
    edit_id = request.args.get('edit', type=int)
    if edit_id:
        assignment = Assignment.query.get(edit_id)
        if not assignment or assignment.assignment_type != 'quiz':
            flash("Quiz assignment not found.", "danger")
            return redirect(url_for('teacher.create_quiz_assignment'))
        if not is_authorized_for_class(assignment.class_info):
            flash("You are not authorized to edit this assignment.", "danger")
            return redirect(url_for('teacher.create_quiz_assignment'))
        quiz_data = _build_quiz_data_for_edit(assignment)
    
    question_banks_url = url_for('teacher.quizzes.question_banks_json')
    save_to_bank_url = url_for('teacher.quizzes.save_to_bank')
    return render_template('shared/create_quiz_assignment.html', classes=classes, teacher=teacher, assignment=assignment, quiz_data=quiz_data, question_banks_url=question_banks_url, save_to_bank_url=save_to_bank_url)


@bp.route('/api/question-banks')
@login_required
@teacher_required
def question_banks_json():
    """Return question banks (user's + public) with questions and options for Import from Bank."""
    banks = QuestionBank.query.filter(
        (QuestionBank.created_by == current_user.id) | (QuestionBank.is_public == True)
    ).order_by(QuestionBank.name).all()
    out = []
    for bank in banks:
        questions = QuestionBankQuestion.query.filter_by(bank_id=bank.id).order_by(QuestionBankQuestion.order).all()
        q_list = []
        for q in questions:
            opts = QuestionBankOption.query.filter_by(question_id=q.id).order_by(QuestionBankOption.order).all()
            q_list.append({
                'id': q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'points': float(q.points),
                'options': [{'option_text': o.option_text, 'is_correct': o.is_correct} for o in opts]
            })
        out.append({'id': bank.id, 'name': bank.name, 'questions': q_list})
    return jsonify(out)


@bp.route('/api/save-to-bank', methods=['POST'])
@login_required
@teacher_required
def save_to_bank():
    """Create a question bank from JSON body: { name, questions: [{ question_text, question_type, points, options }] }."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    questions = data.get('questions') or []
    if not name:
        return jsonify({'success': False, 'message': 'Bank name is required.'}), 400
    if not questions:
        return jsonify({'success': False, 'message': 'Add at least one question.'}), 400
    try:
        bank = QuestionBank(name=name, created_by=current_user.id, is_public=False)
        db.session.add(bank)
        db.session.flush()
        for i, q in enumerate(questions):
            qtext = (q.get('question_text') or '').strip()
            if not qtext:
                continue
            qtype = q.get('question_type') or 'multiple_choice'
            pts = float(q.get('points', 1))
            bq = QuestionBankQuestion(bank_id=bank.id, question_text=qtext, question_type=qtype, points=pts, order=i)
            db.session.add(bq)
            db.session.flush()
            opts = q.get('options') or []
            for j, o in enumerate(opts):
                db.session.add(QuestionBankOption(
                    question_id=bq.id,
                    option_text=(o.get('option_text') or '').strip(),
                    is_correct=bool(o.get('is_correct')),
                    order=j
                ))
        db.session.commit()
        return jsonify({'success': True, 'message': 'Question bank saved.', 'bank_id': bank.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


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

