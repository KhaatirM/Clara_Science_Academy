"""3rd grade Language Arts and Math standards checklist content (director report card pages 2–3)."""

QUARTER_COLUMNS = ['Q1', 'Q2', 'Q3', 'Q4']

GRADE3_LANGUAGE_ARTS = {
    'title': 'Language Arts',
    'sections': [
        {
            'title': 'Comprehension and Reading',
            'standards': [
                {
                    'id': 'la_cr_1',
                    'text': (
                        'Understand fiction appropriate to grade level – Identify and interpret the meaning '
                        'of vocabulary, apply word recognition skills, make inferences and draw conclusions, '
                        'identify main idea and relevant details, summarize, and identify genre of fictional text.'
                    ),
                },
                {
                    'id': 'la_cr_2',
                    'text': (
                        'Understand nonfiction appropriate to grade level – Identify and interpret the meaning '
                        'of vocabulary, apply word recognition skills, make inferences and draw conclusions, '
                        'explain main idea and relevant details, summarize, and identify genre of nonfiction text.'
                    ),
                },
            ],
        },
        {
            'title': 'Interpretation and Analysis of Fictional and Nonfictional Text',
            'standards': [
                {
                    'id': 'la_ia_1',
                    'text': (
                        'Understand components within and between texts – Read and respond to fiction and '
                        'nonfiction text demonstrating understanding. Identify, interpret, compare, and describe '
                        'components of fiction and nonfiction (character, setting, plot/action), and make '
                        'connections between texts. Understand literary devices in fictional and nonfictional '
                        'text - Identify and interpret figurative language (e.g., rhyme, rhythm, personification).'
                    ),
                },
                {
                    'id': 'la_ia_2',
                    'text': (
                        'Understand concepts and organization of nonfiction text – Differentiate fact from '
                        'opinion and distinguish between essential and nonessential information. Identify, '
                        'compare, explain, and interpret how organization clarifies meaning of text.'
                    ),
                },
            ],
        },
        {
            'title': '',
            'standards': [
                {
                    'id': 'la_w_1',
                    'text': (
                        'Types of Writing Write narrative pieces (e.g. stories, poems, plays). Write '
                        'multi-paragraph informational pieces (e.g., essays, reports, letters, and instructions). '
                        'Write an opinion and support it with facts. Write to various prompts.'
                    ),
                },
                {
                    'id': 'la_w_2',
                    'text': (
                        'Quality of Writing Write with a sharp, distinct focus identifying topic, task, and '
                        'audience. Use well-developed content appropriate for the topic. Write with controlled '
                        'and/or subtle organization. Write with an understanding of the stylistic aspects of the '
                        'composition. Revise writing to improve word choice, organization, sentence structure, '
                        'order of ideas, and precision of vocabulary. Edit writing using the conventions of '
                        'language. Printing and/or cursive is legible.'
                    ),
                },
            ],
        },
        {
            'title': 'Speaking and Listening',
            'standards': [
                {
                    'id': 'la_sl_1',
                    'text': (
                        'Demonstrate the ability to listen to others, ask questions to aid understanding, and '
                        'distinguish fact from opinion. Listen to fiction or nonfiction literature and relate it '
                        'to similar experiences, make predictions, retell in chronological order, identify and '
                        'define new words and concepts. Speak using appropriate pronunciation and pace with an '
                        'awareness of audience. Contribute to and participate in small and large group discussions. '
                        'Use media/technology for learning purposes.'
                    ),
                },
            ],
        },
    ],
}

