"""Kindergarten standards checklist content and mark helpers."""

QUARTER_COLUMNS = ['Q1', 'Q2', 'Q3', 'Q4']

# Academic standards (ELA / Math)
ACADEMIC_MARKS = ('M', 'N', 'I', 'U')
# Kindergarten skills / writing proficiency / interventions
PROFICIENCY_MARKS = ('X',)
# Work habits
HABIT_MARKS = ('E', 'S', 'N', 'U')
# Developmental writing continuum levels 1–7
WRITING_LEVEL_MARKS = ('1', '2', '3', '4', '5', '6', '7')

VALID_MARKS = tuple(dict.fromkeys(ACADEMIC_MARKS + PROFICIENCY_MARKS + HABIT_MARKS + WRITING_LEVEL_MARKS))

KINDERGARTEN_LANGUAGE_ARTS = {
    'title': 'English Language Arts Academic Standards',
    'mark_scale': 'academic',
    'sections': [
        {
            'title': 'Reading Standards: Foundational Skills — K.RF.1 Print Concepts',
            'standards': [
                {'id': 'k_rf1_1', 'text': 'Track print left to right, top to bottom, and page to page'},
                {'id': 'k_rf1_2', 'text': 'Point to words with one-to-one correspondence'},
                {'id': 'k_rf1_3', 'text': 'Recognize and name all uppercase letters'},
                {'id': 'k_rf1_4', 'text': 'Recognize and name all lowercase letters'},
            ],
        },
        {
            'title': 'K.RF.2 Phonological Awareness',
            'standards': [
                {'id': 'k_rf2_1', 'text': 'Recognize and produce rhyming words'},
                {'id': 'k_rf2_2', 'text': 'Count, pronounce, blend, and segment syllables in spoken words'},
                {'id': 'k_rf2_3', 'text': 'Blend and segment onsets and rimes of spoken words'},
                {'id': 'k_rf2_4', 'text': 'Isolate and pronounce the beginning, middle, and ending sounds of spoken words'},
                {'id': 'k_rf2_5', 'text': 'Add or substitute letter sounds to make new words'},
            ],
        },
        {
            'title': 'K.RF.3 Phonics and Word Recognition',
            'standards': [
                {'id': 'k_rf3_1', 'text': 'Produce all consonant letter sounds'},
                {'id': 'k_rf3_2', 'text': 'Produce all short and long vowel sounds'},
                {'id': 'k_rf3_3', 'text': 'Read common high-frequency words by sight'},
                {'id': 'k_rf3_4', 'text': 'Distinguish differences between similarly-spelled words'},
            ],
        },
        {
            'title': 'K.RF.4 Fluency',
            'standards': [
                {'id': 'k_rf4_1', 'text': 'Read emergent-reader texts with purpose and understanding'},
            ],
        },
        {
            'title': 'Reading Standards for Informational Text and Literature — Key Ideas and Details',
            'standards': [
                {'id': 'k_ri_rl_1', 'text': 'K.RI.1/K.RL.1 Ask and answer questions about key details in a text'},
                {'id': 'k_ri_2', 'text': 'K.RI.2 Identify the main topic and retell key details of a text'},
                {'id': 'k_rl_2', 'text': 'K.RL.2 Retell familiar stories, including key details'},
            ],
        },
        {
            'title': 'Craft and Structure',
            'standards': [
                {'id': 'k_ri_rl_4', 'text': 'K.RI.4/K.RL.4 Ask and answer questions about unknown words in a text'},
                {'id': 'k_ri_5', 'text': 'K.RI.5 Identify front/back cover, and title page of a book'},
                {'id': 'k_ri_rl_6', 'text': 'K.RI.6/K.RL.6 Identify author/illustrator and define role of each'},
            ],
        },
        {
            'title': 'Knowledge and Ideas',
            'standards': [
                {'id': 'k_ri_rl_7', 'text': 'K.RI.7/K.RL.7 Connects text to illustrations'},
                {'id': 'k_ri_rl_9', 'text': 'K.RI.9/K.RL.9 Compare and contrast two texts'},
            ],
        },
        {
            'title': 'Text Types and Purposes (X when proficient — apply after kid spelling stage)',
            'standards': [
                {'id': 'k_w1_topic', 'text': 'K.W.1 Opinion — Define topic'},
                {'id': 'k_w1_opinion', 'text': 'K.W.1 Opinion — State an opinion or preference (explains why)'},
                {'id': 'k_w2_topic', 'text': 'K.W.2 Informative — Define topic'},
                {'id': 'k_w2_info', 'text': 'K.W.2 Informative — Supply information about topic'},
                {'id': 'k_w3_setting', 'text': 'K.W.3 Narrative — Define setting'},
                {'id': 'k_w3_events', 'text': 'K.W.3 Narrative — Recount event(s)'},
                {'id': 'k_w3_sequence', 'text': 'K.W.3 Narrative — Follow order of sequence'},
                {'id': 'k_w3_reaction', 'text': 'K.W.3 Narrative — Provide reaction to what happened'},
                {'id': 'k_w3_linking', 'text': 'Use linking words (when, then, but, and, next)'},
                {'id': 'k_w3_closure', 'text': 'Provide a sense of closure'},
                {'id': 'k_w_conventions', 'text': 'Apply conventions to writing'},
            ],
        },
        {
            'title': 'Language Standards — Conventions of Standard English',
            'standards': [
                {'id': 'k_l1_upper', 'text': 'K.L.1 Correctly print uppercase letters'},
                {'id': 'k_l1_lower', 'text': 'K.L.1 Correctly print lowercase letters'},
                {'id': 'k_l2_cap', 'text': 'K.L.2 Capitalize first word in sentence and the pronoun I'},
                {'id': 'k_l2_punct', 'text': 'K.L.2 Recognize and name end punctuation'},
                {'id': 'k_l2_sounds', 'text': 'K.L.2 Write letter(s) for consonant and short-vowel sounds'},
                {'id': 'k_l2_spell', 'text': 'K.L.2 Spell simple words phonetically'},
            ],
        },
        {
            'title': 'Vocabulary Use',
            'standards': [
                {'id': 'k_l5_sort', 'text': 'K.L.5 Sort common objects into categories (e.g. shapes, food)'},
                {'id': 'k_l5_opposites', 'text': 'K.L.5 Demonstrate understanding of opposites'},
            ],
        },
    ],
}

