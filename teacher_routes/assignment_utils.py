"""
Utility functions for assignment status and date calculations.
"""
import re
from datetime import datetime, timezone


def _as_utc_aware(dt):
    """
    Normalize a datetime for comparison with datetime.now(timezone.utc).
    Naive datetimes are treated as UTC (matches legacy DB rows).
    """
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    # date only
    return datetime.combine(dt, datetime.min.time()).replace(tzinfo=timezone.utc)


_QUIZ_SUBMISSION_SCORE_RE = re.compile(
    r'Quiz\s+submitted\s+with\s+([0-9]*\.?[0-9]+)\s*/\s*([0-9]*\.?[0-9]+)\s*points?',
    re.IGNORECASE,
)


def parse_quiz_submission_auto_score(comments):
    """
    Extract auto-graded points from the comment set by submit_quiz()
    (e.g. 'Quiz submitted with 8.0/10.0 points'). Returns dict with
    earned, total, percentage; or None if not a quiz auto-submit comment.
    """
    if not comments or not isinstance(comments, str):
        return None
    m = _QUIZ_SUBMISSION_SCORE_RE.search(comments.strip())
    if not m:
        return None
    try:
        earned = float(m.group(1))
        total = float(m.group(2))
    except (ValueError, TypeError):
        return None
    pct = (earned / total * 100.0) if total > 0 else 0.0
    return {'earned': earned, 'total': total, 'percentage': round(pct, 2)}


def parse_discussion_description(desc):
    """Parse discussion prompt, instructions, rubric from stored description."""
    prompt, instructions, rubric = '', '', ''
    min_initial_posts, min_replies = 1, 2
    if not desc:
        return prompt, instructions, rubric, min_initial_posts, min_replies
    m = re.search(r'\*\*Discussion Prompt:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)', desc, re.DOTALL)
    if m:
        prompt = m.group(1).strip()
    m = re.search(r'\*\*Instructions:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)', desc, re.DOTALL)
    if m:
        instructions = m.group(1).strip()
    m = re.search(r'\*\*Rubric:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)', desc, re.DOTALL)
    if m:
        rubric = m.group(1).strip()
    m = re.search(r'Minimum (\d+) initial post', desc)
    if m:
        min_initial_posts = int(m.group(1))
    m = re.search(r'Minimum (\d+) reply', desc)
    if m:
        min_replies = int(m.group(1))
    return prompt, instructions, rubric, min_initial_posts, min_replies
from models import AssignmentExtension


def parse_form_datetime_as_school_tz(dt_str, tz_name=None, fmt='%Y-%m-%dT%H:%M'):
    """
    Parse datetime string from form as school timezone, return UTC.
    Form inputs (e.g. datetime-local) are assumed to be in school time (Eastern).
    Tries multiple formats for robustness: %Y-%m-%dT%H:%M, %Y-%m-%d, %Y-%m-%d %H:%M
    """
    if not dt_str or not dt_str.strip():
        return None
    import pytz
    tz = pytz.timezone(tz_name or 'America/New_York')
    s = dt_str.strip()
    for try_fmt in (fmt, '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y-%m-%d %H:%M'):
        try:
            dt = datetime.strptime(s, try_fmt)
            return tz.localize(dt).astimezone(pytz.UTC)
        except ValueError:
            continue
    return None