GRADE3_MATH = {
    'title': 'Math',
    'sections': [
        {
            'title': 'Numbers and Operations',
            'standards': [
                {
                    'id': 'math_no_1',
                    'text': (
                        'Demonstrate an understanding of numbers, ways of representing numbers, relationships '
                        'among numbers and number systems – Apply place value concepts and numeration to counting, '
                        'ordering, grouping, and equivalency. Use fractions to represent quantities as part of a '
                        'whole or set. Count, compare and make change using a collection of coins and one-dollar bills.'
                    ),
                },
                {
                    'id': 'math_no_2',
                    'text': (
                        'Understand the meanings of operations, use operations, and understand how they relate to '
                        'each other Understand various meanings of operations and the relationship between them. '
                        '(e.g., multiplication as repeated addition, fact families, factors, identifying the correct '
                        'operation(s) to solve word problems)'
                    ),
                },
                {
                    'id': 'math_no_3',
                    'text': (
                        'Compute accurately and fluently and make reasonable estimates - Solve computation and word '
                        'problems using addition and subtraction (with and without regrouping), and multiplication '
                        '(through 9x5). Use estimation skills to arrive at conclusions.'
                    ),
                },
            ],
        },
        {
            'title': 'Measurement',
            'standards': [
                {
                    'id': 'math_m_1',
                    'text': (
                        'Demonstrate an understanding of measurable attributes of objects and figures, and the '
                        'units, systems and processes of measurement. Apply appropriate techniques, tools, and '
                        'formulas to determine measurement – Determine or calculate time and elapsed time. Identify '
                        'time of day as AM or PM. Use the attributes of length, area, volume, and weight of objects. '
                        'Determine the measurement of objects with standard and non-standard units of measurement.'
                    ),
                },
            ],
        },
        {
            'title': 'Geometry',
            'standards': [
                {
                    'id': 'math_g_1',
                    'text': (
                        'Analyze characteristics and properties of two- and three-dimensional geometric shapes and '
                        'demonstrate understanding of geometric relationships – Identify and/or describe two- and '
                        'three-dimensional objects. Apply the concepts of transformations and symmetry.'
                    ),
                },
            ],
        },
        {
            'title': 'Algebraic Concepts',
            'standards': [
                {
                    'id': 'math_ac_1',
                    'text': (
                        'Demonstrate an understanding of patterns, relations, and functions. Represent and/or analyze '
                        'mathematical situations using numbers, symbols, words, tables and/or graphs – Recognize, '
                        'describe, or extend a variety of patterns. Create/model expressions, equations, and '
                        'inequalities to match a problem situation. Determine the missing number or symbol in a '
                        'number sentence.'
                    ),
                },
            ],
        },
        {
            'title': 'Data Analysis and Probability',
            'standards': [
                {
                    'id': 'math_dap_1',
                    'text': (
                        'Formulate or answer questions that can be addressed with data and/or organize, display, '
                        'interpret or analyze data – Answer questions based on data shown on tables, charts, and bar '
                        'graphs through analysis, description, and interpretation of data. Organize and display data '
                        'using tables, charts, and bar graphs. Translate information from one type of display to another.'
                    ),
                },
            ],
        },
    ],
}


VALID_MARKS = ('M', 'W', 'NA', 'UA')

# Map subject keys used in URLs / forms to the catalog dicts above.
SUBJECT_CATALOGS = {
    'language_arts': GRADE3_LANGUAGE_ARTS,
    'math': GRADE3_MATH,
}

# Map each standard_id back to its subject_key for fast filtering.
_STANDARD_SUBJECT = {}
for _subject_key, _subject in SUBJECT_CATALOGS.items():
    for _section in _subject['sections']:
        for _std in _section['standards']:
            _STANDARD_SUBJECT[_std['id']] = _subject_key


def subject_for_standard(standard_id):
    """Return the subject key ('language_arts' or 'math') for a standard_id, or None."""
    return _STANDARD_SUBJECT.get(standard_id)


def flat_standards(subject_key):
    """Return a flat list of standards for a subject: [{id, section, text}, ...]."""
    subject = SUBJECT_CATALOGS.get(subject_key)
    if not subject:
        return []
    out = []
    for section in subject['sections']:
        for std in section['standards']:
            out.append({
                'id': std['id'],
                'section': section.get('title') or '',
                'text': std['text'],
            })
    return out


def _normalize_marks(raw_marks):
    """Return {standard_id: {Q1: mark, ...}} from saved report card JSON."""
    if not raw_marks or not isinstance(raw_marks, dict):
        return {}
    out = {}
    for std_id, quarter_map in raw_marks.items():
        if not isinstance(quarter_map, dict):
            continue
        out[str(std_id)] = {
            q: (quarter_map.get(q) or quarter_map.get(q.lower()) or '')
            for q in QUARTER_COLUMNS
        }
    return out


def get_marks_for_student(student_id, school_year_id, subject_key=None):
    """
    Read all Grade3StandardMark rows for a student/school year (optionally filtered
    by subject), returning {standard_id: {Q1: mark, ...}, ...}.
    Returns an empty dict on any error so PDF rendering stays safe.
    """
    try:
        from models import Grade3StandardMark
    except Exception:
        return {}
    try:
        q = Grade3StandardMark.query.filter_by(
            student_id=student_id,
            school_year_id=school_year_id,
        )
        rows = q.all()
    except Exception:
        return {}

    out = {}
    for row in rows:
        sid = row.standard_id
        if subject_key and subject_for_standard(sid) != subject_key:
            continue
        out.setdefault(sid, {})[row.quarter] = row.mark
    return out


