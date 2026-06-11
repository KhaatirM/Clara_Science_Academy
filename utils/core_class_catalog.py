"""
Canonical core (non-elective) class list per grade for Clara Science Academy.

Used by the school-year class auto-setup tool and the manual setup guide.
Religious-language electives and other add-ons are excluded from auto-setup.

Broad subjects (stored on Class.subject): Math, History/Social Studies, Science,
Art, Music, Language Arts, Physical Education.

Class names use a short grade suffix (e.g. Math 2, Language Arts 1, Science K).
Middle-school science uses fixed titles (Introduction to Physics, Physics I,
Physics II) while subject remains Science.
"""

from __future__ import annotations

GRADE_LABELS = {
    0: 'Kindergarten',
    1: '1st Grade',
    2: '2nd Grade',
    3: '3rd Grade',
    4: '4th Grade',
    5: '5th Grade',
    6: '6th Grade',
    7: '7th Grade',
    8: '8th Grade',
}

SETUP_GRADE_LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8]

MIDDLE_SCHOOL_GRADE_MIN = 6
HISTORY_SOCIAL_STUDIES_GRADE_MIN = 2

HISTORY_SOCIAL_STUDIES_SUBJECT = 'History/Social Studies'

ELECTIVE_SUBJECTS = frozenset({
    'islamic studies',
    'islamic',
    'quran',
    "qur'an",
    'arabic',
    'elective',
})

_ART = {
    'display_name': 'Art',
    'subject': 'Art',
    'name_base': 'Art',
    'match_tokens': ('art',),
}
_MUSIC = {
    'display_name': 'Music',
    'subject': 'Music',
    'name_base': 'Music',
    'match_tokens': ('music', 'art/music'),
}
_PE = {
    'display_name': 'Physical Education',
    'subject': 'Physical Education',
    'name_base': 'PE',
    'match_tokens': ('physical education', 'pe', 'p.e.'),
}
_REQUIRED_ENRICHMENT = [_ART, _MUSIC, _PE]

_MATH = {
    'display_name': 'Math',
    'subject': 'Math',
    'name_base': 'Math',
    'match_tokens': ('math', 'mathematics'),
}
_SCIENCE = {
    'display_name': 'Science',
    'subject': 'Science',
    'name_base': 'Science',
    'match_tokens': ('science', 'physics', 'introduction to physics'),
}
_HISTORY = {
    'display_name': 'History',
    'subject': HISTORY_SOCIAL_STUDIES_SUBJECT,
    'name_base': 'History',
    'match_tokens': ('history', 'social studies', 'social'),
}
_SOCIAL_STUDIES = {
    'display_name': 'Social Studies',
    'subject': HISTORY_SOCIAL_STUDIES_SUBJECT,
    'name_base': 'Social Studies',
    'match_tokens': ('social studies', 'social', 'history'),
}
_ELA = {
    'display_name': 'Language Arts',
    'subject': 'Language Arts',
    'name_base': 'Language Arts',
    'match_tokens': (
        'language arts',
        'ela',
        'english language arts',
        'english',
        'reading',
        'writing',
        'spelling',
        'handwriting',
        'vocabulary',
        'reading comprehension',
    ),
}

_PHYSICS_6 = {
    'display_name': 'Introduction to Physics',
    'subject': 'Science',
    'fixed_class_name': 'Introduction to Physics',
    'match_tokens': ('introduction to physics', 'physics', 'science'),
}
_PHYSICS_7 = {
    'display_name': 'Physics I',
    'subject': 'Science',
    'fixed_class_name': 'Physics I',
    'match_tokens': ('physics i', 'physics 1', 'physics', 'science'),
}
_PHYSICS_8 = {
    'display_name': 'Physics II',
    'subject': 'Science',
    'fixed_class_name': 'Physics II',
    'match_tokens': ('physics ii', 'physics 2', 'physics', 'science'),
}


def _with_enrichment(entries: list[dict]) -> list[dict]:
    return entries + list(_REQUIRED_ENRICHMENT)


def _elementary_core(include_history: bool = False) -> list[dict]:
    core = [dict(_ELA), dict(_MATH), dict(_SCIENCE)]
    if include_history:
        core.append(dict(_HISTORY))
    return _with_enrichment(core)


def _middle_school_core(science_entry: dict) -> list[dict]:
    return _with_enrichment([
        dict(_ELA),
        dict(_MATH),
        science_entry,
        dict(_SOCIAL_STUDIES),
    ])


_CORE_BY_GRADE: dict[int, list[dict]] = {
    0: _elementary_core(include_history=False),
    1: _elementary_core(include_history=False),
    2: _elementary_core(include_history=True),
    3: _elementary_core(include_history=True),
}

_GRADES_4_5_CORE = _elementary_core(include_history=True)

for _g in (4, 5):
    _CORE_BY_GRADE[_g] = list(_GRADES_4_5_CORE)
_CORE_BY_GRADE[6] = _middle_school_core(dict(_PHYSICS_6))
_CORE_BY_GRADE[7] = _middle_school_core(dict(_PHYSICS_7))
_CORE_BY_GRADE[8] = _middle_school_core(dict(_PHYSICS_8))


def grade_name_suffix(grade_level: int) -> str:
    g = int(grade_level)
    return 'K' if g == 0 else str(g)


def setup_key_for_entry(entry: dict) -> str:
    if entry.get('setup_key'):
        return entry['setup_key']
    if entry.get('fixed_class_name'):
        return entry['subject']
    return entry['subject']


def class_name_for_grade(grade_level: int, entry: dict) -> str:
    if entry.get('fixed_class_name'):
        return entry['fixed_class_name']
    base = entry.get('name_base') or entry.get('display_name') or entry['subject']
    return f'{base} {grade_name_suffix(grade_level)}'


def grade_label(grade_level: int) -> str:
    return GRADE_LABELS.get(int(grade_level), f'Grade {grade_level}')


def is_middle_school_grade(grade_level: int) -> bool:
    return int(grade_level) >= MIDDLE_SCHOOL_GRADE_MIN


def catalog_entries_for_grade(grade_level: int) -> list[dict]:
    return list(_CORE_BY_GRADE.get(int(grade_level), []))


def all_catalog_entries(grade_levels=None) -> list[dict]:
    grades = grade_levels if grade_levels is not None else SETUP_GRADE_LEVELS
    out = []
    for g in grades:
        for entry in catalog_entries_for_grade(g):
            out.append({
                'grade_level': int(g),
                'grade_label': grade_label(g),
                'display_name': entry['display_name'],
                'subject': entry['subject'],
                'setup_key': setup_key_for_entry(entry),
                'match_tokens': entry.get('match_tokens', (entry['subject'].lower(),)),
                'suggested_name': class_name_for_grade(g, entry),
            })
    return out


def guide_by_grade() -> list[dict]:
    rows = []
    for g in SETUP_GRADE_LEVELS:
        entries = catalog_entries_for_grade(g)
        if not entries:
            continue
        rows.append({
            'grade_level': g,
            'grade_label': grade_label(g),
            'classes': [
                {'name': class_name_for_grade(g, e), 'subject': e['subject']}
                for e in entries
            ],
        })
    return rows


def is_elective_subject(subject: str | None) -> bool:
    if not subject:
        return False
    return subject.strip().lower() in ELECTIVE_SUBJECTS
