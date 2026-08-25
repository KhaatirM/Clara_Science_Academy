"""
Rules for Student Assistant assignments:
- Max 2 assistants per class.
- A student may be assistant for at most 2 classes in the *active* school year
  (closed-year / archived-class assignments do not count toward the limit).
- Eligible students: on the active school roster, and either enrolled in this
  class OR (when the class has grade levels) at or above the class minimum grade.
  Graduated / withdrawn / transferred / removed students are never eligible.
"""

MAX_ASSISTANTS_PER_CLASS = 2
MAX_CLASSES_PER_ASSISTANT = 2


def student_meets_class_grade_band(class_obj, student):
    """
    True if the class has grade levels set and the student's grade is at or
    above the lowest level (same cohort or higher grades).
    """
    if not class_obj or not student:
        return False
    gl = student.grade_level
    if gl is None:
        return False
    try:
        gl = int(gl)
    except (TypeError, ValueError):
        return False
    levels = class_obj.get_grade_levels()
    if not levels:
        return False
    return gl >= min(levels)


def is_eligible_student_assistant_candidate(class_obj, student, enrolled_in_class_ids):
    """
    Eligible if on the active roster and either enrolled in this class, OR
    (class has grade bands and student meets minimum grade).
    """
    from utils.student_roster import student_is_archived

    if not student or student_is_archived(student):
        return False
    eid = getattr(student, "id", None)
    if eid is not None and eid in (enrolled_in_class_ids or set()):
        return True
    return student_meets_class_grade_band(class_obj, student)


def students_in_school_year_for_assistant_pool(school_year_id):
    """
    Active-roster students with an active enrollment in an *active* class for
    this school year (excludes archived / graduated / withdrawn students).
    """
    from models import Student, Enrollment, Class
    from utils.student_roster import active_roster_student_filters

    if not school_year_id:
        return []
    class_ids = [
        c.id
        for c in Class.query.filter_by(school_year_id=school_year_id, is_active=True).all()
    ]
    if not class_ids:
        return []
    q = (
        Student.query.join(Enrollment)
        .filter(
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active.is_(True),
            active_roster_student_filters(),
        )
        .distinct()
    )
    return q.order_by(Student.last_name, Student.first_name).all()


def filter_eligible_assistant_candidates(class_obj, candidate_students, enrolled_in_class_ids):
    """Return students who may be selected as assistants for this class."""
    enrolled_in_class_ids = enrolled_in_class_ids or set()
    out = [
        s
        for s in (candidate_students or [])
        if is_eligible_student_assistant_candidate(class_obj, s, enrolled_in_class_ids)
    ]
    return sorted(
        out,
        key=lambda x: ((x.last_name or "").lower(), (x.first_name or "").lower()),
    )


def count_assistant_classes_for_student_excluding(
    student_id,
    exclude_class_id=None,
    *,
    school_year_id=None,
    active_school_year_only=True,
):
    """
    How many classes this student is already an assistant for.

    By default counts only active classes on the active school year so closed-year
    history does not block new assignments. Pass ``school_year_id`` to scope to a
    specific year; set ``active_school_year_only=False`` only for admin audits.
    """
    from models import Class, SchoolYear, StudentAssistant

    q = (
        StudentAssistant.query.filter_by(student_id=student_id)
        .join(Class, StudentAssistant.class_id == Class.id)
        .filter(Class.is_active.is_(True))
    )
    if exclude_class_id is not None:
        q = q.filter(StudentAssistant.class_id != exclude_class_id)

    if school_year_id is not None:
        q = q.filter(Class.school_year_id == int(school_year_id))
    elif active_school_year_only:
        active = SchoolYear.query.filter_by(is_active=True).first()
        if not active:
            return 0
        q = q.filter(Class.school_year_id == active.id)

    return q.count()


def is_class_open_for_assistant(class_obj, active_school_year=None):
    """
    True when a class may still be used for student-assistant work.
    Closed / archived classes (inactive or not on the active school year) are excluded.
    """
    if not class_obj:
        return False
    if not getattr(class_obj, "is_active", False):
        return False
    if active_school_year is None:
        from models import SchoolYear

        active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_school_year:
        return False
    return class_obj.school_year_id == active_school_year.id


def active_assistant_classes_for_student(student_id, active_school_year=None):
    """Classes this student assists that are still open (active + current school year)."""
    from models import Class, SchoolYear, StudentAssistant

    if not student_id:
        return []
    if active_school_year is None:
        active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_school_year:
        return []

    rows = (
        StudentAssistant.query.filter_by(student_id=student_id)
        .join(Class, StudentAssistant.class_id == Class.id)
        .filter(
            Class.is_active.is_(True),
            Class.school_year_id == active_school_year.id,
        )
        .all()
    )
    classes = [sa.class_info for sa in rows if sa.class_info]
    classes.sort(key=lambda c: ((c.name or "").lower(), c.id or 0))
    return classes


def student_is_active_assistant_for_class(student_id, class_id, active_school_year=None):
    """True if student is assigned assistant for this class and the class is still open."""
    from models import Class, StudentAssistant

    if not student_id or not class_id:
        return False
    sa = StudentAssistant.query.filter_by(student_id=student_id, class_id=class_id).first()
    if not sa:
        return False
    class_obj = sa.class_info or Class.query.get(class_id)
    return is_class_open_for_assistant(class_obj, active_school_year=active_school_year)


# --- Assistant-proposed assignments (teacher/admin approval before students see them) ---

ASSISTANT_APPROVAL_PENDING = "pending"
ASSISTANT_APPROVAL_APPROVED = "approved"
ASSISTANT_APPROVAL_REJECTED = "rejected"


def assignment_visible_to_students(assignment_or_group_assignment):
    """False while pending or rejected; True for normal assignments and approved proposals."""
    s = getattr(assignment_or_group_assignment, "assistant_approval_status", None)
    return s is None or s == ASSISTANT_APPROVAL_APPROVED


def assignment_student_visibility_filter():
    """SQLAlchemy filter: students only see approved or non-assistant assignments; hide quiz drafts."""
    from sqlalchemy import and_, or_
    from models import Assignment

    approved = or_(
        Assignment.assistant_approval_status.is_(None),
        Assignment.assistant_approval_status == ASSISTANT_APPROVAL_APPROVED,
    )
    # Quizzes saved as in-progress drafts are staff-only until published
    not_quiz_draft = or_(
        Assignment.assignment_type != "quiz",
        Assignment.quiz_authoring_is_draft.isnot(True),
    )
    return and_(approved, not_quiz_draft)


def group_assignment_student_visibility_filter():
    from sqlalchemy import or_
    from models import GroupAssignment

    return or_(
        GroupAssignment.assistant_approval_status.is_(None),
        GroupAssignment.assistant_approval_status == ASSISTANT_APPROVAL_APPROVED,
    )


def count_pending_assistant_proposals_for_class(class_id):
    """Individual + group assignments awaiting teacher/admin approval for this class."""
    from models import Assignment, GroupAssignment

    if class_id is None:
        return 0
    return (
        Assignment.query.filter(
            Assignment.class_id == class_id,
            Assignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
        ).count()
        + GroupAssignment.query.filter(
            GroupAssignment.class_id == class_id,
            GroupAssignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
        ).count()
    )
