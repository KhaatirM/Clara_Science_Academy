"""
Assignments routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Assignment, AssignmentAttachment, Grade, Submission, Student, Class, Enrollment, AssignmentExtension,
    AssignmentRedo, AssignmentReopening, QuizQuestion, QuizOption, QuizAnswer, QuizSection, DiscussionThread,
    DiscussionPost, GroupAssignment, TeacherStaff, SchoolYear, ExtensionRequest, RedoRequest,
    QuestionBank, QuestionBankQuestion, QuestionBankOption, Notification, User
)
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta, timezone, time
import os
import shutil
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
import json
from .utils import allowed_file, ALLOWED_EXTENSIONS, update_assignment_statuses, get_current_quarter
from teacher_routes.assignment_utils import is_assignment_open_for_student
from utils.grade_helpers import get_points_earned

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
    preselected_class_id = request.args.get('class_id', type=int)
    return render_template('shared/assignment_type_selector.html', preselected_class_id=preselected_class_id)



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
def _build_quiz_data_for_edit(assignment):
    """Build quiz_data dict (blocks with sections and questions) for template pre-fill."""
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


# Route: /assignment/create/quiz', methods=['GET', 'POST']
# Function: create_quiz_assignment
# ============================================================

@bp.route('/assignment/create/quiz', methods=['GET', 'POST'])
@login_required
@management_required
def create_quiz_assignment():
    """Create or edit a quiz assignment - management version"""
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
            redirect_target = url_for('management.create_quiz_assignment')
            if is_edit:
                redirect_target += f'?edit={assignment_id}'
            return redirect(redirect_target)
        
        try:
            from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz
            tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
            due_date = parse_form_datetime_as_school_tz(due_date_str, tz_name)
            if not due_date:
                raise ValueError("Invalid due date")
            
            # Parse open_date and close_date if provided (interpreted as school timezone)
            open_date_str = request.form.get('open_date', '').strip()
            close_date_str = request.form.get('close_date', '').strip()
            open_date = parse_form_datetime_as_school_tz(open_date_str, tz_name) if open_date_str else None
            close_date = parse_form_datetime_as_school_tz(close_date_str, tz_name) if close_date_str else None
            
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
            
            if is_edit:
                existing = Assignment.query.get(assignment_id)
                if not existing or existing.assignment_type != 'quiz':
                    flash("Quiz assignment not found or invalid.", "danger")
                    return redirect(url_for('management.create_quiz_assignment'))
                existing.title = title
                existing.description = description
                existing.due_date = due_date
                existing.open_date = open_date
                existing.close_date = close_date
                existing.quarter = str(quarter)
                existing.class_id = class_id
                existing.status = calculated_status
                existing.allow_save_and_continue = allow_save_and_continue
                existing.max_save_attempts = max_save_attempts
                existing.save_timeout_minutes = save_timeout_minutes
                existing.time_limit_minutes = time_limit_minutes
                existing.max_attempts = max_attempts
                existing.shuffle_questions = shuffle_questions
                existing.show_correct_answers = show_correct_answers
                existing.google_form_id = google_form_id
                existing.google_form_url = google_form_url if link_google_form else None
                existing.google_form_linked = link_google_form
                existing.assignment_context = assignment_context
                new_assignment = existing
                # Clean old quiz graph in FK-safe order before rebuilding questions.
                from models import QuizProgress
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
                # Fallback: no block_order (existing form behavior - all questions, no sections)
                question_ids = set()
                for key in request.form.keys():
                    if key.startswith('question_text_') and not key.endswith('[]'):
                        question_id = key.split('_')[-1]
                        question_ids.add(question_id)
                for question_id in sorted(question_ids, key=lambda x: int(x) if x.isdigit() else 999):
                    question_text = request.form.get(f'question_text_{question_id}', '').strip()
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

            # Update assignment total_points
            new_assignment.total_points = total_points if total_points > 0 else 100.0
            db.session.commit()
            flash('Quiz assignment updated successfully!' if is_edit else 'Quiz assignment created successfully!', 'success')
            return redirect(url_for('management.assignments_and_grades'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quiz assignment: {str(e)}', 'danger')
    
    # GET request - show form (create or edit)
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    assignment = None
    quiz_data = None
    edit_id = request.args.get('edit', type=int)
    if edit_id:
        assignment = Assignment.query.get(edit_id)
        if not assignment or assignment.assignment_type != 'quiz':
            flash("Quiz assignment not found.", "danger")
            return redirect(url_for('management.create_quiz_assignment'))
        quiz_data = _build_quiz_data_for_edit(assignment)
    question_banks_url = url_for('management.assignments.question_banks_json')
    save_to_bank_url = url_for('management.assignments.save_to_bank')
    return render_template('shared/create_quiz_assignment.html', classes=classes, current_quarter=current_quarter, assignment=assignment, quiz_data=quiz_data, question_banks_url=question_banks_url, save_to_bank_url=save_to_bank_url)


@bp.route('/api/question-banks')
@login_required
@management_required
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
@management_required
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


# ============================================================
# Route: /assignment/create/discussion', methods=['GET', 'POST']
# Function: create_discussion_assignment
# ============================================================

@bp.route('/assignment/create/discussion', methods=['GET', 'POST'])
@login_required
@management_required
def create_discussion_assignment():
    """Create or edit a discussion assignment - management version"""
    from teacher_routes.assignment_utils import calculate_assignment_status

    edit_id = request.args.get('edit', type=int)
    assignment = None
    if edit_id:
        assignment = Assignment.query.get(edit_id)
        if not assignment or assignment.assignment_type != 'discussion':
            flash("Discussion assignment not found.", "danger")
            return redirect(url_for('management.assignments_and_grades'))

    classes = Class.query.filter_by(is_active=True).order_by(Class.name).all()

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
            return render_template('shared/create_discussion_assignment.html', classes=classes, assignment=assignment, current_quarter=get_current_quarter())

        try:
            from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz
            tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
            due_date = parse_form_datetime_as_school_tz(due_date_str, tz_name)
            if not due_date:
                raise ValueError("Invalid due date")
            open_date = parse_form_datetime_as_school_tz(open_date_str, tz_name) if open_date_str else None
            close_date = parse_form_datetime_as_school_tz(close_date_str, tz_name) if close_date_str else None
            if not close_date:
                close_date = due_date

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
                if existing and existing.assignment_type == 'discussion':
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
                    return redirect(url_for('management.view_assignment', assignment_id=existing.id))
                else:
                    flash("Discussion assignment not found.", "danger")
                    return redirect(url_for('management.assignments_and_grades'))

            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return render_template('shared/create_discussion_assignment.html', classes=classes, assignment=assignment, current_quarter=get_current_quarter())

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
                created_by=current_user.id,
                allow_student_edit_posts=allow_student_edit_posts
            )
            db.session.add(new_assignment)
            db.session.commit()
            flash('Discussion assignment created successfully!', 'success')
            return redirect(url_for('management.assignments_and_grades'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error saving discussion assignment: {str(e)}', 'danger')

    current_quarter = get_current_quarter()
    if assignment:
        from teacher_routes.assignment_utils import parse_discussion_description
        prompt, instructions, rubric, min_initial_posts, min_replies = parse_discussion_description(assignment.description)
        class_obj = assignment.class_info
    else:
        prompt, instructions, rubric, min_initial_posts, min_replies = '', '', '', 1, 2
        class_obj = None
    return render_template('shared/create_discussion_assignment.html',
                         classes=classes,
                         current_quarter=current_quarter,
                         assignment=assignment,
                         class_obj=class_obj,
                         discussion_prompt=prompt if assignment else '',
                         instructions=instructions if assignment else '',
                         rubric_criteria=rubric if assignment else '',
                         min_initial_posts=min_initial_posts,
                         min_replies=min_replies)



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
    # Import at function start to avoid UnboundLocalError from inner-scope shadowing
    from models import Enrollment
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
            
            # Get pending extension request count and redo request count
            pending_extension_count = ExtensionRequest.query.filter_by(status='Pending').count()
            pending_redo_count = RedoRequest.query.filter_by(status='Pending').count()

            from management_routes.student_assistant_utils import count_pending_assistant_proposals_for_class
            pending_assistant_by_class = {}
            for class_obj in accessible_classes:
                if class_obj and hasattr(class_obj, 'id') and class_obj.id is not None:
                    pending_assistant_by_class[class_obj.id] = count_pending_assistant_proposals_for_class(class_obj.id)
            total_pending_assistant_proposals = sum(pending_assistant_by_class.values())
            
            return render_template('management/assignments_and_grades.html',
                                 accessible_classes=accessible_classes,
                                 class_assignments=class_assignments,
                                 unique_student_count=unique_student_count,
                                 selected_class=None,
                                 class_assignments_data=None,
                                 group_assignments=[],
                                 sorted_assignments=[],
                                 assignment_grades=None,
                                 sort_by=sort_by,
                                 sort_order=sort_order,
                                 view_mode=view_mode,
                                 user_role=user_role,
                                 show_class_selection=True,
                                 extension_request_count=pending_extension_count,
                                 redo_request_count=pending_redo_count,
                                 pending_assistant_by_class=pending_assistant_by_class,
                                 total_pending_assistant_proposals=total_pending_assistant_proposals)
        
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
                total_percentage_sum = 0
                graded_count = 0
                for assignment in assignments:
                    total_points = (assignment.total_points or 100.0) if hasattr(assignment, 'total_points') else 100.0
                    grades = Grade.query.filter_by(assignment_id=assignment.id).all()
                    grade_stats['total_submissions'] += len(grades)
                    if grades:
                        grade_stats['graded_assignments'] += 1
                        for grade in grades:
                            if grade.grade_data:
                                try:
                                    if isinstance(grade.grade_data, dict):
                                        grade_dict = grade.grade_data
                                    else:
                                        grade_dict = json.loads(grade.grade_data)
                                    if grade_dict.get('is_voided'):
                                        continue
                                    score_value = get_points_earned(grade_dict)
                                    if score_value is not None:
                                        try:
                                            points_float = float(score_value)
                                            pct = (points_float / total_points * 100) if total_points > 0 else 0
                                            total_percentage_sum += pct
                                            graded_count += 1
                                        except (ValueError, TypeError):
                                            continue
                                except (json.JSONDecodeError, TypeError):
                                    continue
                if graded_count > 0:
                    grade_stats['average_score'] = round(total_percentage_sum / graded_count, 1)
            
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
        sorted_assignments = []
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

                    # Get enrolled students for voided-student computation
                    _enrollments = Enrollment.query.filter_by(class_id=selected_class_id, is_active=True).all()
                    _enrolled_students = [e.student for e in _enrollments if e.student]
                    _enrolled_student_ids = {s.id for s in _enrolled_students}

                    # Combine individual and group assignments, sort by due_date (most recent first)
                    def _due_ts(d):
                        if d is None:
                            return 0
                        if hasattr(d, 'timestamp'):
                            return d.timestamp() if d.tzinfo is None else d.replace(tzinfo=None).timestamp()
                        from datetime import datetime as dt
                        from datetime import date as date_cls
                        return dt.combine(d, dt.min.time()).timestamp() if isinstance(d, date_cls) else 0
                    sorted_assignments = (
                        [('individual', a) for a in class_assignments] +
                        [('group', ga) for ga in group_assignments]
                    )
                    sorted_assignments.sort(key=lambda x: (x[1].due_date is None, -_due_ts(x[1].due_date)))

                    # Get enrolled students for voided-student name resolution
                    _enrollments = Enrollment.query.filter_by(class_id=selected_class_id, is_active=True).all()
                    _enrolled_students = [e.student for e in _enrollments if e and getattr(e, 'student', None)]

                # Get grade data for each individual assignment
                for assignment in class_assignments:
                    grades = Grade.query.filter_by(assignment_id=assignment.id).all()
                    # Actual submission count: students marked as submitted (not 'not_submitted')
                    total_submissions = Submission.query.filter_by(assignment_id=assignment.id).filter(
                        Submission.submission_type != 'not_submitted'
                    ).count()
                    
                    graded_grades = []
                    total_score = 0
                    for g in grades:
                        if g.is_voided:
                            continue
                        if g.grade_data is not None:
                            try:
                                if isinstance(g.grade_data, dict):
                                    grade_dict = g.grade_data
                                else:
                                    grade_dict = json.loads(g.grade_data)
                                if grade_dict.get('is_voided'):
                                    continue
                                score_val = get_points_earned(grade_dict)
                                if score_val is not None and str(score_val).strip() != '':
                                    graded_grades.append(grade_dict)
                                    try:
                                        total_score += float(score_val)
                                    except (ValueError, TypeError):
                                        continue
                            except (json.JSONDecodeError, TypeError):
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
                    
                    total_points = (assignment.total_points or 100.0) if getattr(assignment, 'total_points', None) else 100.0
                    avg_pct = round((total_score / len(graded_grades) / total_points * 100), 1) if graded_grades and total_points > 0 else 0
                    # Voided status: all voided (assignment level or all grades) vs partially voided
                    # Use enrolled count, not grade count: voiding creates grades for voided students only,
                    # so comparing to len(grades) incorrectly treats "2 voided of 3 enrolled" as all voided.
                    all_voided = assignment.status == 'Voided'
                    voided_grades = [g for g in grades if g.is_voided]
                    voided_count = len(voided_grades)
                    enrolled_count = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).count()
                    if not all_voided and enrolled_count > 0:
                        all_voided = voided_count == enrolled_count
                    partially_voided = not all_voided and voided_count > 0
                    voided_student_names = []
                    if partially_voided and selected_class:
                        enr = Enrollment.query.filter_by(class_id=selected_class.id, is_active=True).all()
                        for e in enr:
                            if e.student:
                                g = next((x for x in grades if x.student_id == e.student.id and x.is_voided), None)
                                if g:
                                    voided_student_names.append(f"{e.student.first_name} {e.student.last_name}")
                    assignment_grades[assignment.id] = {
                        'total_submissions': total_submissions,
                        'graded_count': len(graded_grades),
                        'average_score': avg_pct,
                        'type': 'individual',
                        'is_autogradeable': is_autogradeable,
                        'all_voided': all_voided,
                        'partially_voided': partially_voided,
                        'voided_count': voided_count,
                        'voided_student_names': voided_student_names,
                        'needs_grading': len(graded_grades) == 0
                    }
                
                # Get grade data for each group assignment
                for group_assignment in group_assignments:
                    from models import GroupGrade, GroupSubmission, StudentGroup, StudentGroupMember
                    group_grades = GroupGrade.query.filter_by(group_assignment_id=group_assignment.id).all()
                    # Count submissions: students with GroupGrade in_person/online + group uploads (each = group's members)
                    submission_student_ids = set()
                    for gg in group_grades:
                        if gg.grade_data and not gg.is_voided:
                            try:
                                gd = json.loads(gg.grade_data) if isinstance(gg.grade_data, str) else gg.grade_data
                                if gd.get('submission_type') in ('in_person', 'online'):
                                    submission_student_ids.add(gg.student_id)
                            except (json.JSONDecodeError, TypeError):
                                pass
                    for gs in GroupSubmission.query.filter_by(group_assignment_id=group_assignment.id).all():
                        if (gs.attachment_file_path or gs.attachment_filename) and gs.group_id:
                            for m in StudentGroupMember.query.filter_by(group_id=gs.group_id).all():
                                submission_student_ids.add(m.student_id)
                    total_group_submissions = len(submission_student_ids)
                    
                    graded_group_grades = []
                    total_score = 0
                    for gg in group_grades:
                        if gg.is_voided:
                            continue
                        if gg.grade_data is not None:
                            try:
                                if isinstance(gg.grade_data, dict):
                                    grade_dict = gg.grade_data
                                else:
                                    grade_dict = json.loads(gg.grade_data)
                                if grade_dict.get('is_voided'):
                                    continue
                                score_val = get_points_earned(grade_dict)
                                if score_val is not None and str(score_val).strip() != '':
                                    graded_group_grades.append(grade_dict)
                                    try:
                                        total_score += float(score_val)
                                    except (ValueError, TypeError):
                                        continue
                            except (json.JSONDecodeError, TypeError):
                                continue
                    
                    total_points_ga = (group_assignment.total_points or 100.0) if getattr(group_assignment, 'total_points', None) else 100.0
                    avg_pct_ga = round((total_score / len(graded_group_grades) / total_points_ga * 100), 1) if graded_group_grades and total_points_ga > 0 else 0
                    # Voided status for group assignments
                    # Use total applicable students (in assigned groups), not grade count - same bug as individual:
                    # voiding creates GroupGrade records for voided students only, so len(group_grades) is wrong.
                    ga_all_voided = group_assignment.status == 'Voided'
                    ga_voided_grades = [g for g in group_grades if g.is_voided]
                    ga_voided_count = len(ga_voided_grades)
                    ga_total_applicable = 0
                    try:
                        from models import StudentGroupMember, StudentGroup
                        sel = group_assignment.selected_group_ids
                        if sel:
                            ids = json.loads(sel) if isinstance(sel, str) else sel
                            ids = [int(x) for x in ids]
                            members = StudentGroupMember.query.join(StudentGroup).filter(
                                StudentGroup.id.in_(ids),
                                StudentGroup.class_id == group_assignment.class_id,
                                StudentGroup.is_active == True
                            ).all()
                        else:
                            members = StudentGroupMember.query.join(StudentGroup).filter(
                                StudentGroup.class_id == group_assignment.class_id,
                                StudentGroup.is_active == True
                            ).all()
                        ga_total_applicable = len({m.student_id for m in members if m.student_id})
                    except Exception:
                        ga_total_applicable = len(group_grades)  # fallback
                    if not ga_all_voided and ga_total_applicable > 0:
                        ga_all_voided = ga_voided_count == ga_total_applicable
                    ga_partially_voided = not ga_all_voided and ga_voided_count > 0
                    ga_voided_student_names = []
                    if ga_partially_voided and selected_class:
                        for gg in ga_voided_grades:
                            if gg.student:
                                ga_voided_student_names.append(f"{gg.student.first_name} {gg.student.last_name}")
                    ga_needs_grading = len(graded_group_grades) == 0
                    assignment_grades[f'group_{group_assignment.id}'] = {
                        'total_submissions': total_group_submissions,
                        'graded_count': len(graded_group_grades),
                        'average_score': avg_pct_ga,
                        'type': 'group',
                        'all_voided': ga_all_voided,
                        'partially_voided': ga_partially_voided,
                        'voided_count': ga_voided_count,
                        'voided_student_names': ga_voided_student_names,
                        'needs_grading': ga_needs_grading
                    }
            except (ValueError, TypeError, AttributeError) as e:
                # Handle any conversion errors gracefully
                selected_class = None
                pass
    
        # Get group_assignments and sorted_assignments if they exist (for passing to template)
        try:
            if 'group_assignments' not in locals():
                group_assignments = []
        except:
            group_assignments = []
        try:
            if 'sorted_assignments' not in locals():
                sorted_assignments = []
        except:
            sorted_assignments = []
        
        from datetime import date
        # Get pending extension request count and redo request count
        pending_extension_count = ExtensionRequest.query.filter_by(status='Pending').count()
        pending_redo_count = RedoRequest.query.filter_by(status='Pending').count()
        
        # Create combined assignments list for grades and table views
        class_assignments_data = list(class_assignments) if class_assignments else []
        
        # Get enrolled students and all assignments for any view when class is selected
        enrolled_students = []
        all_assignments = []
        table_student_grades = {}
        table_student_averages = {}
        
        if selected_class:
            try:
                enrollments = Enrollment.query.filter_by(class_id=selected_class.id, is_active=True).all()
                enrolled_students = [e.student for e in enrollments if e.student]
                # Combine regular and group assignments for table view (use sorted order)
                all_assignments = [item[1] for item in sorted_assignments] if sorted_assignments else list(class_assignments or []) + list(group_assignments or [])
                
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
                                    points_earned = get_points_earned(grade_data)
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
                                        points_earned = get_points_earned(grade_data)
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
                            # Only process valid numeric grades (include 0 - use explicit checks)
                            if grade is not None and grade != 'Not Graded' and grade != 'N/A' and grade != 'Not in Group' and grade != 'Not Assigned' and grade != 'No Group':
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
        
        from management_routes.student_assistant_utils import count_pending_assistant_proposals_for_class
        pending_assistant_count = (
            count_pending_assistant_proposals_for_class(selected_class.id) if selected_class else 0
        )
        pending_assistant_by_class = {}
        for class_obj in accessible_classes:
            if class_obj and hasattr(class_obj, 'id') and class_obj.id is not None:
                pending_assistant_by_class[class_obj.id] = count_pending_assistant_proposals_for_class(class_obj.id)
        total_pending_assistant_proposals = sum(pending_assistant_by_class.values())

        return render_template('management/assignments_and_grades.html',
                             accessible_classes=accessible_classes,
                             class_data=class_data,
                             selected_class=selected_class,
                             class_assignments=class_assignments,
                             class_assignments_data=class_assignments_data,
                             group_assignments=group_assignments,
                             sorted_assignments=sorted_assignments,
                             assignment_grades=assignment_grades,
                             class_filter=class_filter,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             view_mode=view_mode,
                             user_role=user_role,
                             show_class_selection=False,
                             today=date.today(),
                             extension_request_count=pending_extension_count,
                             redo_request_count=pending_redo_count,
                             pending_assistant_count=pending_assistant_count,
                             pending_assistant_by_class=pending_assistant_by_class,
                             total_pending_assistant_proposals=total_pending_assistant_proposals,
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
        title = request.form.get('title')
        description = request.form.get('description')
        # Support multiple classes (class_ids) or single class (class_id)
        class_ids = [int(x) for x in request.form.getlist('class_ids') if x]
        class_id = request.form.get('class_id', type=int)
        if class_ids:
            pass  # Use class_ids for multi-class
        elif class_id:
            class_ids = [class_id]  # Single class
        else:
            class_ids = []
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
        
        if not all([title, due_date_str, quarter]) or not class_ids:
            flash("Title, Class(es), Due Date, and Quarter are required.", "danger")
            return redirect(request.url)

        # Type assertion for due_date_str
        assert due_date_str is not None
        from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz
        tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
        due_date = parse_form_datetime_as_school_tz(due_date_str, tz_name)
        if not due_date:
            flash("Invalid due date.", "danger")
            return redirect(request.url)
        open_date_str = request.form.get('open_date', '').strip()
        close_date_str = request.form.get('close_date', '').strip()
        open_date = parse_form_datetime_as_school_tz(open_date_str, tz_name) if open_date_str else None
        close_date = parse_form_datetime_as_school_tz(close_date_str, tz_name) if close_date_str else None
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

        # Save uploaded files once (can only read request.files once)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        upload_dir = os.path.join(upload_folder, 'assignments')
        os.makedirs(upload_dir, exist_ok=True)
        files_to_save = request.files.getlist('assignment_files') or []
        if not files_to_save or not (files_to_save[0] and files_to_save[0].filename):
            single = request.files.get('assignment_file')
            if single and single.filename:
                files_to_save = [single]
        saved_file_data = []  # list of dicts: attachment_filename, attachment_original_filename, source_path, attachment_file_size, attachment_mime_type, sort_order
        for idx, file in enumerate(files_to_save):
            if not file or not file.filename:
                continue
            if not allowed_file(file.filename):
                flash(f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                return redirect(request.url)
            assert file.filename is not None
            filename = secure_filename(file.filename)
            unique_filename = f"assignment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}_{filename}"
            filepath = os.path.join(upload_dir, unique_filename)
            try:
                file.save(filepath)
                saved_file_data.append({
                    'attachment_filename': unique_filename,
                    'attachment_original_filename': filename,
                    'source_path': filepath,
                    'attachment_file_size': os.path.getsize(filepath),
                    'attachment_mime_type': file.content_type or None,
                    'sort_order': idx,
                })
            except Exception as e:
                flash(f'Error saving file: {str(e)}', 'danger')
                return redirect(request.url)

        try:
            created_count = 0
            for cid in class_ids:
                new_assignment = Assignment()
                new_assignment.title = title
                new_assignment.description = description
                new_assignment.due_date = due_date
                new_assignment.open_date = open_date
                new_assignment.close_date = close_date
                new_assignment.class_id = cid
                new_assignment.school_year_id = current_school_year.id
                new_assignment.quarter = str(quarter)
                new_assignment.status = status
                new_assignment.assignment_context = assignment_context
                new_assignment.assignment_type = 'pdf_paper'
                new_assignment.total_points = total_points
                new_assignment.allow_extra_credit = allow_extra_credit
                new_assignment.max_extra_credit_points = max_extra_credit_points if allow_extra_credit else 0.0
                new_assignment.late_penalty_enabled = late_penalty_enabled
                new_assignment.late_penalty_per_day = late_penalty_per_day if late_penalty_enabled else 0.0
                new_assignment.late_penalty_max_days = late_penalty_max_days if late_penalty_enabled else 0
                new_assignment.assignment_category = assignment_category
                new_assignment.category_weight = category_weight
                new_assignment.created_by = current_user.id
                db.session.add(new_assignment)
                db.session.flush()

                for att_idx, att_data in enumerate(saved_file_data):
                    dest_filename = f"assignment_{cid}_{new_assignment.id}_{att_idx}_{att_data['attachment_original_filename']}"
                    dest_path = os.path.join(upload_dir, dest_filename)
                    shutil.copy2(att_data['source_path'], dest_path)
                    # Store relative path (assignments/filename) so files resolve after redeploys
                    attachment_file_path_stored = os.path.join('assignments', dest_filename)
                    att = AssignmentAttachment(
                        assignment_id=new_assignment.id,
                        attachment_filename=dest_filename,
                        attachment_original_filename=att_data['attachment_original_filename'],
                        attachment_file_path=attachment_file_path_stored,
                        attachment_file_size=att_data['attachment_file_size'],
                        attachment_mime_type=att_data['attachment_mime_type'],
                        sort_order=att_data['sort_order'],
                    )
                    db.session.add(att)
                    if att_idx == 0:
                        new_assignment.attachment_filename = dest_filename
                        new_assignment.attachment_original_filename = att_data['attachment_original_filename']
                        new_assignment.attachment_file_path = attachment_file_path_stored
                        new_assignment.attachment_file_size = att_data['attachment_file_size']
                        new_assignment.attachment_mime_type = att_data['attachment_mime_type']
                created_count += 1

            db.session.commit()
            flash(f'Assignment created successfully for {created_count} class{"es" if created_count > 1 else ""}.', 'success')
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
    # For in-class: default due date = today at 4:00 PM EST
    default_due_date = None
    in_class_due_date_str = None  # Always compute for JS (when user switches context)
    try:
        est = ZoneInfo('America/New_York')
        now_est = datetime.now(est)
        today_est = now_est.date()
        in_class_dt = datetime.combine(today_est, time(16, 0))
        in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
        if context == 'in-class':
            default_due_date = in_class_dt
    except Exception:
        in_class_dt = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
        if context == 'in-class':
            default_due_date = in_class_dt
    return render_template('shared/add_assignment.html', classes=classes, current_quarter=current_quarter, context=context, default_due_date=default_due_date, in_class_due_date_str=in_class_due_date_str)




# ============================================================
# Route: /grade/assignment/<int:assignment_id>', methods=['GET', 'POST']
# Function: grade_assignment
# ============================================================

def _save_single_student_grade(assignment_id, student_id):
    """Helper: save a single student's grade. Used by AJAX Speed Grader."""
    assignment = Assignment.query.get_or_404(assignment_id)
    student = Student.query.get_or_404(student_id)
    enrollment = Enrollment.query.filter_by(
        class_id=assignment.class_id, student_id=student_id, is_active=True
    ).first()
    if not enrollment:
        return None, 'Student not in class'

    score_val = request.form.get('score', request.json.get('score') if request.is_json else None)
    score_raw = str(score_val).strip() if score_val is not None else ''
    comment = request.form.get('comment', request.json.get('comment', '')) or ''
    submission_type = request.form.get('submission_type', request.json.get('submission_type', '')) or ''
    notes_type = request.form.get('submission_notes_type', request.json.get('submission_notes_type', 'On-Time')) or 'On-Time'
    notes_other = request.form.get('submission_notes', request.json.get('submission_notes', '')) or ''
    submission_notes = notes_other if notes_type == 'Other' else notes_type

    total_points = assignment.total_points if assignment.total_points else 100.0

    teacher = TeacherStaff.query.get(current_user.teacher_staff_id) if current_user.teacher_staff_id else None
    if submission_type:
        sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
        if submission_type in ['in_person', 'online']:
            if sub:
                sub.submission_type = submission_type
                sub.submission_notes = submission_notes
                sub.marked_by = teacher.id if teacher else None
                sub.marked_at = datetime.utcnow()
            else:
                sub = Submission(
                    student_id=student_id, assignment_id=assignment_id,
                    submission_type=submission_type, submission_notes=submission_notes,
                    marked_by=teacher.id if teacher else None,
                    marked_at=datetime.utcnow(), submitted_at=datetime.utcnow(), file_path=None
                )
                db.session.add(sub)
        elif submission_type == 'not_submitted' and sub:
            db.session.delete(sub)

    existing_grade = Grade.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
    if existing_grade and existing_grade.is_voided:
        return True, 'Voided'

    if score_raw == '':
        if existing_grade:
            db.session.delete(existing_grade)
        db.session.commit()
        return True, 'Cleared'

    try:
        points_earned = float(score_raw)
    except (ValueError, TypeError):
        return False, 'Invalid score'

    percentage = (points_earned / total_points * 100) if total_points > 0 else 0
    grade_data = json.dumps({
        'score': points_earned, 'points_earned': points_earned,
        'total_points': total_points, 'max_score': total_points,
        'percentage': round(percentage, 2), 'comment': comment, 'feedback': comment,
        'graded_at': datetime.utcnow().isoformat()
    })

    if existing_grade:
        existing_grade.grade_data = grade_data
        existing_grade.graded_at = datetime.utcnow()
    else:
        grade = Grade(student_id=student_id, assignment_id=assignment_id, grade_data=grade_data, graded_at=datetime.utcnow())
        db.session.add(grade)
        sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
        if not sub and points_earned > 0:
            sub = Submission(
                student_id=student_id, assignment_id=assignment_id,
                submission_type='in_person', submission_notes='Auto-marked: grade entered',
                marked_by=teacher.id if teacher else None,
                marked_at=datetime.utcnow(), submitted_at=datetime.utcnow(), file_path=None
            )
            db.session.add(sub)

    db.session.commit()
    return True, 'Saved'