KINDERGARTEN_MATH = {
    'title': 'Mathematics Standards',
    'mark_scale': 'academic',
    'sections': [
        {
            'title': 'Counting and Cardinality — Know number names and the count sequence',
            'standards': [
                {'id': 'k_cc1_ones', 'text': 'K.CC.1 Count to 100 by ones'},
                {'id': 'k_cc1_tens', 'text': 'K.CC.1 Count to 100 by tens'},
                {'id': 'k_cc2', 'text': 'K.CC.2 Count forward beginning from a given number'},
                {'id': 'k_cc3', 'text': 'K.CC.3 Write numbers from 0-20'},
            ],
        },
        {
            'title': 'Count to tell the number of objects',
            'standards': [
                {'id': 'k_cc4_1', 'text': 'K.CC.4 Count objects with one-to-one correspondence'},
                {'id': 'k_cc4_2', 'text': 'K.CC.4 Identify the number that is one more than a given number 0-20'},
                {'id': 'k_cc5', 'text': 'K.CC.5 Count to tell how many objects are in a set up to 20'},
            ],
        },
        {
            'title': 'Compare numbers',
            'standards': [
                {'id': 'k_cc6', 'text': 'K.CC.6 Compare sets of objects as greater than, less than, or equal to 0-10'},
                {'id': 'k_cc7', 'text': 'K.CC.7 Compare two numbers presented as written numerals 1-10'},
            ],
        },
        {
            'title': 'Number and Operations in Base Ten',
            'standards': [
                {
                    'id': 'k_nbt1',
                    'text': 'K.NBT.1 Represent numbers as tens and ones using objects, drawings, equations',
                },
            ],
        },
        {
            'title': 'Measurement and Data',
            'standards': [
                {'id': 'k_md1', 'text': 'K.MD.1 Describe measurable attributes of a single object'},
                {
                    'id': 'k_md2',
                    'text': 'K.MD.2 Compare/contrast two objects (longer, shorter, taller, lighter, or heavier)',
                },
                {'id': 'k_md3', 'text': 'K.MD.3 Sort objects into given categories and count number in each'},
            ],
        },
        {
            'title': 'Geometry — Identify and describe shapes',
            'standards': [
                {'id': 'k_g1_names', 'text': 'K.G.1 Describe objects in the environment using names of shapes'},
                {
                    'id': 'k_g1_position',
                    'text': 'K.G.1 Describe the relative position of objects (above, below, beside, etc.)',
                },
                {'id': 'k_g2', 'text': 'K.G.2 Correctly names the 9 shapes listed above'},
                {'id': 'k_g3', 'text': 'K.G.3 Identify shapes as two-dimensional or three-dimensional'},
            ],
        },
        {
            'title': 'Analyze, compare, create, and compose shapes',
            'standards': [
                {'id': 'k_g4', 'text': 'K.G.4 Analyze and compare shapes'},
                {'id': 'k_g5', 'text': 'K.G.5 Model shapes in the world by building and drawing'},
                {'id': 'k_g6', 'text': 'K.G.6 Make larger shapes by combining smaller shapes'},
            ],
        },
    ],
}