def get_marks_for_students(student_ids, school_year_id, subject_key=None):
    """
    Return {student_id: {standard_id: {Q1: mark, ...}}} for a set of students,
    optionally filtered to one subject (language_arts | math).
    """
    student_ids = [int(s) for s in (student_ids or []) if s is not None]
    if not student_ids:
        return {}
    try:
        from models import Grade3StandardMark
    except Exception:
        return {}
    try:
        rows = Grade3StandardMark.query.filter(
            Grade3StandardMark.student_id.in_(student_ids),
            Grade3StandardMark.school_year_id == school_year_id,
        ).all()
    except Exception:
        return {}

    out = {sid: {} for sid in student_ids}
    for row in rows:
        if subject_key and subject_for_standard(row.standard_id) != subject_key:
            continue
        student_marks = out.setdefault(row.student_id, {})
        student_marks.setdefault(row.standard_id, {})[row.quarter] = row.mark
    return out


def upsert_mark(student_id, standard_id, school_year_id, quarter, mark, user_id=None):
    """
    Insert/update/delete one mark row.
    - mark in VALID_MARKS: insert or update the row
    - mark falsy (''/None): delete any existing row
    Caller is responsible for db.session.commit().
    Returns True if the row was changed.
    """
    try:
        from extensions import db
        from models import Grade3StandardMark
    except Exception:
        return False
    if quarter not in QUARTER_COLUMNS:
        return False
    if not subject_for_standard(standard_id):
        return False

    row = Grade3StandardMark.query.filter_by(
        student_id=student_id,
        standard_id=standard_id,
        school_year_id=school_year_id,
        quarter=quarter,
    ).first()

    clean_mark = (mark or '').strip()
    if clean_mark and clean_mark not in VALID_MARKS:
        return False

    if not clean_mark:
        if row:
            db.session.delete(row)
            return True
        return False

    if row:
        if row.mark == clean_mark and row.updated_by == user_id:
            return False
        row.mark = clean_mark
        row.updated_by = user_id
        return True

    db.session.add(Grade3StandardMark(
        student_id=student_id,
        standard_id=standard_id,
        school_year_id=school_year_id,
        quarter=quarter,
        mark=clean_mark,
        updated_by=user_id,
    ))
    return True


def class_completeness(student_ids, school_year_id, subject_key):
    """
    Return per-quarter completeness stats for a class roster.
    {
        'total_cells_per_quarter': int,   # students * standards
        'standards_count': int,
        'students_count': int,
        'quarters': {'Q1': {'filled': int, 'total': int, 'percent': int}, ...},
        'overall': {'filled': int, 'total': int, 'percent': int},  # all 4 quarters
        'last_updated': datetime | None,
    }
    """
    standards = flat_standards(subject_key)
    standards_count = len(standards)
    students_count = len(student_ids or [])
    per_quarter_total = students_count * standards_count
    overall_total = per_quarter_total * len(QUARTER_COLUMNS)

    quarters = {q: {'filled': 0, 'total': per_quarter_total, 'percent': 0} for q in QUARTER_COLUMNS}
    last_updated = None

    if not student_ids or standards_count == 0:
        return {
            'total_cells_per_quarter': per_quarter_total,
            'standards_count': standards_count,
            'students_count': students_count,
            'quarters': quarters,
            'overall': {'filled': 0, 'total': overall_total, 'percent': 0},
            'last_updated': None,
        }

    try:
        from models import Grade3StandardMark
        rows = Grade3StandardMark.query.filter(
            Grade3StandardMark.student_id.in_([int(s) for s in student_ids]),
            Grade3StandardMark.school_year_id == school_year_id,
        ).all()
    except Exception:
        rows = []

    standard_ids_in_subject = {s['id'] for s in standards}
    total_filled = 0
    for r in rows:
        if r.standard_id not in standard_ids_in_subject:
            continue
        if r.quarter in quarters:
            quarters[r.quarter]['filled'] += 1
            total_filled += 1
        if r.updated_at and (last_updated is None or r.updated_at > last_updated):
            last_updated = r.updated_at

    for q, stats in quarters.items():
        stats['percent'] = int(round(100 * stats['filled'] / stats['total'])) if stats['total'] else 0

    overall_percent = int(round(100 * total_filled / overall_total)) if overall_total else 0
    return {
        'total_cells_per_quarter': per_quarter_total,
        'standards_count': standards_count,
        'students_count': students_count,
        'quarters': quarters,
        'overall': {'filled': total_filled, 'total': overall_total, 'percent': overall_percent},
        'last_updated': last_updated,
    }