def save_student_grade(assignment_id, student_id):
    """AJAX endpoint for Speed Grader - save a single student's grade."""
    try:
        ok, msg = _save_single_student_grade(assignment_id, student_id)
        if ok:
            return jsonify({'success': True, 'message': msg})
        return jsonify({'success': False, 'error': msg}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


def send_reminder(assignment_id):
    """Send deadline reminder to selected students (from grading page bulk action)."""
    assignment = Assignment.query.get_or_404(assignment_id)
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to send reminders.", "danger")
        return redirect(url_for('management.assignments_and_grades'))

    reminder_type = request.form.get('reminder_type')
    student_ids = request.form.getlist('student_ids')
    custom_message = request.form.get('custom_message', '').strip()
    redirect_to = request.form.get('next') or request.form.get('redirect_url')

    try:
        if reminder_type == 'all':
            enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
            student_ids = [str(e.student_id) for e in enrollments if e.student_id]

        if not student_ids:
            flash("No students selected to send reminder to.", "warning")
            return redirect(redirect_to or url_for('management.grade_assignment', assignment_id=assignment_id))

        default_msg = f"Don't forget! Assignment '{assignment.title}' is due on {assignment.due_date.strftime('%b %d, %Y at %I:%M %p')}."
        msg = custom_message or default_msg

        for student_id in student_ids:
            user = User.query.filter_by(student_id=int(student_id)).first()
            if user:
                n = Notification(user_id=user.id, type='deadline_reminder', title=f"Reminder: {assignment.title}", message=msg)
                db.session.add(n)

        db.session.commit()
        flash(f"Reminder sent to {len(student_ids)} student(s) successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error sending reminder: {str(e)}", "danger")

    return redirect(redirect_to or url_for('management.grade_assignment', assignment_id=assignment_id))


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
                # Collect user IDs for grade-update digest (one notification per student after save)
                graded_user_ids = []
                for student in students:
                    score = request.form.get(f'score_{student.id}')
                    comment = request.form.get(f'comment_{student.id}')
                    submission_type = request.form.get(f'submission_type_{student.id}')
                    notes_type = request.form.get(f'submission_notes_type_{student.id}', 'On-Time')
                    notes_other = request.form.get(f'submission_notes_{student.id}', '').strip()
                    submission_notes = notes_other if notes_type == 'Other' else notes_type
                    
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
                    
                    # Always process grade - blank/empty means 0 and not submitted
                    try:
                        points_earned = float(score) if (score is not None and str(score).strip()) else 0.0
                    except (ValueError, TypeError):
                        points_earned = 0.0

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

                    # Only auto-create in_person submission when score > 0 (blank = 0 and not submitted)
                    if points_earned > 0:
                        submission = Submission.query.filter_by(
                            student_id=student.id,
                            assignment_id=assignment_id
                        ).first()
                        if not submission:
                            submission = Submission(
                                student_id=student.id,
                                assignment_id=assignment_id,
                                submission_type='in_person',
                                submission_notes='Auto-marked: grade entered',
                                marked_by=teacher.id if teacher else None,
                                marked_at=datetime.utcnow(),
                                submitted_at=datetime.utcnow(),
                                file_path=None,
                            )
                            db.session.add(submission)

                    # Queue for digest notification (one per student after commit)
                    if student.user and points_earned > 0:
                        graded_user_ids.append(student.user.id)
                
                db.session.commit()
                if graded_user_ids:
                    from app import create_grade_update_digest
                    create_grade_update_digest(
                        graded_user_ids,
                        assignment_title=assignment.title,
                        link=url_for('student.student_grades')
                    )
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
            quiz_questions = QuizQuestion.query.options(
                joinedload(QuizQuestion.options),
                joinedload(QuizQuestion.section)
            ).filter_by(assignment_id=assignment_id).order_by(QuizQuestion.order).all()
            
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
# Route: /assignment/<int:assignment_id>/center
# Function: assignment_command_center (tabbed hub - one page for View / Grade / Stats)
# ============================================================

@bp.route('/assignment/<int:assignment_id>/center')
@login_required
@management_required
def assignment_command_center(assignment_id):
    """Single command-center page for an assignment: Overview, Grade, Statistics in one place."""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_info = assignment.class_info if assignment.class_id else None
    submission_count = Submission.query.filter_by(assignment_id=assignment_id).filter(
        Submission.submission_type != 'not_submitted'
    ).count()
    graded_count = Grade.query.filter_by(assignment_id=assignment_id).filter(
        Grade.is_voided == False,
        Grade.grade_data != None,
        Grade.grade_data != ''
    ).count()
    return render_template(
        'management/assignment_command_center.html',
        assignment=assignment,
        class_info=class_info,
        submission_count=submission_count,
        graded_count=graded_count,
    )


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
            from models import DiscussionThread, DiscussionPost, Student
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

        # Statistics payload for view page
        total_students = Enrollment.query.filter_by(
            class_id=assignment.class_id,
            is_active=True
        ).count() if assignment.class_id else 0

        non_voided_grades = Grade.query.filter_by(
            assignment_id=assignment_id,
            is_voided=False
        ).all()
        graded_count = len(non_voided_grades)

        assignment_points = 0
        if hasattr(assignment, 'total_points') and assignment.total_points:
            assignment_points = assignment.total_points
        elif hasattr(assignment, 'points') and assignment.points:
            assignment_points = assignment.points
        assignment_points = float(assignment_points or 0)

        average_score = None
        if graded_count > 0:
            total_percentage = 0.0
            pct_count = 0
            for grade in non_voided_grades:
                try:
                    if not grade.grade_data:
                        continue
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
                    pct_count += 1
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
            if pct_count > 0:
                average_score = round(total_percentage / pct_count, 1)

        submission_rate = round((total_submissions_count / total_students * 100) if total_students > 0 else 0, 1)
        submission_rate = min(submission_rate, 100.0)
        grading_rate = round((graded_count / total_students * 100) if total_students > 0 else 0, 1)
        pending_count = max(total_students - graded_count, 0)
        
        # Get current date for status calculations
        today = datetime.now().date()
        
        # Get voided grades for the unvoid modal
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
                             total_students=total_students,
                             graded_count=graded_count,
                             average_score=average_score,
                             submission_rate=submission_rate,
                             grading_rate=grading_rate,
                             pending_count=pending_count,
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
# Route: /discussion/thread/<int:thread_id>
# Function: view_discussion_thread (for teachers/admins)
# ============================================================

@bp.route('/discussion/thread/<int:thread_id>')
@login_required
@management_required
def view_discussion_thread(thread_id):
    """View a discussion thread (for Directors and School Administrators)"""
    thread = DiscussionThread.query.get_or_404(thread_id)
    assignment = thread.assignment
    if not assignment or assignment.assignment_type != 'discussion':
        flash("Discussion thread not found.", "danger")
        return redirect(url_for('management.assignments_and_grades'))
    posts = DiscussionPost.query.filter_by(thread_id=thread_id).order_by(
        DiscussionPost.created_at.asc()
    ).all()
    back_url = url_for('management.view_assignment', assignment_id=assignment.id)
    return render_template('shared/view_discussion_thread.html',
                         assignment=assignment,
                         thread=thread,
                         posts=posts,
                         back_url=back_url,
                         show_reply_form=False)


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

    # Quiz and discussion assignments use different edit flows - redirect to avoid errors
    if assignment.assignment_type == 'quiz':
        flash("Use the quiz editor to edit this assignment.", "info")
        return redirect(url_for('management.create_quiz_assignment') + f'?edit={assignment_id}')
    if assignment.assignment_type == 'discussion':
        return redirect(url_for('management.create_discussion_assignment') + f'?edit={assignment_id}')
    
    # Authorization check - Directors and School Administrators can edit any assignment
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('management.assignments_and_grades'))

    if not class_obj:
        flash("Assignment class information not found. Cannot edit.", "danger")
        return redirect(url_for('management.assignments_and_grades'))
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
        assignment_context = request.form.get('assignment_context', 'homework')
        assignment_category = request.form.get('assignment_category', '').strip() or None
        category_weight = request.form.get('category_weight', type=float)
        if category_weight is None:
            category_weight = 0.0
        total_points = request.form.get('total_points', type=float)
        status_revert_enabled = request.form.get('status_revert_enabled') == '1'
        status_override_until_str = request.form.get('status_override_until', '').strip()
        
        if not all([title, due_date_str, quarter]):
            flash('Title, Due Date, and Quarter are required.', 'danger')
            return redirect(request.url)
        
        if total_points is None or total_points <= 0:
            total_points = 100.0
        
        # Validate status
        valid_statuses = ['Active', 'Inactive', 'Upcoming', 'Voided']
        if status not in valid_statuses:
            flash('Invalid assignment status.', 'danger')
            return redirect(request.url)
        
        try:
            from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz
            tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
            due_date = parse_form_datetime_as_school_tz(due_date_str, tz_name)
            if not due_date:
                flash("Invalid due date.", "danger")
                return redirect(request.url)

            # Update assignment
            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.quarter = str(quarter)  # Store as string to match model definition
            assignment.status = status
            assignment.assignment_context = assignment_context
            assignment.assignment_category = assignment_category
            assignment.category_weight = category_weight
            assignment.total_points = total_points
            
            # Status override: when "revert after" is set, lock status until that datetime
            if status_revert_enabled and status_override_until_str:
                try:
                    override_until = parse_form_datetime_as_school_tz(status_override_until_str, tz_name)
                    if override_until:
                        assignment.status_override = status
                        assignment.status_override_until = override_until
                    else:
                        assignment.status_override = None
                        assignment.status_override_until = None
                except (ValueError, TypeError):
                    assignment.status_override = None
                    assignment.status_override_until = None
            else:
                assignment.status_override = None
                assignment.status_override_until = None
            
            # Handle file upload(s) - multiple (assignment_files) or single (assignment_file)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            upload_dir = os.path.join(upload_folder, 'assignments')
            files_to_save = request.files.getlist('assignment_files') or []
            if not files_to_save or not (files_to_save[0] and files_to_save[0].filename):
                single = request.files.get('assignment_file')
                if single and single.filename:
                    files_to_save = [single]
            if files_to_save:
                os.makedirs(upload_dir, exist_ok=True)
                # Replace existing attachments with new uploads
                AssignmentAttachment.query.filter_by(assignment_id=assignment.id).delete()
                for idx, file in enumerate(files_to_save):
                    if not file or not file.filename:
                        continue
                    if not allowed_file(file.filename):
                        flash(f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                        db.session.rollback()
                        return redirect(request.url)
                    filename = secure_filename(file.filename)
                    unique_filename = f"assignment_{assignment.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}_{filename}"
                    filepath = os.path.join(upload_dir, unique_filename)
                    try:
                        file.save(filepath)
                        # Store relative path (assignments/filename) so files resolve after redeploys
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
                    except Exception as e:
                        flash(f'Error saving file: {str(e)}', 'danger')
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
            QuizQuestion, QuizProgress, QuizSection, DiscussionThread, DiscussionPost, QuizAnswer, QuizOption,
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
        
        # 1. Delete quiz answers/options first (they reference quiz questions)
        quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).all()
        for question in quiz_questions:
            QuizAnswer.query.filter_by(question_id=question.id).delete()
            QuizOption.query.filter_by(question_id=question.id).delete()
        
        # 2. Delete quiz progress before questions (progress can reference current_question_id)
        QuizProgress.query.filter_by(assignment_id=assignment_id).delete()
        
        # 3. Delete quiz questions (they reference assignments and sections)
        QuizQuestion.query.filter_by(assignment_id=assignment_id).delete()
        
        # 4. Delete quiz sections (they reference assignments)
        QuizSection.query.filter_by(assignment_id=assignment_id).delete()
        
        # 5. Delete discussion threads and posts
        discussion_threads = DiscussionThread.query.filter_by(assignment_id=assignment_id).all()
        for thread in discussion_threads:
            # Delete posts first (they reference threads)
            DiscussionPost.query.filter_by(thread_id=thread.id).delete()
        DiscussionThread.query.filter_by(assignment_id=assignment_id).delete()
        
        # 6. Delete grades (they reference assignments)
        Grade.query.filter_by(assignment_id=assignment_id).delete()
        
        # 7. Delete submissions (they reference assignments)
        Submission.query.filter_by(assignment_id=assignment_id).delete()
        
        # 8. Delete extensions (they reference assignments)
        AssignmentExtension.query.filter_by(assignment_id=assignment_id).delete()
        
        # Delete assignment attachment files (multiple and legacy)
        for att in AssignmentAttachment.query.filter_by(assignment_id=assignment_id).all():
            if att.attachment_file_path and os.path.exists(att.attachment_file_path):
                try:
                    os.remove(att.attachment_file_path)
                except OSError:
                    pass
            elif att.attachment_filename:
                for p in [os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments', att.attachment_filename),
                          os.path.join(current_app.config['UPLOAD_FOLDER'], att.attachment_filename)]:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass
                        break
        AssignmentAttachment.query.filter_by(assignment_id=assignment_id).delete()
        
        # Delete the legacy assignment file if it exists
        if attachment_filename:
            for filepath in [os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments', attachment_filename),
                             os.path.join(current_app.config['UPLOAD_FOLDER'], attachment_filename)]:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                    break
        
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
    letter_grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
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
                    letter_grades['E'] += 1
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
    letter_grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
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
                    letter_grades['E'] += 1
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
def void_group_assignment(assignment_id):
    """Void a group assignment for all groups, specific groups, or specific students. Teachers and admins."""
    from teacher_routes.utils import teacher_or_management_for_group_assignment
    return teacher_or_management_for_group_assignment(_void_group_assignment_impl)(assignment_id)