def calculate_assignment_status(assignment):
    """
    Calculate assignment status based on open_date, close_date, and current date.
    
    Status logic:
    - 'Voided': If assignment.status is 'Voided' (manual override)
    - 'Upcoming': If current time is before open_date (or before close_date if no open_date)
    - 'Active': If current time is between open_date and close_date (or past open_date if no close_date)
    - 'Inactive': If current time is past close_date (or past due_date if no close_date)
    
    Returns:
        str: 'Upcoming', 'Active', 'Inactive', or 'Voided'
    """
    if assignment.status == 'Voided':
        return 'Voided'
    
    now = datetime.now(timezone.utc)  # Use timezone-aware datetime
    
    # If assignment has open_date, check if we're before it
    if assignment.open_date:
        open_datetime = assignment.open_date
        # Ensure open_datetime is timezone-aware
        if isinstance(open_datetime, datetime):
            if open_datetime.tzinfo is None:
                open_datetime = open_datetime.replace(tzinfo=timezone.utc)
        else:
            open_datetime = datetime.combine(open_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
        if now < open_datetime:
            return 'Upcoming'
    
    # Check close_date (or due_date if close_date not set)
    close_datetime = None
    if assignment.close_date:
        close_datetime = assignment.close_date
        # Ensure close_datetime is timezone-aware
        if isinstance(close_datetime, datetime):
            if close_datetime.tzinfo is None:
                close_datetime = close_datetime.replace(tzinfo=timezone.utc)
        else:
            close_datetime = datetime.combine(close_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
    elif assignment.due_date:
        # If close_date not set, use due_date as close_date
        close_datetime = assignment.due_date
        # Ensure close_datetime is timezone-aware
        if isinstance(close_datetime, datetime):
            if close_datetime.tzinfo is None:
                close_datetime = close_datetime.replace(tzinfo=timezone.utc)
        else:
            close_datetime = datetime.combine(close_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    if close_datetime:
        if now > close_datetime:
            return 'Inactive'
        else:
            # We're past open_date (if set) and before close_date
            return 'Active'
    else:
        # No close_date or due_date - default to Active if we're past open_date (or always Active if no open_date)
        if assignment.open_date:
            open_datetime = assignment.open_date
            # Ensure open_datetime is timezone-aware
            if isinstance(open_datetime, datetime):
                if open_datetime.tzinfo is None:
                    open_datetime = open_datetime.replace(tzinfo=timezone.utc)
            else:
                open_datetime = datetime.combine(open_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
            if now >= open_datetime:
                return 'Active'
            else:
                return 'Upcoming'
        else:
            # No open_date or close_date - default to Active
            return 'Active'


def get_effective_assignment_status(assignment):
    """
    Lifecycle status for display (templates, reports).

    - Voided rows stay Voided.
    - If status_override + status_override_until is still in the future, keep the stored
      status for that window (teacher/admin pinned Active/Inactive/etc.).
    - Otherwise derive status from open_date / close_date / due_date via
      calculate_assignment_status() so labels match actual availability dates.
    """
    if getattr(assignment, 'status', None) == 'Voided':
        return 'Voided'
    now = datetime.now(timezone.utc)
    until = getattr(assignment, 'status_override_until', None)
    override = getattr(assignment, 'status_override', None)
    if until is not None and override:
        until_aware = _as_utc_aware(until)
        if until_aware and until_aware > now:
            st = getattr(assignment, 'status', None)
            if st and st != 'Voided':
                return st
    return calculate_assignment_status(assignment)


def compute_assignment_void_scope(assignment, enrolled_student_ids, voided_student_ids):
    """
    Whether an assignment is fully or partially voided for the class roster.
    enrolled_student_ids / voided_student_ids are student id iterables.
    """
    enrolled_set = {sid for sid in (enrolled_student_ids or []) if sid}
    voided_set = {sid for sid in (voided_student_ids or []) if sid} & enrolled_set
    all_voided = (
        getattr(assignment, 'status', None) == 'Voided'
        or (bool(enrolled_set) and enrolled_set <= voided_set)
    )
    partially_voided = not all_voided and bool(voided_set)
    return {
        'all_voided': all_voided,
        'partially_voided': partially_voided,
        'voided_count': len(voided_set),
        'enrolled_count': len(enrolled_set),
    }


def get_student_close_date(assignment, student_id):
    """
    Get the effective close date for a student, considering extensions.
    
    Args:
        assignment: Assignment object
        student_id: Student ID to check for extensions
    
    Returns:
        datetime: The effective close date for this student (extension date if exists, otherwise assignment close_date or due_date)
    """
    # Check for active extension
    if student_id:
        extension = AssignmentExtension.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True
        ).first()
        
        if extension and extension.extended_due_date:
            return extension.extended_due_date
    
    # No extension - use close_date or due_date
    if assignment.close_date:
        close_dt = assignment.close_date
        if isinstance(close_dt, datetime):
            # Ensure timezone-aware
            if close_dt.tzinfo is None:
                close_dt = close_dt.replace(tzinfo=timezone.utc)
            return close_dt
        else:
            return datetime.combine(close_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
    elif assignment.due_date:
        due_dt = assignment.due_date
        if isinstance(due_dt, datetime):
            # Ensure timezone-aware
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            return due_dt
        else:
            return datetime.combine(due_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    return None


def is_assignment_open_for_student(assignment, student_id):
    """
    Check if an assignment is currently open for submission for a specific student.
    
    Args:
        assignment: Assignment object
        student_id: Student ID to check
    
    Returns:
        bool: True if assignment is open for this student, False otherwise
    """
    # Check if assignment is voided
    if assignment.status == 'Voided':
        return False

    # Student assistant proposals: not open until approved
    ap = getattr(assignment, 'assistant_approval_status', None)
    if ap is not None and ap != 'approved':
        return False

    from models import Grade
    st_grade = Grade.query.filter_by(
        assignment_id=assignment.id,
        student_id=student_id,
    ).first()
    if st_grade and getattr(st_grade, 'is_voided', False):
        return False

    now = datetime.now(timezone.utc)  # Use timezone-aware datetime
    lifecycle = get_effective_assignment_status(assignment)

    # Inactive assignments: block unless student has valid extension, reopening, or redo
    if lifecycle == 'Inactive':
        from models import AssignmentReopening, AssignmentRedo
        # First check: student may have extension—is their effective close_date still valid?
        student_close_date = get_student_close_date(assignment, student_id)
        if student_close_date and now <= _as_utc_aware(student_close_date):
            return True  # Still within extension window
        # Otherwise check reopening or redo
        reopening = AssignmentReopening.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True
        ).first()
        if reopening:
            return True  # Student has been granted reopening
        redo = AssignmentRedo.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_used=False
        ).first()
        if redo and redo.redo_deadline and now <= _as_utc_aware(redo.redo_deadline):
            return True  # Student has valid redo within deadline
        return False  # Inactive and no extension/reopening/redo - cannot submit

    # Upcoming assignments: block unless student has active reopening or valid redo
    if lifecycle == 'Upcoming':
        from models import AssignmentReopening, AssignmentRedo
        reopening = AssignmentReopening.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True
        ).first()
        if reopening:
            return True  # Reopening grants early access
        redo = AssignmentRedo.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_used=False
        ).first()
        if redo and redo.redo_deadline and now <= _as_utc_aware(redo.redo_deadline):
            return True  # Valid redo grants access
        # Fall through to open_date check below (will return False)
    
    # Check open_date
    if assignment.open_date:
        open_datetime = assignment.open_date
        # Ensure open_datetime is timezone-aware
        if isinstance(open_datetime, datetime):
            if open_datetime.tzinfo is None:
                open_datetime = open_datetime.replace(tzinfo=timezone.utc)
        else:
            open_datetime = datetime.combine(open_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
        if now < open_datetime:
            return False  # Assignment hasn't opened yet
    
    # Check close_date (with extension support)
    student_close_date = get_student_close_date(assignment, student_id)
    if student_close_date:
        if now > _as_utc_aware(student_close_date):
            return False  # Assignment is closed (even with extension)
    
    return True  # Assignment is open


def quiz_authoring_save_action(form):
    """Form value for quiz builder: 'draft' (save progress) or 'publish' (students may see when dates allow)."""
    v = (form.get("quiz_save_action") or "publish").strip().lower()
    return v if v in ("draft", "publish") else "publish"


def quiz_draft_default_due_date():
    """UTC naive datetime used when saving a draft without a due date yet."""
    from datetime import timedelta

    return datetime.utcnow() + timedelta(days=7)


def count_quiz_questions_in_request(form):
    """
    Count non-empty quiz questions in POST data (block_order or legacy question_text_* keys).
    Used to require at least one question before publishing.
    """
    block_order_str = (form.get("block_order") or "").strip()
    n = 0
    if block_order_str:
        for block in block_order_str.split(","):
            block = block.strip()
            if block.startswith("question_"):
                qid = block.replace("question_", "")
                if (form.get(f"question_text_{qid}") or "").strip():
                    n += 1
        return n
    for key in form.keys():
        if key.startswith("question_text_") and not key.endswith("[]"):
            if (form.get(key) or "").strip():
                n += 1
    return n


def teacher_can_review_extension_request(extension_request, teacher):
    """True if teacher owns the class for this extension request."""
    if teacher is None:
        return False
    assignment = extension_request.assignment
    class_info = getattr(assignment, 'class_info', None)
    if not class_info:
        return False
    return class_info.teacher_id == teacher.id


def apply_extension_request_review(extension_request, action, review_notes, reviewer_id):
    """
    Approve or reject a pending extension request and sync AssignmentExtension on approve.
    Returns a short success message. Caller must commit the session.
    """
    from datetime import datetime
    from models import db

    if extension_request.status != 'Pending':
        raise ValueError('Request is no longer pending')

    assignment = extension_request.assignment
    now = datetime.utcnow()

    if action == 'approve':
        extension_request.status = 'Approved'
        extension_request.reviewed_at = now
        extension_request.reviewed_by = reviewer_id
        extension_request.review_notes = review_notes if review_notes else None

        existing_extension = AssignmentExtension.query.filter_by(
            assignment_id=assignment.id,
            student_id=extension_request.student_id,
            is_active=True,
        ).first()

        reason = review_notes if review_notes else 'Extension granted'
        if existing_extension:
            existing_extension.extended_due_date = extension_request.requested_due_date
            existing_extension.reason = reason
        else:
            db.session.add(AssignmentExtension(
                assignment_id=assignment.id,
                student_id=extension_request.student_id,
                extended_due_date=extension_request.requested_due_date,
                reason=reason,
                granted_by=reviewer_id,
                is_active=True,
            ))

        return (
            f'Extension request approved. New due date: '
            f'{extension_request.requested_due_date.strftime("%Y-%m-%d %I:%M %p")}'
        )

    extension_request.status = 'Rejected'
    extension_request.reviewed_at = now
    extension_request.reviewed_by = reviewer_id
    extension_request.review_notes = review_notes if review_notes else 'Extension request rejected'
    return 'Extension request rejected'


def bulk_process_extension_reviews(request_ids, action, review_notes, reviewer_id, teacher=None, admin=False):
    """
    Review multiple pending extension requests. Returns (processed_requests, failed_entries).
    Caller must commit the session.
    """
    from models import ExtensionRequest

    processed = []
    failed = []

    for rid in request_ids:
        extension_request = ExtensionRequest.query.get(rid)
        if not extension_request:
            failed.append({'id': rid, 'reason': 'Not found'})
            continue
        if not admin and not teacher_can_review_extension_request(extension_request, teacher):
            failed.append({'id': rid, 'reason': 'Not authorized'})
            continue
        if extension_request.status != 'Pending':
            failed.append({'id': rid, 'reason': 'Not pending'})
            continue
        try:
            apply_extension_request_review(
                extension_request,
                action,
                review_notes,
                reviewer_id,
            )
            processed.append(extension_request)
        except ValueError as e:
            failed.append({'id': rid, 'reason': str(e)})

    return processed, failed


def notify_extension_request_review(extension_request, action, review_notes=''):
    """Notify the student about an extension decision (best-effort)."""
    try:
        from flask import url_for
        from app import create_notification

        student_user = getattr(extension_request.student, 'user', None)
        if not student_user or not student_user.id:
            return

        assign_title = extension_request.assignment.title
        if action == 'approve':
            create_notification(
                student_user.id,
                'extension_request',
                'Extension request approved',
                (
                    f'Your extension request for "{assign_title}" was approved. '
                    f'New due date: {extension_request.requested_due_date.strftime("%B %d, %Y at %I:%M %p")}.'
                ),
                link=url_for('student.student_assignments'),
            )
        else:
            create_notification(
                student_user.id,
                'extension_request',
                'Extension request not approved',
                (
                    f'Your extension request for "{assign_title}" was not approved.'
                    + (f' Note: {review_notes}' if review_notes else '')
                ),
                link=url_for('student.student_assignments'),
            )
    except Exception:
        pass