KINDERGARTEN_WRITING_LEVEL = {
    'title': 'Developmental Writing Level',
    'mark_scale': 'writing_level',
    'sections': [
        {
            'title': 'Developmental Stages of Writing (1–7)',
            'standards': [
                {
                    'id': 'k_writing_level',
                    'text': (
                        '1 Pictures · 2 Scribbles · 3 Random Letters · 4 Letters Represent Words · '
                        '5 Beginning Sounds Represent Words · 6 Kid Spelling · 7 Kid Spelling with standard Spelling'
                    ),
                },
            ],
        },
    ],
}

KINDERGARTEN_SKILLS = {
    'title': 'Kindergarten Skills',
    'mark_scale': 'proficiency',
    'sections': [
        {
            'title': 'Life / readiness skills (X when proficient)',
            'standards': [
                {'id': 'k_skill_days', 'text': 'Name days of the week'},
                {'id': 'k_skill_months', 'text': 'Name months of the year'},
                {'id': 'k_skill_colors', 'text': 'Name 11 basic colors'},
                {'id': 'k_skill_first', 'text': 'Print first name correctly'},
                {'id': 'k_skill_last', 'text': 'Print last name correctly'},
                {'id': 'k_skill_tools', 'text': 'Hold writing tools correctly'},
                {'id': 'k_skill_cut', 'text': 'Cut on a line'},
                {'id': 'k_skill_address', 'text': 'Know address'},
                {'id': 'k_skill_phone', 'text': 'Know phone number'},
                {'id': 'k_skill_birthday', 'text': 'Name birthday'},
            ],
        },
    ],
}

KINDERGARTEN_WORK_HABITS = {
    'title': 'Work Habits and Social Skills',
    'mark_scale': 'habits',
    'sections': [
        {
            'title': 'E = Excellent · S = Satisfactory · N = Needs Improvement · U = Unsatisfactory',
            'standards': [
                {'id': 'k_habit_ontime', 'text': 'Complete and turn in work on time'},
                {'id': 'k_habit_independent', 'text': 'Work independently'},
                {'id': 'k_habit_participate', 'text': 'Participate willingly in activities'},
                {'id': 'k_habit_cooperate', 'text': 'Work and play cooperatively with others'},
                {'id': 'k_habit_directions', 'text': 'Follow simple directions'},
                {'id': 'k_habit_control', 'text': 'Control body and voice'},
                {'id': 'k_habit_cleanup', 'text': 'Clean up work area'},
                {'id': 'k_habit_effort', 'text': 'Give best effort'},
                {'id': 'k_habit_respect', 'text': 'Respect authority of all school staff'},
                {'id': 'k_habit_task', 'text': 'Stay on task during instruction'},
            ],
        },
    ],
}

KINDERGARTEN_INTERVENTIONS = {
    'title': 'Interventions',
    'mark_scale': 'proficiency',
    'sections': [
        {
            'title': 'X if parent was notified if child is',
            'standards': [
                {'id': 'k_int_risk', 'text': 'At risk for retention'},
                {'id': 'k_int_recommend', 'text': 'Recommended for retention'},
            ],
        },
    ],
}

# Writing standards use X (proficiency) even though nested under LA catalog section title.
_WRITING_PROFICIENCY_IDS = {
    'k_w1_topic', 'k_w1_opinion', 'k_w2_topic', 'k_w2_info', 'k_w3_setting', 'k_w3_events',
    'k_w3_sequence', 'k_w3_reaction', 'k_w3_linking', 'k_w3_closure', 'k_w_conventions',
}

_HOMEROOM_SUBJECT_KEYS = ("writing_level", "kindergarten_skills", "work_habits", "interventions")

KINDERGARTEN_HOMEROOM = {
    "title": "Kindergarten Skills, Habits & Writing",
    "mark_scale": "mixed",
    "sections": [
        *KINDERGARTEN_WRITING_LEVEL["sections"],
        *KINDERGARTEN_SKILLS["sections"],
        *KINDERGARTEN_WORK_HABITS["sections"],
        *KINDERGARTEN_INTERVENTIONS["sections"],
    ],
}

