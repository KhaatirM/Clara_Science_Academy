"""Structured payloads for the post-save credential summary modal (students & staff)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from utils.student_login_policy import MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN, parse_grade_level_for_policy

_GRADE_LABELS = {
    0: "Kindergarten",
    1: "1st grade",
    2: "2nd grade",
    3: "3rd grade",
    4: "4th grade",
    5: "5th grade",
    6: "6th grade",
    7: "7th grade",
    8: "8th grade",
    9: "9th grade",
    10: "10th grade",
    11: "11th grade",
    12: "12th grade",
}


def grade_level_display(grade_level: Any) -> str:
    gl = parse_grade_level_for_policy(grade_level)
    if gl is None:
        return "Unknown grade"
    return _GRADE_LABELS.get(gl, f"Grade {gl}")


def student_k2_modal_payload(
    *,
    first_name: str,
    last_name: str,
    student_id: str,
    grade_level: Any,
    entrance_school_year: Optional[str] = None,
) -> Dict[str, Any]:
    """K–2: no portal or Workspace; explain promotion and admin handoff."""
    gl = parse_grade_level_for_policy(grade_level)
    years_until = None
    if gl is not None and gl < MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN:
        years_until = MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN - gl

    notes: List[str] = [
        "Kindergarten through 2nd grade are kept as directory records only: no student website login "
        "and no school Gmail address yet.",
        "When this student is promoted to 3rd grade in this system, a portal account and school email "
        "are created automatically (or on the next save if Google sync is configured).",
        "School Administrators and Directors receive an email when a new 3rd-grade login is provisioned "
        "so you can share credentials securely with the family. Until then, families do not use the student portal.",
        "If a student skips a grade or you need early access, edit the student and set grade to 3rd or higher, "
        "then use the credential summary to distribute logins.",
    ]
    if years_until is not None:
        notes.insert(
            0,
            f"This student is {years_until} academic year(s) away from 3rd grade under the usual progression "
            f"({grade_level_display(gl)} → 3rd). Exact dates depend on your school calendar.",
        )

    fields: List[Dict[str, Any]] = [
        {"label": "Student", "value": f"{first_name} {last_name}".strip()},
        {"label": "Student ID", "value": student_id or "—", "mono": True},
        {"label": "Current grade", "value": grade_level_display(gl)},
    ]
    if entrance_school_year:
        fields.append({"label": "Entrance school year", "value": entrance_school_year})

    return {
        "variant": "student_k2",
        "title": "Student saved — no login yet (K–2)",
        "subtitle": "Records only until 3rd grade",
        "fields": fields,
        "alerts": [
            {
                "type": "info",
                "text": "No passwords are generated for K–2. Use parent/guardian contact info on file for school communication.",
            }
        ],
        "notes": notes,
    }


def student_grade3_plus_modal_payload(
    *,
    first_name: str,
    last_name: str,
    student_id: str,
    username: str,
    portal_password: str,
    school_email: Optional[str],
    google_initial_password: str,
    google_user_created: Optional[bool] = None,
    google_warning: Optional[str] = None,
) -> Dict[str, Any]:
    fields: List[Dict[str, Any]] = [
        {"label": "Student", "value": f"{first_name} {last_name}".strip()},
        {"label": "Student ID", "value": student_id or "—", "mono": True},
        {"label": "Website username", "value": username, "mono": True},
        {"label": "Website (portal) temporary password", "value": portal_password, "mono": True},
    ]
    if school_email:
        fields.append({"label": "School email (Google)", "value": school_email, "mono": True})
        fields.append(
            {
                "label": "First Google sign-in password",
                "value": google_initial_password,
                "mono": True,
            }
        )
    else:
        fields.append({"label": "School email", "value": "Not generated — check grade or sync settings."})

    alerts: List[Dict[str, str]] = []
    if google_warning:
        alerts.append({"type": "warning", "text": google_warning})
    elif google_user_created is False and school_email:
        alerts.append(
            {
                "type": "warning",
                "text": "Google account may not exist yet in Admin Console. Verify Directory sync or create the user manually.",
            }
        )

    notes = [
        "The website password and the Google password are different. The student must change both on first sign-in.",
        "Share credentials through a secure channel (in person, password manager, or encrypted message)—not class-wide email.",
        "If anything looks wrong, edit the student, check the Users list, or contact Tech support before sharing with the family.",
    ]

    return {
        "variant": "student_grade_3_plus",
        "title": "Student account ready",
        "subtitle": "Copy these details before closing — they may not be shown again",
        "fields": fields,
        "alerts": alerts,
        "notes": notes,
    }


def staff_full_modal_payload(
    *,
    display_name: str,
    staff_id: str,
    role_label: str,
    username: str,
    portal_password: str,
    school_email: Optional[str],
    google_initial_password: str,
    personal_email: str,
    welcome_email_sent: bool,
    is_temporary: bool,
    access_expires_at: Optional[str] = None,
) -> Dict[str, Any]:
    fields: List[Dict[str, Any]] = [
        {"label": "Name", "value": display_name},
        {"label": "Role", "value": role_label},
        {"label": "Staff ID", "value": staff_id or "—", "mono": True},
        {"label": "Website username", "value": username, "mono": True},
        {"label": "Website (portal) temporary password", "value": portal_password, "mono": True},
        {"label": "Personal email (on file)", "value": personal_email, "mono": True},
    ]
    if school_email:
        fields.append({"label": "School email (Google)", "value": school_email, "mono": True})
        fields.append(
            {"label": "First Google sign-in password", "value": google_initial_password, "mono": True}
        )

    alerts: List[Dict[str, str]] = []
    if welcome_email_sent:
        alerts.append(
            {
                "type": "info",
                "text": f"A welcome message with the same details was sent to {personal_email} (if mail is configured).",
            }
        )
    else:
        alerts.append(
            {
                "type": "warning",
                "text": "Welcome email was not sent (check MAIL_PASSWORD / SMTP). Share credentials securely yourself.",
            }
        )

    if is_temporary and access_expires_at:
        alerts.append(
            {
                "type": "warning",
                "text": f"Temporary portal access expires on {access_expires_at}.",
            }
        )

    notes = [
        "Portal login is separate from Google sign-in; both passwords must be changed when prompted.",
        "If this person also uses Tech tools, they may need to pick the correct dashboard after login.",
    ]

    return {
        "variant": "staff_full",
        "title": "Staff account ready",
        "subtitle": "Website login + school email",
        "fields": fields,
        "alerts": alerts,
        "notes": notes,
    }


def staff_directory_only_modal_payload(
    *,
    display_name: str,
    staff_id: str,
    role_label: str,
    personal_email: str,
) -> Dict[str, Any]:
    return {
        "variant": "staff_directory_only",
        "title": "Staff saved — directory only",
        "subtitle": "No website login for this person",
        "fields": [
            {"label": "Name", "value": display_name},
            {"label": "Role", "value": role_label},
            {"label": "Staff ID", "value": staff_id or "—", "mono": True},
            {"label": "Personal email (on file)", "value": personal_email, "mono": True},
        ],
        "alerts": [
            {
                "type": "info",
                "text": "There is no portal username or password. You can still assign classes and sync Google later if you add a school email from Edit staff.",
            }
        ],
        "notes": [
            "To enable website login later, edit this staff member and turn on “Portal login,” then save.",
            "Unexpected outcome: if you expected a login, confirm the Portal login checkbox was selected on the add form.",
        ],
    }