def _void_group_assignment_impl(assignment_id):
    """Implementation of void group assignment."""
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
                            group_id=group.id,
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
                                group_id=group.id,
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
                            group_id=student_group.id,
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
def unvoid_group_assignment(assignment_id):
    """Unvoid a group assignment - restore all voided grades. Teachers and admins."""
    from teacher_routes.utils import teacher_or_management_for_group_assignment
    return teacher_or_management_for_group_assignment(_unvoid_group_assignment_impl)(assignment_id)


def _unvoid_group_assignment_impl(assignment_id):
    """Implementation of unvoid group assignment."""
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
    
    # Only allow redos for PDF/Paper assignments (include pdf_paper - used when creating new PDF/Paper assignments)
    if assignment.assignment_type not in ['PDF', 'Paper', 'pdf', 'paper', 'pdf_paper']:
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
            from app import create_notification
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
# Route: /grant-redo-from-request/<int:request_id>', methods=['POST']
# Function: grant_redo_from_request
# ============================================================

@bp.route('/grant-redo-from-request/<int:request_id>', methods=['POST'])
@login_required
def grant_redo_from_request(request_id):
    """Grant redo from a student's redo request (inactive assignment)"""
    from models import RedoRequest

    req = RedoRequest.query.get_or_404(request_id)
    if req.status != 'Pending':
        return jsonify({'success': False, 'message': 'This request has already been reviewed.'})

    assignment = Assignment.query.get_or_404(req.assignment_id)

    # Authorization - same as grant_assignment_redo
    from decorators import is_teacher_role
    from models import class_additional_teachers, class_substitute_teachers

    is_teacher = is_teacher_role(current_user.role)
    is_admin = current_user.role in ['Director', 'School Administrator']

    if is_teacher:
        if not current_user.teacher_staff_id:
            return jsonify({'success': False, 'message': 'Teacher record not found.'})
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        class_obj = assignment.class_info
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class not found.'})
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
        return jsonify({'success': False, 'message': 'You are not authorized.'})

    redo_deadline_str = request.form.get('redo_deadline')
    if not redo_deadline_str:
        return jsonify({'success': False, 'message': 'Please provide a redo deadline.'})

    try:
        redo_deadline = datetime.strptime(redo_deadline_str, '%Y-%m-%d')
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id) if current_user.teacher_staff_id else None

        submission = Submission.query.filter_by(
            student_id=req.student_id,
            assignment_id=req.assignment_id
        ).first()
        has_submitted = submission is not None and submission.submission_type != 'not_submitted'

        if has_submitted:
            existing = AssignmentRedo.query.filter_by(
                assignment_id=req.assignment_id,
                student_id=req.student_id
            ).first()
            if existing:
                req.status = 'Approved'
                req.reviewed_at = datetime.utcnow()
                req.reviewed_by = teacher.id if teacher else None
                db.session.commit()
                return jsonify({'success': True, 'message': 'Redo already granted for this student.'})

            grade = Grade.query.filter_by(student_id=req.student_id, assignment_id=req.assignment_id).first()
            orig_grade = None
            if grade and grade.grade_data:
                try:
                    gd = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                    orig_grade = gd.get('score') or gd.get('points_earned')
                except (TypeError, json.JSONDecodeError):
                    pass

            redo_rec = AssignmentRedo(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
                granted_by=teacher.id if teacher else None,
                redo_deadline=redo_deadline,
                reason=req.reason or 'Granted from redo request',
                original_grade=orig_grade
            )
            db.session.add(redo_rec)
        else:
            existing = AssignmentReopening.query.filter_by(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
                is_active=True
            ).first()
            if existing:
                req.status = 'Approved'
                req.reviewed_at = datetime.utcnow()
                req.reviewed_by = teacher.id if teacher else None
                db.session.commit()
                return jsonify({'success': True, 'message': 'Reopening already granted for this student.'})

            reopening = AssignmentReopening(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
                reopened_by=teacher.id if teacher else None,
                is_active=True,
                additional_attempts=0
            )
            db.session.add(reopening)

        req.status = 'Approved'
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = teacher.id if teacher else None
        db.session.commit()

        # Notify student
        if req.student and req.student.user:
            from app import create_notification
            create_notification(
                user_id=req.student.user.id,
                notification_type='assignment',
                title=f'Redo Granted: {assignment.title}',
                message=f'Your teacher granted a redo for "{assignment.title}". New deadline: {redo_deadline.strftime("%m/%d/%Y")}.',
                link=url_for('student.student_assignments')
            )

        return jsonify({'success': True, 'message': 'Redo granted successfully. The student has been notified.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# Route: /reject-redo-request/<int:request_id>', methods=['POST']
# ============================================================

@bp.route('/reject-redo-request/<int:request_id>', methods=['POST'])
@login_required
def reject_redo_request(request_id):
    """Reject a student's redo request"""
    from models import RedoRequest

    req = RedoRequest.query.get_or_404(request_id)
    if req.status != 'Pending':
        return jsonify({'success': False, 'message': 'This request has already been reviewed.'})

    assignment = Assignment.query.get_or_404(req.assignment_id)
    from decorators import is_teacher_role
    from models import class_additional_teachers, class_substitute_teachers

    is_teacher = is_teacher_role(current_user.role)
    is_admin = current_user.role in ['Director', 'School Administrator']

    if is_teacher:
        if not current_user.teacher_staff_id:
            return jsonify({'success': False, 'message': 'Teacher record not found.'})
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        class_obj = assignment.class_info
        if not class_obj:
            return jsonify({'success': False, 'message': 'Assignment class not found.'})
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
            return jsonify({'success': False, 'message': 'You can only act on requests for your own classes.'})
    elif not is_admin:
        return jsonify({'success': False, 'message': 'You are not authorized.'})

    try:
        req.status = 'Rejected'
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = TeacherStaff.query.get(current_user.teacher_staff_id).id if current_user.teacher_staff_id else None
        db.session.commit()
        return jsonify({'success': True, 'message': 'Redo request rejected.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


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
    
    # Accept both form data and JSON (some callers use JSON)
    new_status = request.form.get('status')
    if new_status is None and request.is_json:
        data = request.get_json(silent=True) or {}
        new_status = data.get('status')
    
    # Validate status
    valid_statuses = ['Active', 'Inactive', 'Voided']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid status selected.'})
    
    try:
        assignment.status = new_status
        # When reopening (Inactive -> Active): extend close_date if it's in the past (or set it if missing)
        # so update_assignment_statuses() won't immediately revert the status
        if new_status == 'Active':
            now = datetime.now(timezone.utc)
            need_extend = False
            if assignment.close_date:
                close_dt = assignment.close_date
                if hasattr(close_dt, 'tzinfo') and close_dt.tzinfo is None:
                    close_dt = close_dt.replace(tzinfo=timezone.utc)
                need_extend = close_dt < now
            else:
                need_extend = True  # No close_date - set one so it stays open
            if need_extend:
                import pytz
                tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
                school_tz = pytz.timezone(tz_name)
                end_of_today = datetime.now(school_tz).replace(hour=23, minute=59, second=59, microsecond=999999)
                assignment.close_date = end_of_today.astimezone(pytz.UTC)
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
# Route: /group-assignment/<int:assignment_id>/extensions
# Function: admin_grant_group_extensions
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/extensions')
@login_required
def admin_grant_group_extensions(assignment_id):
    """View and manage extensions for a group assignment - Teachers and admins."""
    from models import GroupAssignment, GroupAssignmentExtension, StudentGroupMember
    from teacher_routes.utils import teacher_or_management_for_group_assignment

    # Auth check via decorator logic
    if current_user.role not in ['Director', 'School Administrator']:
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        from teacher_routes.utils import is_authorized_for_class
        if not is_authorized_for_class(group_assignment.class_info):
            flash("You are not authorized to manage extensions for this assignment.", "danger")
            return redirect(url_for('teacher.assignments.view_group_assignment', assignment_id=assignment_id))

    try:
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        class_obj = group_assignment.class_info

        # Get existing extensions for this group assignment
        extensions = GroupAssignmentExtension.query.filter_by(
            group_assignment_id=assignment_id, is_active=True
        ).all()

        # Get students in groups for this assignment
        from models import StudentGroup
        if group_assignment.selected_group_ids:
            try:
                selected_ids = json.loads(group_assignment.selected_group_ids) if isinstance(group_assignment.selected_group_ids, str) else group_assignment.selected_group_ids
                groups = StudentGroup.query.filter(StudentGroup.class_id == group_assignment.class_id, StudentGroup.is_active == True, StudentGroup.id.in_(selected_ids)).all()
            except Exception:
                groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
        else:
            groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()

        students = []
        for group in groups:
            for member in StudentGroupMember.query.filter_by(group_id=group.id).all():
                if member.student and member.student not in students:
                    students.append(member.student)

        return render_template('management/admin_grant_group_extensions.html',
                             group_assignment=group_assignment,
                             assignment=group_assignment,
                             class_obj=class_obj,
                             extensions=extensions,
                             students=students)
    except Exception as e:
        print(f"Error viewing group extensions: {e}")
        import traceback
        traceback.print_exc()
        flash('Error accessing extensions management.', 'error')
        return redirect(url_for('teacher.assignments.view_group_assignment', assignment_id=assignment_id))


@bp.route('/group-assignment/<int:assignment_id>/grant-extensions', methods=['POST'])
@login_required
def grant_group_extensions(assignment_id):
    """Grant extensions for a group assignment - Teachers and admins."""
    from models import GroupAssignment, GroupAssignmentExtension
    from teacher_routes.utils import is_authorized_for_class

    group_assignment = GroupAssignment.query.get_or_404(assignment_id)
    if current_user.role not in ['Director', 'School Administrator']:
        if not is_authorized_for_class(group_assignment.class_info):
            flash("You are not authorized to grant extensions.", "danger")
            return redirect(url_for('teacher.assignments.view_group_assignment', assignment_id=assignment_id))

    try:
        extended_due_date_str = request.form.get('extended_due_date')
        reason = request.form.get('reason', '')
        student_ids = request.form.getlist('student_ids')

        if not all([extended_due_date_str, student_ids]):
            flash('Missing required fields.', 'danger')
            return redirect(url_for('management.admin_grant_group_extensions', assignment_id=assignment_id))

        extended_due_date = datetime.strptime(extended_due_date_str, '%Y-%m-%dT%H:%M')
        granter_id = current_user.teacher_staff_id or (group_assignment.class_info.teacher_id if group_assignment.class_info else None)

        if not granter_id:
            flash('Cannot grant extensions: No teacher record found.', 'danger')
            return redirect(url_for('management.admin_grant_group_extensions', assignment_id=assignment_id))

        granted_count = 0
        for sid in student_ids:
            try:
                sid = int(sid)
                for old_ext in GroupAssignmentExtension.query.filter_by(group_assignment_id=assignment_id, student_id=sid, is_active=True).all():
                    old_ext.is_active = False
                new_ext = GroupAssignmentExtension(
                    group_assignment_id=assignment_id,
                    student_id=sid,
                    extended_due_date=extended_due_date,
                    reason=reason,
                    granted_by=granter_id,
                    is_active=True
                )
                db.session.add(new_ext)
                granted_count += 1
            except (ValueError, TypeError):
                continue

        db.session.commit()
        flash(f'Successfully granted extensions to {granted_count} student(s).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error granting extensions: {str(e)}', 'danger')

    return redirect(url_for('management.admin_grant_group_extensions', assignment_id=assignment_id))


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
    from types import SimpleNamespace
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
        
        # Get extensions for this group assignment
        try:
            from models import GroupAssignmentExtension
            extensions = GroupAssignmentExtension.query.filter_by(group_assignment_id=assignment_id, is_active=True).all()
        except Exception:
            extensions = []
        
        # Calculate enhanced statistics
        from models import GroupGrade
        from datetime import datetime, timedelta
        
        # Get all group grades (including voided ones for the unvoid button check)
        all_group_grades = GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()
        non_voided_grades = [g for g in all_group_grades if not g.is_voided]  # Non-voided for graded count
        graded_count = len(non_voided_grades)

        # Preserve visibility for grades tied to deleted/inactive groups.
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
        total_students = 0
        for group in groups:
            if getattr(group, 'id', None) == 0:
                total_students += len(getattr(group, 'members', []))
            else:
                total_students += len(group.members)
        
        # Calculate submission statistics
        submitted_group_ids = {s.group_id for s in submissions if getattr(s, 'group_id', None)}
        group_submission_count = len(submitted_group_ids)

        # Student-level submissions from GroupSubmission + GroupGrade(in_person/online)
        submission_student_ids = set()
        for gs in submissions:
            if (gs.attachment_file_path or gs.attachment_filename) and gs.group_id:
                for m in gs.group.members if gs.group else []:
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
        
        # Determine assignment status badge (Voided takes precedence)
        if group_assignment.status == 'Voided':
            assignment_status = 'Voided'
            status_class = 'secondary'
        elif non_voided_grades and len(non_voided_grades) > 0:
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
                             group_submission_count=group_submission_count,
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
        return redirect(url_for('management.assignments_and_grades', class_id=group_assignment.class_id))



# ============================================================
# Route: /group-assignment/<int:assignment_id>/grade', methods=['GET', 'POST']
# Function: admin_grade_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/grade', methods=['GET', 'POST'])
@login_required
def admin_grade_group_assignment(assignment_id):
    """Grade a group assignment - Allows teachers and administrators."""
    from models import GroupAssignment, StudentGroup, GroupGrade, GroupAssignmentExtension, TeacherStaff, Student, GroupSubmission
    from teacher_routes.utils import is_authorized_for_class
    from types import SimpleNamespace
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
        
        groups = list(groups)  # So we can append virtual group
        
        # Collect all students from all groups
        all_students = []
        students_by_id = {}
        for group in groups:
            for member in group.members:
                if member.student and member.student.id not in students_by_id:
                    all_students.append(member.student)
                    students_by_id[member.student.id] = member.student
        # If no groups (e.g. selected groups missing), ensure roster from class enrollment so grading still works
        if not students_by_id and group_assignment.class_id:
            for enr in Enrollment.query.filter_by(class_id=group_assignment.class_id).all():
                if getattr(enr, 'student', None) and enr.student.id not in students_by_id:
                    all_students.append(enr.student)
                    students_by_id[enr.student.id] = enr.student
            if all_students:
                virtual_roster = SimpleNamespace(
                    id=0,
                    name='Class roster',
                    members=[SimpleNamespace(student=s) for s in all_students]
                )
                groups.insert(0, virtual_roster)
        
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
        
        # Include students who have a grade for this assignment but are not in any current group
        # (e.g. their group was deleted — admin sets group_id to NULL; teacher marks group inactive)
        orphan_student_ids = [sid for sid in grades_by_student if sid not in students_by_id]
        if orphan_student_ids:
            orphan_students = Student.query.filter(Student.id.in_(orphan_student_ids)).all()
            if orphan_students:
                virtual_group = SimpleNamespace(
                    id=0,
                    name='Students from deleted group',
                    members=[SimpleNamespace(student=s) for s in orphan_students]
                )
                groups.append(virtual_group)
                for s in orphan_students:
                    if s.id not in students_by_id:
                        all_students.append(s)
                        students_by_id[s.id] = s
        
        # Get active extensions for this group assignment
        extensions = GroupAssignmentExtension.query.filter_by(
            group_assignment_id=assignment_id,
            is_active=True
        ).all()
        extensions_dict = {ext.student_id: ext for ext in extensions}
        
        # Build group submission status: group_id -> 'online' | 'not_submitted'
        group_submission_status = {}
        for sub in GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all():
            if sub.group_id and (sub.attachment_file_path or sub.attachment_filename):
                group_submission_status[sub.group_id] = 'online'
        
        # Calculate statistics
        total_students = len(all_students)
        graded_count = len([g for g in grades_by_student.values() if g.get('score', 0) > 0])
        total_score = sum([g.get('score', 0) for g in grades_by_student.values() if g.get('score', 0) > 0])
        average_score = (total_score / graded_count) if graded_count > 0 else 0
        
        if request.method == 'POST':
            try:
                # Build set of valid (group_id, student_id) from current groups
                valid_score_keys = {}
                for group in groups:
                    gid = getattr(group, 'id', None)
                    for member in group.members:
                        student = getattr(member, 'student', None)
                        if student and getattr(student, 'id', None):
                            valid_score_keys[f"score_{gid}_{student.id}"] = (gid, student.id)
                # Also allow any score_GID_SID where student is in our roster (resilient to key format or missing valid_score_keys)
                valid_student_ids = set(students_by_id.keys())
                # Debug: log grading context (remove or reduce after fixing live issue)
                score_form_keys = [k for k in request.form if k.startswith('score_')]
                try:
                    current_app.logger.info(
                        f"[group_grade] assignment_id={assignment_id} groups={len(groups)} "
                        f"valid_score_keys={len(valid_score_keys)} valid_student_ids={len(valid_student_ids)} "
                        f"form_score_keys={len(score_form_keys)} sample={score_form_keys[:5]!r}"
                    )
                except Exception:
                    pass
                graded_by_id = None
                if current_user.teacher_staff_id:
                    graded_by_id = current_user.teacher_staff_id
                if not graded_by_id and group_assignment.class_info:
                    try:
                        graded_by_id = group_assignment.class_info.teacher_id
                    except Exception:
                        pass
                if not graded_by_id:
                    t = TeacherStaff.query.limit(1).first()
                    if t:
                        graded_by_id = t.id
                if not graded_by_id:
                    # Fallback: any teacher for same school year
                    try:
                        sy_id = getattr(group_assignment.class_info, 'school_year_id', None) if group_assignment.class_info else None
                        if sy_id:
                            c = Class.query.filter_by(school_year_id=sy_id).filter(Class.teacher_id.isnot(None)).limit(1).first()
                            if c and c.teacher_id:
                                graded_by_id = c.teacher_id
                    except Exception:
                        pass
                try:
                    current_app.logger.info(f"[group_grade] graded_by_id={graded_by_id} total_points={group_assignment.total_points}")
                except Exception:
                    pass
                total_points = group_assignment.total_points if group_assignment.total_points else 100.0
                # UI sends 0-100 scale; accept up to max(total_points, 100) so percentage-style entry always saves
                effective_max = max(total_points, 100.0)
                saved_count = 0
                # Process ALL valid (gid, student_id) pairs so blank/missing scores = 0 get saved
                for key, (gid, student_id) in list(valid_score_keys.items()):
                    score = request.form.get(key)
                    comments_key = f"comments_{gid}_{student_id}"
                    comments = request.form.get(comments_key, '')
                    submission_type_key = f"submission_type_{gid}_{student_id}"
                    submission_type = request.form.get(submission_type_key, '').strip() or 'not_submitted'
                    notes_type_key = f"submission_notes_type_{gid}_{student_id}"
                    notes_type = request.form.get(notes_type_key, 'On-Time').strip()
                    notes_other_key = f"submission_notes_{gid}_{student_id}"
                    notes_other = request.form.get(notes_other_key, '').strip()
                    # Process all students - blank score = 0 and not submitted
                    try:
                        points_earned = float(score) if (score and str(score).strip()) else 0.0
                    except (ValueError, TypeError):
                        points_earned = 0.0
                    if not (0 <= points_earned <= effective_max):
                        continue
                    # UI is 0-100; if assignment total is not 100 and value looks like percentage (e.g. 85 > 10), scale to assignment total
                    if total_points > 0 and total_points < 100 and points_earned > total_points and points_earned <= 100:
                        points_earned = round(points_earned / 100.0 * total_points, 2)
                        display_total = total_points
                        percentage = (points_earned / display_total * 100) if display_total > 0 else 0
                    else:
                        display_total = total_points
                        percentage = (points_earned / display_total * 100) if display_total > 0 else 0
                    letter_grade = 'A' if percentage >= 90 else ('B' if percentage >= 80 else ('C' if percentage >= 70 else ('D' if percentage >= 60 else 'E')))
                    grade_data = {
                        'score': points_earned,
                        'points_earned': points_earned,
                        'total_points': display_total,
                        'max_score': display_total,
                        'percentage': round(percentage, 2),
                        'letter_grade': letter_grade
                    }
                    if submission_type in ('online', 'in_person', 'not_submitted'):
                        grade_data['submission_type'] = submission_type
                    # Submission notes: On-Time, Late, or custom text from Other
                    grade_data['submission_notes'] = notes_other if notes_type == 'Other' else (notes_type or 'On-Time')
                    save_group_id = None if gid == 0 else gid
                    existing_grade = GroupGrade.query.filter_by(
                        group_assignment_id=assignment_id,
                        student_id=student_id
                    ).first()
                    if existing_grade:
                        existing_grade.grade_data = json.dumps(grade_data)
                        existing_grade.comments = comments
                        existing_grade.group_id = save_group_id
                        if graded_by_id is not None:
                            existing_grade.graded_by = graded_by_id
                    else:
                        new_grade = GroupGrade(
                            group_assignment_id=assignment_id,
                            group_id=save_group_id,
                            student_id=student_id,
                            grade_data=json.dumps(grade_data),
                            graded_by=graded_by_id,  # may be None if no teacher available
                            comments=comments
                        )
                        db.session.add(new_grade)
                    saved_count += 1
                try:
                    current_app.logger.info(f"[group_grade] saved_count={saved_count} assignment_id={assignment_id}")
                    if saved_count == 0 and score_form_keys:
                        # Diagnose why nothing saved: count skips by reason
                        no_value = out_of_range = bad_float = student_invalid = 0
                        for k in score_form_keys:
                            parts = k.split('_')
                            if len(parts) != 3:
                                continue
                            try:
                                sid = int(parts[2])
                            except (ValueError, TypeError):
                                student_invalid += 1
                                continue
                            if sid not in valid_student_ids:
                                student_invalid += 1
                                continue
                            val = request.form.get(k)
                            if not val:
                                no_value += 1
                                continue
                            try:
                                p = float(val)
                                if not (0 <= p <= total_points):
                                    out_of_range += 1
                            except ValueError:
                                bad_float += 1
                        current_app.logger.warning(
                            f"[group_grade] saved_count=0 diagnosis: form_score_keys={len(score_form_keys)} "
                            f"no_value={no_value} out_of_range={out_of_range} bad_float={bad_float} student_invalid={student_invalid}"
                        )
                except Exception:
                    pass
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
                             group_submission_status=group_submission_status,
                             today=datetime.now().date())
    except Exception as e:
        print(f"Error grading group assignment: {e}")
        flash('Error accessing group assignment grading.', 'error')
        return redirect(url_for('management.assignments_and_grades', class_id=group_assignment.class_id))



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
    return redirect(url_for('management.assignments_and_grades', class_id=group_assignment.class_id))



# ============================================================
# Route: /group-assignment/<int:assignment_id>/edit', methods=['GET', 'POST']
# Function: admin_edit_group_assignment
# ============================================================

@bp.route('/group-assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_group_assignment(assignment_id):
    """Edit a group assignment - allows teachers (authorized for class) and admins."""
    # Enforce authorization: Directors/Admins or teachers authorized for the class
    if current_user.role not in ['Director', 'School Administrator']:
        from models import GroupAssignment
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        from teacher_routes.utils import is_authorized_for_class
        if not is_authorized_for_class(group_assignment.class_info):
            flash("You are not authorized to edit this group assignment.", "danger")
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))

    try:
        from models import GroupAssignment, StudentGroup

        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        class_obj = group_assignment.class_info

        # Get groups for select groups section
        groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
        # Parse selected group IDs for pre-checking (null/empty = all groups)
        selected_ids = []
        if group_assignment.selected_group_ids:
            try:
                selected_ids = json.loads(group_assignment.selected_group_ids) if isinstance(group_assignment.selected_group_ids, str) else group_assignment.selected_group_ids
                selected_ids = [int(x) for x in selected_ids]
            except Exception:
                pass
        # If no specific groups selected, treat as "all groups" - pre-select all
        if not selected_ids and groups:
            selected_ids = [g.id for g in groups]

        if request.method == 'POST':
            try:
                # Update basic fields
                group_assignment.title = request.form.get('title', group_assignment.title)
                group_assignment.description = request.form.get('description', group_assignment.description)
                group_assignment.status = request.form.get('assignment_status', group_assignment.status)
                group_assignment.quarter = request.form.get('quarter', group_assignment.quarter)

                # Dates (interpret form datetimes as school timezone)
                from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz
                tz_name = current_app.config.get('SCHOOL_TIMEZONE') or 'America/New_York'
                due_date_str = request.form.get('due_date')
                if due_date_str:
                    parsed = parse_form_datetime_as_school_tz(due_date_str, tz_name)
                    if parsed:
                        group_assignment.due_date = parsed
                    else:
                        flash('Invalid due date format.', 'error')
                        return render_template('management/admin_edit_group_assignment.html',
                                             group_assignment=group_assignment, class_obj=class_obj, groups=groups, selected_ids=selected_ids)
                open_date_str = request.form.get('open_date', '').strip()
                close_date_str = request.form.get('close_date', '').strip()
                group_assignment.open_date = parse_form_datetime_as_school_tz(open_date_str, tz_name) if open_date_str else None
                group_assignment.close_date = parse_form_datetime_as_school_tz(close_date_str, tz_name) if close_date_str else None

                # Category
                group_assignment.assignment_category = request.form.get('assignment_category') or None
                try:
                    group_assignment.category_weight = float(request.form.get('category_weight', 0) or 0)
                except (ValueError, TypeError):
                    group_assignment.category_weight = 0.0

                # Grading
                try:
                    group_assignment.total_points = float(request.form.get('total_points', 100) or 100)
                except (ValueError, TypeError):
                    group_assignment.total_points = 100.0
                group_assignment.allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
                try:
                    group_assignment.max_extra_credit_points = float(request.form.get('max_extra_credit_points', 0) or 0)
                except (ValueError, TypeError):
                    group_assignment.max_extra_credit_points = 0.0
                group_assignment.late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
                try:
                    group_assignment.late_penalty_per_day = float(request.form.get('late_penalty_per_day', 0) or 0)
                    group_assignment.late_penalty_max_days = int(request.form.get('late_penalty_max_days', 0) or 0)
                except (ValueError, TypeError):
                    group_assignment.late_penalty_per_day = 0.0
                    group_assignment.late_penalty_max_days = 0
                grade_scale_preset = request.form.get('grade_scale_preset', '').strip()
                if grade_scale_preset == 'standard':
                    group_assignment.grade_scale = json.dumps({"A": 93, "B": 80, "C": 70, "D": 60, "F": 0, "use_plus_minus": True})
                elif grade_scale_preset == 'strict':
                    group_assignment.grade_scale = json.dumps({"A": 93, "B": 85, "C": 77, "D": 70, "F": 0, "use_plus_minus": True})
                elif grade_scale_preset == 'lenient':
                    group_assignment.grade_scale = json.dumps({"A": 88, "B": 78, "C": 68, "D": 58, "F": 0, "use_plus_minus": True})
                else:
                    group_assignment.grade_scale = None

                # Group size (group_size_min, group_size_max; blank max = unlimited)
                min_size = request.form.get('min_group_size', '').strip()
                max_size = request.form.get('max_group_size', '').strip()
                try:
                    group_assignment.group_size_min = int(min_size) if min_size else 2
                    group_assignment.group_size_max = int(max_size) if max_size else None  # Blank = unlimited
                except ValueError:
                    flash('Invalid group size values.', 'error')
                    return render_template('management/admin_edit_group_assignment.html',
                                         group_assignment=group_assignment, class_obj=class_obj, groups=groups, selected_ids=selected_ids)

                group_assignment.assignment_type = request.form.get('assignment_type', group_assignment.assignment_type)
                group_assignment.collaboration_type = request.form.get('collaboration_type', group_assignment.collaboration_type)

                # Optional file replacement
                upload = request.files.get('assignment_file')
                if upload and upload.filename:
                    if not allowed_file(upload.filename):
                        flash(f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                        return render_template('management/admin_edit_group_assignment.html',
                                             group_assignment=group_assignment, class_obj=class_obj, groups=groups, selected_ids=selected_ids)

                    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'group_assignments')
                    os.makedirs(upload_dir, exist_ok=True)

                    original_name = secure_filename(upload.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    unique_filename = f"{timestamp}{original_name}"
                    file_path = os.path.join(upload_dir, unique_filename)

                    # Best-effort cleanup of previous stored file variants
                    old_name = group_assignment.attachment_filename
                    old_rel_path = group_assignment.attachment_file_path
                    if old_name:
                        for candidate in (
                            os.path.join(current_app.config['UPLOAD_FOLDER'], old_name),
                            os.path.join(current_app.config['UPLOAD_FOLDER'], 'group_assignments', old_name),
                        ):
                            try:
                                if os.path.exists(candidate):
                                    os.remove(candidate)
                            except OSError:
                                pass
                    if old_rel_path:
                        rel_norm = str(old_rel_path).replace('/', os.sep).replace('\\', os.sep)
                        abs_old = os.path.join(current_app.config['UPLOAD_FOLDER'], rel_norm)
                        try:
                            if os.path.exists(abs_old):
                                os.remove(abs_old)
                        except OSError:
                            pass

                    upload.save(file_path)
                    group_assignment.attachment_filename = unique_filename
                    group_assignment.attachment_original_filename = original_name
                    group_assignment.attachment_file_path = os.path.join('group_assignments', unique_filename)
                    try:
                        group_assignment.attachment_file_size = os.path.getsize(file_path)
                    except OSError:
                        group_assignment.attachment_file_size = None
                    group_assignment.attachment_mime_type = upload.content_type or None

                # Selected groups (empty = all groups = null; need at least one for valid assignment)
                selected_groups = request.form.getlist('groups')
                if not selected_groups and groups:
                    flash('Please select at least one group for this assignment.', 'warning')
                    return render_template('management/admin_edit_group_assignment.html',
                                         group_assignment=group_assignment, class_obj=class_obj, groups=groups, selected_ids=selected_ids)
                group_assignment.selected_group_ids = json.dumps(selected_groups) if selected_groups else None

                db.session.commit()
                flash('Assignment updated successfully!', 'success')
                # Redirect to appropriate view: teacher view for teachers, admin view for admins
                if current_user.role in ['Director', 'School Administrator']:
                    return redirect(url_for('management.admin_view_group_assignment', assignment_id=assignment_id))
                return redirect(url_for('teacher.assignments.view_group_assignment', assignment_id=assignment_id))
                
            except Exception as e:
                db.session.rollback()
                print(f"Error updating assignment: {e}")
                flash('Error updating assignment. Please try again.', 'error')

        return render_template('management/admin_edit_group_assignment.html',
                             group_assignment=group_assignment, class_obj=class_obj, groups=groups, selected_ids=selected_ids)
    except Exception as e:
        print(f"Error editing group assignment: {e}")
        flash('Error accessing group assignment editing.', 'error')
        try:
            ga = GroupAssignment.query.get(assignment_id)
            class_id = ga.class_id if ga else None
            if class_id:
                if current_user.role in ['Director', 'School Administrator']:
                    return redirect(url_for('management.assignments_and_grades', class_id=class_id))
                return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        except Exception:
            pass
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))



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
        from models import Assignment, AssignmentReopening, Enrollment, TeacherStaff, Submission, Grade
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
@management_required
def admin_get_reopen_status(assignment_id):
    """Get reopening status for all students in the assignment's class - Management view."""
    try:
        from models import Assignment, AssignmentReopening, Student, Submission, Grade
        
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