SUBJECT_CATALOGS = {
    "language_arts": KINDERGARTEN_LANGUAGE_ARTS,
    "math": KINDERGARTEN_MATH,
    "writing_level": KINDERGARTEN_WRITING_LEVEL,
    "kindergarten_skills": KINDERGARTEN_SKILLS,
    "work_habits": KINDERGARTEN_WORK_HABITS,
    "interventions": KINDERGARTEN_INTERVENTIONS,
    "homeroom": KINDERGARTEN_HOMEROOM,
}

_SCALE_MARKS = {
    'academic': ACADEMIC_MARKS,
    'proficiency': PROFICIENCY_MARKS,
    'habits': HABIT_MARKS,
    'writing_level': WRITING_LEVEL_MARKS,
}

_STANDARD_SUBJECT = {}
_STANDARD_SCALE = {}
for _subject_key, _subject in SUBJECT_CATALOGS.items():
    if _subject_key == "homeroom":
        continue
    scale = _subject.get("mark_scale") or "academic"
    for _section in _subject["sections"]:
        for _std in _section["standards"]:
            sid = _std["id"]
            _STANDARD_SUBJECT[sid] = _subject_key
            if sid in _WRITING_PROFICIENCY_IDS:
                _STANDARD_SCALE[sid] = "proficiency"
            else:
                _STANDARD_SCALE[sid] = scale


def subject_for_standard(standard_id):
    return _STANDARD_SUBJECT.get(standard_id)


def scale_for_standard(standard_id):
    return _STANDARD_SCALE.get(standard_id)


def valid_marks_for_standard(standard_id):
    return _SCALE_MARKS.get(scale_for_standard(standard_id), ACADEMIC_MARKS)


def _standard_matches_subject(standard_id, subject_key):
    if not subject_key:
        return True
    if subject_key == "homeroom":
        return subject_for_standard(standard_id) in _HOMEROOM_SUBJECT_KEYS
    return subject_for_standard(standard_id) == subject_key


def flat_standards(subject_key):
    if subject_key == "homeroom":
        out = []
        for key in _HOMEROOM_SUBJECT_KEYS:
            out.extend(flat_standards(key))
        return out
    subject = SUBJECT_CATALOGS.get(subject_key)
    if not subject:
        return []
    out = []
    for section in subject["sections"]:
        for std in section["standards"]:
            out.append(
                {
                    "id": std["id"],
                    "section": section.get("title") or "",
                    "text": std["text"],
                    "mark_scale": scale_for_standard(std["id"]),
                    "valid_marks": list(valid_marks_for_standard(std["id"])),
                }
            )
    return out


def _normalize_marks(raw_marks):
    if not raw_marks or not isinstance(raw_marks, dict):
        return {}
    out = {}
    for std_id, quarter_map in raw_marks.items():
        if not isinstance(quarter_map, dict):
            continue
        out[str(std_id)] = {
            q: (quarter_map.get(q) or quarter_map.get(q.lower()) or "")
            for q in QUARTER_COLUMNS
        }
    return out


def get_marks_for_student(student_id, school_year_id, subject_key=None):
    try:
        from models import GradeKStandardMark
    except Exception:
        return {}
    try:
        rows = GradeKStandardMark.query.filter_by(
            student_id=student_id,
            school_year_id=school_year_id,
        ).all()
    except Exception:
        return {}

    out = {}
    for row in rows:
        sid = row.standard_id
        if not _standard_matches_subject(sid, subject_key):
            continue
        out.setdefault(sid, {})[row.quarter] = row.mark
    return out


def get_marks_for_students(student_ids, school_year_id, subject_key=None):
    student_ids = [int(s) for s in (student_ids or []) if s is not None]
    if not student_ids:
        return {}
    try:
        from models import GradeKStandardMark
    except Exception:
        return {}
    try:
        rows = GradeKStandardMark.query.filter(
            GradeKStandardMark.student_id.in_(student_ids),
            GradeKStandardMark.school_year_id == school_year_id,
        ).all()
    except Exception:
        return {}

    out = {sid: {} for sid in student_ids}
    for row in rows:
        if not _standard_matches_subject(row.standard_id, subject_key):
            continue
        student_marks = out.setdefault(row.student_id, {})
        student_marks.setdefault(row.standard_id, {})[row.quarter] = row.mark
    return out


