"""Shared school-year filter state for management list views."""

from flask import request

from models import Class, Enrollment, SchoolYear, db


def get_active_school_year():
    """Return the single active school year, or None when the year is closed."""
    return SchoolYear.query.filter_by(is_active=True).first()


def get_school_year_for_display():
    """
    School year for read-only enrollment displays (student detail, etc.).
    Uses the active year when set; otherwise the most recent year by start date.
    """
    active = get_active_school_year()
    if active:
        return active
    return (
        SchoolYear.query.order_by(SchoolYear.start_date.desc(), SchoolYear.id.desc()).first()
    )


def student_classes_for_school_year(student_id: int, school_year: SchoolYear) -> list:
    """Classes a student is/was enrolled in for the given school year."""
    q = (
        Enrollment.query.join(Class, Enrollment.class_id == Class.id)
        .filter(
            Enrollment.student_id == student_id,
            Class.school_year_id == school_year.id,
        )
    )
    if school_year.is_active:
        q = q.filter(Enrollment.is_active.is_(True))
    rows = q.order_by(Class.name).all()
    seen: set[int] = set()
    classes = []
    for enrollment in rows:
        class_info = enrollment.class_info
        if class_info and class_info.id not in seen:
            seen.add(class_info.id)
            classes.append(class_info)
    return classes


def active_school_year_class_ids(*, include_inactive_classes: bool = False) -> list[int]:
    """Class IDs belonging to the active school year."""
    active = get_active_school_year()
    if not active:
        return []
    q = Class.query.filter(Class.school_year_id == active.id)
    if not include_inactive_classes:
        q = q.filter(Class.is_active.is_(True))
    return [row[0] for row in q.with_entities(Class.id).all()]


def student_ids_enrolled_in_school_year(
    school_year_id: int,
    student_ids: list[int] | None = None,
    *,
    class_ids: list[int] | None = None,
) -> list[int]:
    """Student IDs with an active enrollment in the given school year's classes."""
    if class_ids is None:
        class_ids = [
            row[0]
            for row in Class.query.filter(Class.school_year_id == school_year_id)
            .with_entities(Class.id)
            .all()
        ]
    if not class_ids:
        return []
    q = Enrollment.query.filter(
        Enrollment.class_id.in_(class_ids),
        Enrollment.is_active.is_(True),
    )
    if student_ids is not None:
        q = q.filter(Enrollment.student_id.in_(student_ids))
    return list({row[0] for row in q.with_entities(Enrollment.student_id).all()})


def teacher_class_ids_for_school_year(teacher_staff_id: int, school_year_id: int) -> list[int]:
    """Classes a teacher leads (primary, additional, or substitute) in a school year."""
    from sqlalchemy import or_

    from models import class_additional_teachers, class_substitute_teachers

    classes = Class.query.filter(
        Class.school_year_id == school_year_id,
        Class.is_active.is_(True),
        or_(
            Class.teacher_id == teacher_staff_id,
            Class.id.in_(
                db.session.query(class_additional_teachers.c.class_id).filter(
                    class_additional_teachers.c.teacher_id == teacher_staff_id
                )
            ),
            Class.id.in_(
                db.session.query(class_substitute_teachers.c.class_id).filter(
                    class_substitute_teachers.c.teacher_id == teacher_staff_id
                )
            ),
        ),
    ).all()
    return [c.id for c in classes]


def teacher_class_ids_active_school_year(teacher_staff_id: int) -> list[int]:
    """Teacher's class IDs scoped to the active school year."""
    active = get_active_school_year()
    if not active:
        return []
    return teacher_class_ids_for_school_year(teacher_staff_id, active.id)


def _empty_query(model):
    """SQLAlchemy query that matches no rows."""
    return model.query.filter(db.false())


def extension_requests_query(*, class_ids: list[int] | None = None, status: str | None = None):
    """Extension requests for assignments in the active school year."""
    from models import Assignment, ExtensionRequest

    active = get_active_school_year()
    if not active:
        return _empty_query(ExtensionRequest)

    q = ExtensionRequest.query.join(Assignment).filter(
        Assignment.school_year_id == active.id
    )
    if class_ids is not None:
        if not class_ids:
            return _empty_query(ExtensionRequest)
        q = q.filter(Assignment.class_id.in_(class_ids))
    if status:
        q = q.filter(ExtensionRequest.status == status)
    return q


def redo_requests_query(*, class_ids: list[int] | None = None, status: str | None = None):
    """Redo requests for assignments in the active school year."""
    from models import Assignment, RedoRequest

    active = get_active_school_year()
    if not active:
        return _empty_query(RedoRequest)

    q = RedoRequest.query.join(Assignment).filter(
        Assignment.school_year_id == active.id
    )
    if class_ids is not None:
        if not class_ids:
            return _empty_query(RedoRequest)
        q = q.filter(Assignment.class_id.in_(class_ids))
    if status:
        q = q.filter(RedoRequest.status == status)
    return q


def count_pending_extension_requests(class_ids: list[int] | None = None) -> int:
    return extension_requests_query(class_ids=class_ids, status='Pending').count()


def count_pending_redo_requests(class_ids: list[int] | None = None) -> int:
    return redo_requests_query(class_ids=class_ids, status='Pending').count()


def assignment_redos_query(*, class_ids: list[int] | None = None):
    """Assignment redo records scoped to the active school year."""
    from models import Assignment, AssignmentRedo

    active = get_active_school_year()
    if not active:
        return _empty_query(AssignmentRedo)

    q = AssignmentRedo.query.join(Assignment).filter(
        Assignment.school_year_id == active.id
    )
    if class_ids is not None:
        if not class_ids:
            return _empty_query(AssignmentRedo)
        q = q.filter(Assignment.class_id.in_(class_ids))
    return q


def assignment_reopenings_query(*, class_ids: list[int] | None = None, active_only: bool = True):
    """Assignment reopening records scoped to the active school year."""
    from models import Assignment, AssignmentReopening

    active = get_active_school_year()
    if not active:
        return _empty_query(AssignmentReopening)

    q = AssignmentReopening.query.join(Assignment).filter(
        Assignment.school_year_id == active.id
    )
    if active_only:
        q = q.filter(AssignmentReopening.is_active.is_(True))
    if class_ids is not None:
        if not class_ids:
            return _empty_query(AssignmentReopening)
        q = q.filter(Assignment.class_id.in_(class_ids))
    return q


def classes_for_active_school_year(*, class_ids: list[int] | None = None) -> list:
    """Class rows for the active school year (optional id subset)."""
    active = get_active_school_year()
    if not active:
        return []
    q = Class.query.filter(
        Class.school_year_id == active.id,
        Class.is_active.is_(True),
    )
    if class_ids is not None:
        if not class_ids:
            return []
        q = q.filter(Class.id.in_(class_ids))
    return q.order_by(Class.name).all()


def get_school_year_filter_context():
    """
    School year dropdown state for filter UIs.

    - Defaults selection to the active year when one exists.
    - When the year is closed (no active year), selection stays empty until the user picks one.
    """
    active = get_active_school_year()
    selected = request.args.get('school_year_id', type=int)
    if selected is None and active:
        selected = active.id
    years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    return {
        'school_years': years,
        'selected_school_year_id': selected,
        'active_school_year': active,
    }
