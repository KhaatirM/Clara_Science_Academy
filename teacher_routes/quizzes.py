"""
Quiz management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, SchoolYear, QuizQuestion, QuizOption, QuizAnswer, QuizSection,
    QuizProgress, QuestionBank, QuestionBankQuestion, QuestionBankOption
)
from datetime import datetime
from utils.school_timezone import get_school_timezone_name
from teacher_routes.assignment_utils import (
    quiz_authoring_save_action,
    quiz_draft_default_due_date,
    count_quiz_questions_in_request,
)

bp = Blueprint('quizzes', __name__)

def _upsert_quiz_from_blocks(*, assignment, blocks):
    """
    Rebuild quiz sections/questions from ordered blocks.
    Blocks format matches `create_quiz_assignment.html`:
      - {type:'section', title: str}
      - {type:'question', question_text, question_type, points, options:[{option_text,is_correct}]}
    """
    # Delete existing graph in FK-safe order
    old_question_ids = [
        q.id for q in QuizQuestion.query.with_entities(QuizQuestion.id).filter_by(assignment_id=assignment.id).all()
    ]
    if old_question_ids:
        QuizAnswer.query.filter(QuizAnswer.question_id.in_(old_question_ids)).delete(synchronize_session=False)
        QuizOption.query.filter(QuizOption.question_id.in_(old_question_ids)).delete(synchronize_session=False)
    QuizProgress.query.filter_by(assignment_id=assignment.id).delete(synchronize_session=False)
    QuizQuestion.query.filter_by(assignment_id=assignment.id).delete(synchronize_session=False)
    QuizSection.query.filter_by(assignment_id=assignment.id).delete(synchronize_session=False)

    # Re-create sections/questions in order
    section_order = 0
    question_order = 0
    total_points = 0.0
    current_section_id = None
    for b in blocks or []:
        btype = (b.get('type') or '').strip().lower()
        if btype == 'section':
            title = (b.get('title') or '').strip() or f'Part {section_order + 1}'
            sec = QuizSection(assignment_id=assignment.id, title=title, order=section_order)
            db.session.add(sec)
            db.session.flush()
            current_section_id = sec.id
            section_order += 1
            continue
        if btype != 'question':
            continue

        qtext = (b.get('question_text') or '').strip()
        if not qtext:
            continue
        qtype = (b.get('question_type') or 'multiple_choice').strip()
        try:
            pts = float(b.get('points', 1.0))
        except (TypeError, ValueError):
            pts = 1.0
        if pts <= 0:
            pts = 1.0
        total_points += pts

        q = QuizQuestion(
            assignment_id=assignment.id,
            section_id=current_section_id,
            question_text=qtext,
            question_type=qtype,
            points=pts,
            order=question_order,
        )
        db.session.add(q)
        db.session.flush()

        opts = b.get('options') or []
        if qtype == 'multiple_choice':
            for i, o in enumerate(opts):
                text = (o.get('option_text') or '').strip()
                if not text:
                    continue
                db.session.add(QuizOption(
                    question_id=q.id,
                    option_text=text,
                    is_correct=bool(o.get('is_correct')),
                    order=i,
                ))
        elif qtype == 'true_false':
            # Ensure T/F options exist even if client didn't send options.
            is_true_correct = False
            for o in opts:
                if (o.get('option_text') or '').strip().lower() == 'true' and bool(o.get('is_correct')):
                    is_true_correct = True
                    break
            db.session.add(QuizOption(question_id=q.id, option_text='True', is_correct=is_true_correct, order=0))
            db.session.add(QuizOption(question_id=q.id, option_text='False', is_correct=(not is_true_correct), order=1))

        question_order += 1

    assignment.total_points = total_points if total_points > 0 else 100.0


@bp.route('/assignment/create/quiz/autosave', methods=['POST'])
@login_required
@teacher_required
def autosave_quiz_draft():
    """
    Autosave quiz draft (server-side) so work survives refresh/logout.
    """
    data = request.get_json(silent=True) or {}
    meta = data.get('meta') or {}
    blocks = data.get('blocks') or []
    assignment_id = meta.get('assignment_id')

    class_id = meta.get('class_id')
    if not class_id:
        # Can't draft without a class; still allow local storage fallback on client.
        return jsonify({'success': False, 'message': 'class_id_required'}), 400

    class_obj = Class.query.get(int(class_id))
    if not is_authorized_for_class(class_obj):
        return jsonify({'success': False, 'message': 'unauthorized'}), 403

    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        return jsonify({'success': False, 'message': 'no_active_school_year'}), 400

    title = (meta.get('title') or '').strip() or 'Untitled quiz (autosaved draft)'
    description = meta.get('description') or ''
    quarter = str((meta.get('quarter') or '').strip() or '1')
    due_date_str = (meta.get('due_date') or '').strip()
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M') if due_date_str else quiz_draft_default_due_date()
    except ValueError:
        due_date = quiz_draft_default_due_date()

    open_date_str = (meta.get('open_date') or '').strip()
    close_date_str = (meta.get('close_date') or '').strip()
    open_date = None
    close_date = None
    if open_date_str:
        try:
            open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            open_date = None
    if close_date_str:
        try:
            close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            close_date = None
    if not close_date:
        close_date = due_date

    assignment_context = (meta.get('assignment_context') or 'homework').strip() or 'homework'
    assignment_category = (meta.get('assignment_category') or '').strip() or None
    try:
        category_weight = float(meta.get('category_weight') or 0.0)
    except (TypeError, ValueError):
        category_weight = 0.0
    allow_extra_credit = bool(meta.get('allow_extra_credit'))
    try:
        max_extra_credit_points = float(meta.get('max_extra_credit_points') or 0.0)
    except (TypeError, ValueError):
        max_extra_credit_points = 0.0

    # Always keep drafts inactive until explicitly published.
    calculated_status = 'Inactive'

    if assignment_id:
        assignment = Assignment.query.get(int(assignment_id))
        if not assignment or assignment.assignment_type != 'quiz' or not is_authorized_for_class(assignment.class_info):
            return jsonify({'success': False, 'message': 'not_found'}), 404
        assignment.title = title
        assignment.description = description
        assignment.due_date = due_date
        assignment.open_date = open_date
        assignment.close_date = close_date
        assignment.quarter = quarter
        assignment.class_id = int(class_id)
        assignment.school_year_id = current_school_year.id
        assignment.status = calculated_status
        assignment.quiz_authoring_is_draft = True
        assignment.assignment_context = assignment_context
        assignment.assignment_category = assignment_category
        assignment.category_weight = category_weight
        assignment.allow_extra_credit = allow_extra_credit
        assignment.max_extra_credit_points = max_extra_credit_points if allow_extra_credit else 0.0
    else:
        assignment = Assignment(
            title=title,
            description=description,
            due_date=due_date,
            open_date=open_date,
            close_date=close_date,
            total_points=100.0,
            quarter=quarter,
            class_id=int(class_id),
            school_year_id=current_school_year.id,
            assignment_type='quiz',
            status=calculated_status,
            quiz_authoring_is_draft=True,
            assignment_context=assignment_context,
            assignment_category=assignment_category,
            category_weight=category_weight,
            allow_extra_credit=allow_extra_credit,
            max_extra_credit_points=max_extra_credit_points if allow_extra_credit else 0.0,
            created_by=current_user.id,
        )
        db.session.add(assignment)
        db.session.flush()

    _upsert_quiz_from_blocks(assignment=assignment, blocks=blocks)
    db.session.commit()
    return jsonify({'success': True, 'assignment_id': assignment.id})

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
        save_action = quiz_authoring_save_action(request.form)
        is_draft = save_action == 'draft'
        assignment_id = request.form.get('assignment_id', type=int)
        is_edit = bool(assignment_id)
        title = (request.form.get('title') or '').strip()
        class_id = request.form.get('class_id', type=int)
        description = request.form.get('description', '')
        due_date_str = (request.form.get('due_date') or '').strip()
        quarter = (request.form.get('quarter') or '').strip()
        assignment_context = request.form.get('assignment_context', 'homework')
        assignment_category = (request.form.get('assignment_category') or '').strip() or None
        category_weight = request.form.get('category_weight', type=float)
        if category_weight is None:
            category_weight = 0.0
        allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
        max_extra_credit_points = request.form.get('max_extra_credit_points', type=float) or 0.0

        def _redirect_back():
            rt = url_for('teacher.create_quiz_assignment')
            if is_edit:
                rt += f'?edit={assignment_id}'
            return redirect(rt)

        if is_draft:
            if not class_id:
                flash("Choose a class to save your draft.", "danger")
                return _redirect_back()
            title = title or 'Untitled quiz (draft)'
            quarter = quarter or '1'
            try:
                due_date = (
                    datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
                    if due_date_str
                    else quiz_draft_default_due_date()
                )
            except ValueError:
                due_date = quiz_draft_default_due_date()
        else:
            if not all([title, class_id, due_date_str, quarter]):
                flash("Please fill in all required fields.", "danger")
                return _redirect_back()
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid due date.", "danger")
                return _redirect_back()

        link_google_form = request.form.get('link_google_form') == 'on'
        if not is_draft and not link_google_form and count_quiz_questions_in_request(request.form) < 1:
            flash("Add at least one question before publishing, or use Save draft.", "warning")
            return _redirect_back()

        try:
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
            
            # Calculate status based on dates (drafts stay inactive until published)
            from teacher_routes.assignment_utils import calculate_assignment_status
            if is_draft:
                calculated_status = 'Inactive'
            else:
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
                existing.quiz_authoring_is_draft = is_draft
                existing.assignment_context = assignment_context
                existing.assignment_category = assignment_category
                existing.category_weight = float(category_weight or 0.0)
                existing.allow_extra_credit = allow_extra_credit
                existing.max_extra_credit_points = float(max_extra_credit_points or 0.0) if allow_extra_credit else 0.0
                new_assignment = existing
                # Delete old quiz graph in FK-safe order before rebuilding.
                old_question_ids = [
                    q.id for q in QuizQuestion.query.with_entities(QuizQuestion.id).filter_by(assignment_id=assignment_id).all()
                ]
                if old_question_ids:
                    QuizAnswer.query.filter(QuizAnswer.question_id.in_(old_question_ids)).delete(synchronize_session=False)
                    QuizOption.query.filter(QuizOption.question_id.in_(old_question_ids)).delete(synchronize_session=False)
                QuizProgress.query.filter_by(assignment_id=assignment_id).delete(synchronize_session=False)
                QuizQuestion.query.filter_by(assignment_id=assignment_id).delete(synchronize_session=False)
                QuizSection.query.filter_by(assignment_id=assignment_id).delete(synchronize_session=False)
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
                    quiz_authoring_is_draft=is_draft,
                    assignment_context=assignment_context,
                    assignment_category=assignment_category,
                    category_weight=float(category_weight or 0.0),
                    allow_extra_credit=allow_extra_credit,
                    max_extra_credit_points=float(max_extra_credit_points or 0.0) if allow_extra_credit else 0.0,
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
            if is_draft:
                flash(
                    'Draft saved. Open it again from Assignments & Grades when you are ready to continue.'
                    if is_edit
                    else 'Draft saved. You can finish and publish later from Assignments & Grades.',
                    'success',
                )
                return redirect(url_for('teacher.create_quiz_assignment') + f'?edit={new_assignment.id}')
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
    return render_template(
        'shared/create_quiz_assignment.html',
        classes=classes,
        teacher=teacher,
        assignment=assignment,
        quiz_data=quiz_data,
        question_banks_url=question_banks_url,
        save_to_bank_url=save_to_bank_url,
        quiz_drafts_enabled=True,
    )


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
    # Use silent=True so non-JSON POSTs return a clean 400 instead of raising 415 and becoming a 500.
    data = request.get_json(silent=True) or {}
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
    """Create or edit a discussion assignment"""
    from teacher_routes.assignment_utils import calculate_assignment_status, parse_discussion_description
    from .utils import get_teacher_or_admin, is_authorized_for_class
    from datetime import timezone

    edit_id = request.args.get('edit', type=int)
    assignment = None
    if edit_id:
        assignment = Assignment.query.get(edit_id)
        if not assignment or assignment.assignment_type != 'discussion':
            flash("Discussion assignment not found.", "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        if assignment.class_info and not is_authorized_for_class(assignment.class_info):
            flash("You are not authorized to edit this assignment.", "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))

    teacher = get_teacher_or_admin()
    if is_admin():
        classes = Class.query.filter_by(is_active=True).order_by(Class.name).all()
    elif teacher:
        classes = Class.query.filter_by(teacher_id=teacher.id, is_active=True).order_by(Class.name).all()
    else:
        classes = []

    class_id_param = request.args.get('class_id', type=int)
    class_obj = None
    if class_id_param:
        class_obj = Class.query.get(class_id_param)
        if class_obj and not is_authorized_for_class(class_obj):
            flash("You are not authorized to access this class.", "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    elif assignment:
        class_obj = assignment.class_info

    if request.method == 'POST':
        edit_id_form = request.form.get('edit_id', type=int)
        title = request.form.get('title', '').strip()
        class_id = request.form.get('class_id', type=int)
        discussion_prompt = request.form.get('discussion_prompt', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        quarter = request.form.get('quarter', '').strip()
        total_points = request.form.get('total_points', type=float) or 100.0
        assignment_context = request.form.get('assignment_context', 'homework')
        min_initial_posts = request.form.get('min_initial_posts', type=int) or 1
        min_replies = request.form.get('min_replies', type=int) or 2
        allow_student_edit_posts = request.form.get('allow_student_edit_posts') == 'on'
        use_rubric = request.form.get('use_rubric') == 'on'
        rubric_criteria = request.form.get('rubric_criteria', '').strip() if use_rubric else None
        open_date_str = request.form.get('open_date', '').strip()
        close_date_str = request.form.get('close_date', '').strip()

        if not all([title, class_id, discussion_prompt, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            prompt, instructions, rubric, mi, mr = parse_discussion_description(assignment.description) if assignment else ('', '', '', 1, 2)
            return render_template('shared/create_discussion_assignment.html', classes=classes, class_obj=class_obj, assignment=assignment,
                                 discussion_prompt=prompt, instructions=instructions, rubric_criteria=rubric, min_initial_posts=mi or 1, min_replies=mr or 2, teacher=teacher)

        class_obj = Class.query.get(class_id)
        if not class_obj or not is_authorized_for_class(class_obj):
            flash("You are not authorized to create assignments for this class.", "danger")
            return render_template('shared/create_discussion_assignment.html', classes=classes, class_obj=None, assignment=assignment, teacher=teacher)

        try:
            from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz

            tz_name = get_school_timezone_name()
            due_date = parse_form_datetime_as_school_tz(due_date_str, tz_name)
            if not due_date:
                flash("Invalid due date.", "danger")
                return render_template('shared/create_discussion_assignment.html', classes=classes, class_obj=class_obj)
            open_date = parse_form_datetime_as_school_tz(open_date_str, tz_name) if open_date_str else None
            close_date = parse_form_datetime_as_school_tz(close_date_str, tz_name) if close_date_str else None
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

            temp_assignment = type('obj', (object,), {
                'status': 'Active',
                'open_date': open_date,
                'close_date': close_date,
                'due_date': due_date
            })
            calculated_status = calculate_assignment_status(temp_assignment)

            if edit_id_form:
                existing = Assignment.query.get(edit_id_form)
                if existing and existing.assignment_type == 'discussion' and is_authorized_for_class(existing.class_info):
                    existing.title = title
                    existing.description = full_description
                    existing.due_date = due_date
                    existing.open_date = open_date
                    existing.close_date = close_date
                    existing.quarter = str(quarter)
                    existing.class_id = class_id
                    existing.status = calculated_status
                    existing.assignment_context = assignment_context
                    existing.total_points = total_points
                    existing.allow_student_edit_posts = allow_student_edit_posts
                    db.session.commit()
                    flash('Discussion assignment updated successfully!', 'success')
                    return redirect(url_for('teacher.assignments.view_assignment', assignment_id=existing.id))
                else:
                    flash("Discussion assignment not found or you are not authorized to edit it.", "danger")
                    return redirect(url_for('teacher.dashboard.assignments_and_grades'))

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
                created_by=current_user.id,
                allow_student_edit_posts=allow_student_edit_posts
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
    from .utils import get_current_quarter
    current_quarter = get_current_quarter()
    if assignment:
        prompt, instructions, rubric, min_initial_posts, min_replies = parse_discussion_description(assignment.description)
        class_obj = assignment.class_info
    else:
        prompt, instructions, rubric, min_initial_posts, min_replies = '', '', '', 1, 2
    return render_template('shared/create_discussion_assignment.html',
                         classes=classes,
                         teacher=teacher,
                         assignment=assignment,
                         class_obj=class_obj,
                         current_quarter=current_quarter,
                         discussion_prompt=prompt,
                         instructions=instructions,
                         rubric_criteria=rubric,
                         min_initial_posts=min_initial_posts,
                         min_replies=min_replies)