def upsert_mark(student_id, standard_id, school_year_id, quarter, mark, user_id=None):
    try:
        from extensions import db
        from models import GradeKStandardMark
    except Exception:
        return False
    if quarter not in QUARTER_COLUMNS:
        return False
    if not subject_for_standard(standard_id):
        return False

    row = GradeKStandardMark.query.filter_by(
        student_id=student_id,
        standard_id=standard_id,
        school_year_id=school_year_id,
        quarter=quarter,
    ).first()

    clean_mark = (mark or '').strip().upper()
    allowed = valid_marks_for_standard(standard_id)
    if clean_mark and clean_mark not in allowed:
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

    db.session.add(GradeKStandardMark(
        student_id=student_id,
        standard_id=standard_id,
        school_year_id=school_year_id,
        quarter=quarter,
        mark=clean_mark,
        updated_by=user_id,
    ))
    return True


def class_completeness(student_ids, school_year_id, subject_key):
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
        from models import GradeKStandardMark
        rows = GradeKStandardMark.query.filter(
            GradeKStandardMark.student_id.in_([int(s) for s in student_ids]),
            GradeKStandardMark.school_year_id == school_year_id,
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

    for stats in quarters.values():
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
    subject = SUBJECT_CATALOGS.get(subject_key)
    if not subject or not student_ids:
        return {}

    sections = []
    for section in subject['sections']:
        std_ids = [s['id'] for s in section.get('standards', [])]
        sections.append({
            'title': section.get('title') or '',
            'standard_ids': std_ids,
            'filled': 0,
            'total': len(student_ids) * len(std_ids),
        })

    try:
        from models import GradeKStandardMark
        rows = GradeKStandardMark.query.filter(
            GradeKStandardMark.student_id.in_([int(s) for s in student_ids]),
            GradeKStandardMark.school_year_id == school_year_id,
            GradeKStandardMark.quarter == quarter,
        ).all()
    except Exception:
        rows = []

    id_to_section = {}
    for idx, section in enumerate(sections):
        for sid in section['standard_ids']:
            id_to_section[sid] = idx

    for r in rows:
        idx = id_to_section.get(r.standard_id)
        if idx is not None:
            sections[idx]['filled'] += 1

    result = {}
    for section in sections:
        stats = {
            'filled': section['filled'],
            'total': section['total'],
            'percent': int(round(100 * section['filled'] / section['total'])) if section['total'] else 0,
        }
        result[section['title']] = stats
    return result


def copy_marks_from_previous_quarter(student_ids, school_year_id, subject_key, target_quarter, user_id=None):
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


def kindergarten_standards_context(report_card_data=None, student_id=None, school_year_id=None):
    saved = {}
    if isinstance(report_card_data, dict):
        saved = report_card_data.get('standards_marks') or {}

    all_marks = {}
    for key in SUBJECT_CATALOGS:
        all_marks[key] = _normalize_marks(saved.get(key) if isinstance(saved, dict) else {})

    if student_id and school_year_id:
        live = get_marks_for_student(student_id, school_year_id)
        for std_id, per_q in live.items():
            subject = subject_for_standard(std_id)
            if not subject:
                continue
            target = all_marks.setdefault(subject, {})
            existing = target.get(std_id, {q: '' for q in QUARTER_COLUMNS})
            for q in QUARTER_COLUMNS:
                v = per_q.get(q)
                if v:
                    existing[q] = v
            target[std_id] = existing

    # Flatten for templates that expect one marks dict
    flat = {}
    for subject_marks in all_marks.values():
        flat.update(subject_marks)

    return {
        'k_language_arts': KINDERGARTEN_LANGUAGE_ARTS,
        'k_math': KINDERGARTEN_MATH,
        'k_writing_level': KINDERGARTEN_WRITING_LEVEL,
        'k_skills': KINDERGARTEN_SKILLS,
        'k_work_habits': KINDERGARTEN_WORK_HABITS,
        'k_interventions': KINDERGARTEN_INTERVENTIONS,
        'k_marks': flat,
        'k_quarter_columns': QUARTER_COLUMNS,
        'k_scoring_key': [
            {'code': 'M', 'label': 'Mastered the standard'},
            {'code': 'N', 'label': 'Nearing mastery'},
            {'code': 'I', 'label': 'Improvement needed'},
            {'code': 'U', 'label': 'Unable to demonstrate understanding of standard'},
        ],
        'k_writing_stages': [
            {'level': '1', 'label': 'Pictures'},
            {'level': '2', 'label': 'Scribbles'},
            {'level': '3', 'label': 'Random Letters'},
            {'level': '4', 'label': 'Letters Represent Words'},
            {'level': '5', 'label': 'Beginning Sounds Represent Words'},
            {'level': '6', 'label': 'Kid Spelling'},
            {'level': '7', 'label': 'Kid Spelling with standard Spelling'},
        ],
    }
