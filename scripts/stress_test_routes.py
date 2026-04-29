"""
Route smoke/stress tester.

Goal: hit every route for a given role and report 5xx crashes.
This is intentionally pragmatic: a route returning 403/404/302 is not a crash.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class HitResult:
    method: str
    path: str
    status: int
    location: Optional[str]


def _set_testing_env() -> None:
    # Ensure project root is importable when executing from /scripts
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)

    os.environ.setdefault("FLASK_ENV", "testing")
    # Avoid token-decrypt crashes if any template touches google_refresh_token.
    # (Fernet expects a urlsafe base64-encoded 32-byte key.)
    os.environ.setdefault("ENCRYPTION_KEY", "uZBvS2m_bqG3qg7lQm6oYqk8u6p8x0T0cU4x8rVYQ2I=")
    os.environ.setdefault("SECRET_KEY", "test-secret-key")


def _make_app():
    _set_testing_env()
    from app import create_app
    from config import TestingConfig

    return create_app(TestingConfig)


def _seed_minimal_fixtures(app) -> Dict[str, Any]:
    """
    Create a minimal DB state that lets many teacher routes render without 500s.
    We intentionally keep this small; missing objects should typically yield 404s, not 500s.
    """
    from extensions import db
    from models import (
        User,
        TeacherStaff,
        Student,
        SchoolYear,
        Class,
        Enrollment,
        Assignment,
        Grade,
        Submission,
    )
    from werkzeug.security import generate_password_hash

    with app.app_context():
        # Ensure tables exist (create_app already calls create_all, but keep safe for import variations)
        db.create_all()

        # School year is required by Class/Assignment
        sy = SchoolYear(
            name="2025-2026",
            start_date=date(2025, 8, 15),
            end_date=date(2026, 6, 15),
            is_active=True,
        )
        db.session.add(sy)
        db.session.flush()

        teacher_staff = TeacherStaff(
            first_name="Test",
            last_name="Teacher",
            email="teacher@example.com",
            department="Science",
            assigned_role="Teacher",
        )
        db.session.add(teacher_staff)
        db.session.flush()

        teacher_user = User(
            username="teacher1",
            password_hash=generate_password_hash("password123"),
            role="Teacher",
            teacher_staff_id=teacher_staff.id,
            email="teacher@example.com",
        )
        db.session.add(teacher_user)

        director_user = User(
            username="director1",
            password_hash=generate_password_hash("password123"),
            role="Director",
            email="director@example.com",
        )
        db.session.add(director_user)

        school_admin_user = User(
            username="admin1",
            password_hash=generate_password_hash("password123"),
            role="School Administrator",
            email="admin@example.com",
        )
        db.session.add(school_admin_user)

        tech_user = User(
            username="tech1",
            password_hash=generate_password_hash("password123"),
            role="Tech",
            email="tech@example.com",
        )
        db.session.add(tech_user)

        student = Student(
            first_name="Test",
            last_name="Student",
            dob="2013-01-01",
            grade_level=6,
            student_id="STU001",
        )
        db.session.add(student)
        db.session.flush()

        student_user = User(
            username="student1",
            password_hash=generate_password_hash("password123"),
            role="Student",
            student_id=student.id,
        )
        db.session.add(student_user)
        db.session.flush()

        cls = Class(
            name="Science 6",
            subject="Science",
            teacher_id=teacher_staff.id,
            school_year_id=sy.id,
            is_active=True,
        )
        db.session.add(cls)
        db.session.flush()

        enroll = Enrollment(student_id=student.id, class_id=cls.id, is_active=True)
        db.session.add(enroll)

        now = datetime.now(timezone.utc)
        asn = Assignment(
            title="Test Assignment",
            description="Fixture",
            class_id=cls.id,
            due_date=now + timedelta(days=7),
            open_date=now - timedelta(days=1),
            close_date=now + timedelta(days=8),
            quarter="Q1",
            semester="S1",
            school_year_id=sy.id,
            assignment_type="pdf",
            assignment_context="homework",
            total_points=100.0,
            status="Active",
            created_by=teacher_user.id,
        )
        db.session.add(asn)
        db.session.flush()

        grade = Grade(
            student_id=student.id,
            assignment_id=asn.id,
            grade_data='{"score": 85, "max_score": 100}',
        )
        db.session.add(grade)
        db.session.flush()

        sub = Submission(
            student_id=student.id,
            assignment_id=asn.id,
            submission_type="online",
            comments="fixture",
        )
        db.session.add(sub)
        db.session.flush()

        db.session.commit()

        # Return primitives only (avoid DetachedInstanceError outside app_context)
        return {
            "teacher_username": teacher_user.username,
            "teacher_password": "password123",
            "teacher_user_id": teacher_user.id,
            "teacher_staff_id": teacher_staff.id,
            "director_username": director_user.username,
            "director_password": "password123",
            "director_user_id": director_user.id,
            "school_admin_username": school_admin_user.username,
            "school_admin_password": "password123",
            "school_admin_user_id": school_admin_user.id,
            "tech_username": tech_user.username,
            "tech_password": "password123",
            "tech_user_id": tech_user.id,
            "student_user_id": student_user.id,
            "student_username": student_user.username,
            "student_password": "password123",
            "student_id": student.id,
            "class_id": cls.id,
            "assignment_id": asn.id,
            "grade_id": grade.id,
            "submission_id": sub.id,
            "school_year_id": sy.id,
        }


def _login(client, username: str, password: str) -> None:
    # Follow redirects so role dashboard wiring is exercised
    resp = client.post("/login", data={"username": username, "password": password}, follow_redirects=True)
    if resp.status_code >= 500:
        raise RuntimeError(f"Login crashed with {resp.status_code}")
    # Ensure we actually authenticated (avoid false-positive stress runs).
    with client.session_transaction() as sess:
        if not sess.get("_user_id"):
            raise RuntimeError(f"Login failed for {username!r} (no session user id set)")


_SKIP_PREFIXES = (
    "/static/",
)


def _is_rule_testable(rule) -> bool:
    if rule.rule.startswith(_SKIP_PREFIXES):
        return False
    # Skip cron/webhook/migration by default in role stress tests
    if rule.rule.startswith("/cron/") or rule.rule.startswith("/migrate/"):
        return False
    return True


def _build_path(rule: str, params: Dict[str, Any]) -> str:
    """
    Very small converter-substitution helper for Flask rules.
    Supports <int:name> and <path:name> and <name>.
    """

    def repl(m: re.Match[str]) -> str:
        conv = m.group("conv")
        name = m.group("name")
        if name in params:
            return str(params[name])
        if conv == "int":
            return "1"
        return "x"

    return re.sub(r"<(?:(?P<conv>[^:>]+):)?(?P<name>[^>]+)>", repl, rule)


def _iter_rules_with_prefix(app, prefix: str) -> Iterable[Tuple[str, Any]]:
    for rule in app.url_map.iter_rules():
        if not _is_rule_testable(rule):
            continue
        if rule.rule.startswith(prefix):
            yield (rule.rule, rule)


def _hit_rule(client, rule, path: str) -> List[HitResult]:
    hits: List[HitResult] = []
    methods = sorted([m for m in (rule.methods or set()) if m in {"GET", "POST"} and m != "HEAD"])
    for m in methods:
        try:
            if m == "GET":
                resp = client.get(path, follow_redirects=False)
            else:
                # Most POST routes in this codebase expect form data; give a minimal payload.
                resp = client.post(path, data={}, follow_redirects=False)
        except Exception as exc:
            # This is effectively a 500 at request dispatch time
            hits.append(HitResult(method=m, path=path, status=599, location=f"EXC:{exc}"))
            continue
        hits.append(HitResult(method=m, path=path, status=resp.status_code, location=resp.headers.get("Location")))
    return hits


def _stress_prefix(app, prefix: str, username: str, password: str, params: Dict[str, Any]) -> Tuple[List[HitResult], List[HitResult]]:
    client = app.test_client()
    _login(client, username, password)

    all_hits: List[HitResult] = []
    bad_5xx: List[HitResult] = []

    for rule_str, rule in _iter_rules_with_prefix(app, prefix):
        path = _build_path(rule_str, params)
        hits = _hit_rule(client, rule, path)
        all_hits.extend(hits)
        for h in hits:
            if h.status >= 500 or h.status == 599:
                bad_5xx.append(h)

    return all_hits, bad_5xx


def run_all_role_stress() -> Dict[str, Tuple[List[HitResult], List[HitResult]]]:
    results: Dict[str, Tuple[List[HitResult], List[HitResult]]] = {}

    # Run each role against a fresh in-memory app/DB so destructive POSTs can't
    # break later role logins or distort results.
    def _fresh():
        app = _make_app()
        fx = _seed_minimal_fixtures(app)
        params = {
            "class_id": fx["class_id"],
            "assignment_id": fx["assignment_id"],
            "student_id": fx["student_id"],
            "grade_id": fx["grade_id"],
            "submission_id": fx["submission_id"],
        }
        return app, fx, params

    app, fx, params = _fresh()
    results["teacher:/teacher"] = _stress_prefix(app, "/teacher", fx["teacher_username"], fx["teacher_password"], params)
    results["teacher:/communications"] = _stress_prefix(app, "/communications", fx["teacher_username"], fx["teacher_password"], params)

    app, fx, params = _fresh()
    results["director:/management"] = _stress_prefix(app, "/management", fx["director_username"], fx["director_password"], params)

    app, fx, params = _fresh()
    results["school_admin:/management"] = _stress_prefix(app, "/management", fx["school_admin_username"], fx["school_admin_password"], params)

    app, fx, params = _fresh()
    results["student:/student"] = _stress_prefix(app, "/student", fx["student_username"], fx["student_password"], params)

    app, fx, params = _fresh()
    results["tech:/tech"] = _stress_prefix(app, "/tech", fx["tech_username"], fx["tech_password"], params)

    return results


def main() -> int:
    results = run_all_role_stress()
    any_bad = False
    for label, (all_hits, bad) in results.items():
        print(f"{label} route hits: {len(all_hits)}")
        print(f"{label} 5xx crashes: {len(bad)}")
        for h in bad:
            print(f"CRASH {label} {h.method} {h.path} -> {h.status} {h.location or ''}")
        if bad:
            any_bad = True
    return 1 if any_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