def section_completeness(student_ids, school_year_id, subject_key, quarter):
    """Return per-section completeness for one subject + one quarter.
    Returns: {section_title: {'filled': int, 'total': int, 'percent': int}}
    """
    subject = SUBJECT_CATALOGS.get(subject_key)
    if not subject or not student_ids:
        return {}

    sections = []
    section_for_std = {}
    for section in subject['sections']:
        title = section.get('title') or ''
        std_ids = [s['id'] for s in section['standards']]
        sections.append({'title': title, 'std_ids': std_ids})
        for sid in std_ids:
            section_for_std[sid] = title

    try:
        from models import Grade3StandardMark
        rows = Grade3StandardMark.query.filter(
            Grade3StandardMark.student_id.in_([int(s) for s in student_ids]),
            Grade3StandardMark.school_year_id == school_year_id,
            Grade3StandardMark.quarter == quarter,
        ).all()
    except Exception:
        rows = []

    students_count = len(student_ids)
    result = {}
    for sect in sections:
        total = students_count * len(sect['std_ids'])
        result[sect['title']] = {'filled': 0, 'total': total, 'percent': 0}

    for r in rows:
        sect_title = section_for_std.get(r.standard_id)
        if sect_title is not None:
            result[sect_title]['filled'] += 1

    for stats in result.values():
        stats['percent'] = int(round(100 * stats['filled'] / stats['total'])) if stats['total'] else 0
    return result


def copy_marks_from_previous_quarter(student_ids, school_year_id, subject_key, target_quarter, user_id=None):
    """
    For each student, copy any marks from the previous quarter into target_quarter,
    only filling cells that are currently blank. Returns count of marks copied.
    """
    if target_quarter not in QUARTER_COLUMNS:
        return 0
    idx = QUARTER_COLUMNS.index(target_quarter)
    if idx == 0:
        return 0
    prev_q = QUARTER_COLUMNS[idx - 1]

    existing = get_marks_for_students(student_ids, school_year_id, subject_key=subject_key)
    copied = 0
    for sid in student_ids:
        per_std = existing.get(sid, {})
        for std_id, per_q in per_std.items():
            prev_mark = per_q.get(prev_q)
            if not prev_mark:
                continue
            if per_q.get(target_quarter):
                continue
            if upsert_mark(sid, std_id, school_year_id, target_quarter, prev_mark, user_id=user_id):
                copied += 1
    return copied


def grade3_standards_context(report_card_data=None, student_id=None, school_year_id=None):
    """
    Template context for pages 2 (Language Arts) and 3 (Math).
    Prefers persistent Grade3StandardMark rows for the student/year; falls back to
    marks saved in `report_card_data['standards_marks']` so older PDFs still render.
    """
    saved = {}
    if isinstance(report_card_data, dict):
        saved = report_card_data.get('standards_marks') or {}

    la_marks = _normalize_marks(saved.get('language_arts') if isinstance(saved, dict) else {})
    math_marks = _normalize_marks(saved.get('math') if isinstance(saved, dict) else {})

    if student_id and school_year_id:
        live = get_marks_for_student(student_id, school_year_id)
        # Live DB marks win over JSON when present (more accurate; teacher kept editing).
        for std_id, per_q in live.items():
            subject = subject_for_standard(std_id)
            target = la_marks if subject == 'language_arts' else math_marks
            existing = target.get(std_id, {q: '' for q in QUARTER_COLUMNS})
            for q in QUARTER_COLUMNS:
                v = per_q.get(q)
                if v:
                    existing[q] = v
            target[std_id] = existing

    return {
        'grade3_language_arts': GRADE3_LANGUAGE_ARTS,
        'grade3_math': GRADE3_MATH,
        'grade3_language_arts_marks': la_marks,
        'grade3_math_marks': math_marks,
        'grade3_quarter_columns': QUARTER_COLUMNS,
    }
