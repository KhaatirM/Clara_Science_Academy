"""
Report card grade calculation by grade level.
Uses SubjectRequirement table when populated; falls back to hardcoded lists.
"""

import json
from sqlalchemy import func

from flask import current_app
from extensions import db
from models import Grade, Assignment, ReportCard, Student, AcademicPeriod, SubjectRequirement

# Fallback subject lists (used when SubjectRequirement table is empty)
_SUBJECTS_1_2 = [
    "Reading Comprehension", "Language Arts", "Spelling", "Handwriting",
    "Math", "Science", "Social Studies", "Art", "Physical Education"
]
_SUBJECTS_3 = [
    "Reading", "English", "Spelling", "Math", "Science", "Social Studies",
    "Art", "Physical Education", "Islamic Studies", "Quran", "Arabic"
]
_SUBJECTS_4_8 = [
    "Reading", "English", "Spelling", "Vocabulary", "Math", "Science",
    "Social Studies", "Art", "Physical Education", "Islamic Studies", "Quran", "Arabic"
]


def _subjects_for_grade_level(grade_level):
    """Return list of subject names for a grade level from DB or fallback."""
    try:
        reqs = SubjectRequirement.query.filter(
            SubjectRequirement.grade_level_min <= grade_level,
            SubjectRequirement.grade_level_max >= grade_level
        ).order_by(SubjectRequirement.display_order).all()
        if reqs:
            return [r.subject_name for r in reqs]
    except Exception:
        pass
    if grade_level in (1, 2):
        return _SUBJECTS_1_2
    if grade_level == 3:
        return _SUBJECTS_3
    if grade_level in (4, 5, 6, 7, 8):
        return _SUBJECTS_4_8
    return []


def _calculate_grades_for_subjects(grades, subjects):
    """
    Helper: average grades for a list of subjects.
    """
    calculated = {}
    for subject in subjects:
        subject_grades = [g for g in grades if g.assignment.class_info.name == subject]
        if subject_grades:
            total_score = 0
            count = 0
            for g in subject_grades:
                try:
                    grade_data = json.loads(g.grade_data)
                    score = grade_data.get('score')
                    if isinstance(score, (int, float)):
                        total_score += score
                        count += 1
                except (json.JSONDecodeError, TypeError):
                    current_app.logger.warning(f"Could not parse grade_data for grade id {g.id}: {g.grade_data}")
            if count > 0:
                avg = total_score / count
                calculated[subject] = {'score': round(avg, 2), 'comment': ''}
    return calculated


def _calculate_grades_1_2(grades, quarter):
    """Grades for 1st and 2nd grade. Uses SubjectRequirement table or fallback."""
    subjects = _subjects_for_grade_level(1)
    return _calculate_grades_for_subjects(grades, subjects)


def _calculate_grades_3(grades, quarter):
    """Grades for 3rd grade. Uses SubjectRequirement table or fallback."""
    subjects = _subjects_for_grade_level(3)
    return _calculate_grades_for_subjects(grades, subjects)


def _calculate_grades_4_8(grades, quarter):
    """Grades for 4th–8th grade. Uses SubjectRequirement table or fallback."""
    subjects = _subjects_for_grade_level(4)
    calculated_grades = _calculate_grades_for_subjects(grades, subjects)
    if calculated_grades:
        scores = [d.get('score', 0) for d in calculated_grades.values() if isinstance(d.get('score'), (int, float))]
        if scores:
            overall_avg = sum(scores) / len(scores)
            calculated_grades['Overall'] = {'score': round(overall_avg, 2)}
    return calculated_grades


def calculate_and_get_grade_for_student(student_id, school_year_id, quarter):
    """
    Calculate grades for a student for a quarter and school year; store in ReportCard.
    Only runs if the quarter has ended (AcademicPeriod end_date).
    """
    from datetime import date

    student = Student.query.get(student_id)
    if not student:
        return {}

    quarter_period = AcademicPeriod.query.filter_by(
        school_year_id=school_year_id,
        name=f"Q{quarter}",
        period_type='quarter',
        is_active=True
    ).first()

    if quarter_period:
        today = date.today()
        if today < quarter_period.end_date:
            current_app.logger.info(
                f"Quarter Q{quarter} has not ended yet (ends {quarter_period.end_date}). Grade calculation skipped."
            )
            return {}

    grades = db.session.query(Grade).join(Assignment).filter(
        Grade.student_id == student_id,
        Assignment.school_year_id == school_year_id,
        Assignment.quarter == quarter
    ).all()

    calculated_grades = {}
    if student.grade_level in [1, 2]:
        calculated_grades = _calculate_grades_1_2(grades, quarter)
    elif student.grade_level == 3:
        calculated_grades = _calculate_grades_3(grades, quarter)
    elif student.grade_level in [4, 5, 6, 7, 8]:
        calculated_grades = _calculate_grades_4_8(grades, quarter)
    else:
        current_app.logger.info(f"No grade calculation logic for grade level: {student.grade_level}")
        return {}

    report_card = ReportCard.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id,
        quarter=quarter
    ).first()

    if not report_card:
        report_card = ReportCard()
        report_card.student_id = student_id
        report_card.school_year_id = school_year_id
        report_card.quarter = quarter
        db.session.add(report_card)

    report_card.grades_details = json.dumps(calculated_grades)
    report_card.generated_at = func.now()
    db.session.commit()
    return calculated_grades


def get_grade_for_student(student_id, school_year_id, quarter):
    """
    Return stored report card grades for a student/quarter. If none, calculate and return.
    """
    report_card = ReportCard.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id,
        quarter=quarter
    ).first()

    if report_card and report_card.grades_details:
        return json.loads(report_card.grades_details)
    return calculate_and_get_grade_for_student(student_id, school_year_id, quarter)
