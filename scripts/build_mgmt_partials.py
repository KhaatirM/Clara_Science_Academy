"""One-off helper to build _management_students.html and _management_staff.html from extracted bodies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STU_HEAD = """{# Students hub — administrators & directors #}
{% set is_director = sidebar_role_canonical == 'Director' %}
{% set without_accounts = total_students - students_with_accounts %}

<div class="mgmt-stu container-fluid px-0 px-md-1">
  <div class="mgmt-stu-shell{% if is_director %} mgmt-stu-shell--director{% endif %}">

    <header class="mgmt-stu-hero">
      <div>
        <p class="mgmt-stu-eyebrow">Student records</p>
        <h1 class="mgmt-stu-title">Students</h1>
        <p class="mgmt-stu-subtitle">
          <i class="bi bi-people-fill" aria-hidden="true"></i>
          Manage enrollments, accounts, and academic records
        </p>
      </div>
      <div class="mgmt-stu-hero-actions">
        {% if is_director %}
        <span class="mgmt-stu-role-badge mgmt-stu-role-badge--director">
          <i class="bi bi-award-fill" aria-hidden="true"></i> Director
        </span>
        {% elif has_mgmt_role_access %}
        <span class="mgmt-stu-role-badge mgmt-stu-role-badge--admin">
          <i class="bi bi-shield-fill" aria-hidden="true"></i> Administrator
        </span>
        {% endif %}
        <a href="{{ url_for('management.add_student') }}" class="mgmt-stu-btn mgmt-stu-btn--primary">
          <i class="bi bi-plus-circle" aria-hidden="true"></i> Add student
        </a>
        <a href="{{ url_for('management.management_dashboard') }}" class="mgmt-stu-btn mgmt-stu-btn--ghost">
          <i class="bi bi-house-door" aria-hidden="true"></i> Dashboard
        </a>
      </div>
    </header>

    <div class="mgmt-stu-insights" role="list">
      <div class="mgmt-stu-insight" role="listitem">
        <span class="mgmt-stu-insight-icon"><i class="bi bi-people-fill" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stu-insight-value">{{ total_students }}</div>
          <div class="mgmt-stu-insight-label">Total students</div>
        </div>
      </div>
      <div class="mgmt-stu-insight" role="listitem">
        <span class="mgmt-stu-insight-icon"><i class="bi bi-person-check-fill" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stu-insight-value">{{ students_with_accounts }}</div>
          <div class="mgmt-stu-insight-label">With accounts</div>
        </div>
      </div>
      <div class="mgmt-stu-insight" role="listitem">
        <span class="mgmt-stu-insight-icon"><i class="bi bi-person-x-fill" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stu-insight-value">{{ without_accounts }}</div>
          <div class="mgmt-stu-insight-label">Without accounts</div>
        </div>
      </div>
      <div class="mgmt-stu-insight" role="listitem">
        <span class="mgmt-stu-insight-icon"><i class="bi bi-funnel" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stu-insight-value">{{ students|length }}</div>
          <div class="mgmt-stu-insight-label">On this page</div>
        </div>
      </div>
    </div>

    <div class="mgmt-stu-content">
"""

STU_FOOT = """
    </div>
  </div>
</div>
"""

STF_HEAD = """{# Staff hub — administrators & directors #}
{% set is_director = sidebar_role_canonical == 'Director' %}
{% set teachers_mode = teachers_view|default('manage') %}

<div class="mgmt-stf container-fluid px-0 px-md-1">
  <div class="mgmt-stf-shell{% if is_director %} mgmt-stf-shell--director{% endif %}">

    <header class="mgmt-stf-hero">
      <div>
        <p class="mgmt-stf-eyebrow">People operations</p>
        <h1 class="mgmt-stf-title">Teachers &amp; staff</h1>
        <p class="mgmt-stf-subtitle">
          {% if teachers_mode == 'directory' and can_staff_admin_ui %}
          <i class="bi bi-archive" aria-hidden="true"></i>
          Browse payroll roster and inactive records
          {% else %}
          <i class="bi bi-briefcase" aria-hidden="true"></i>
          Search, add, and maintain active staff records
          {% endif %}
        </p>
      </div>
      <div class="mgmt-stf-hero-actions">
        {% if is_director %}
        <span class="mgmt-stf-role-badge mgmt-stf-role-badge--director">
          <i class="bi bi-award-fill" aria-hidden="true"></i> Director
        </span>
        {% elif has_mgmt_role_access %}
        <span class="mgmt-stf-role-badge mgmt-stf-role-badge--admin">
          <i class="bi bi-shield-fill" aria-hidden="true"></i> Administrator
        </span>
        {% endif %}
        {% if can_staff_admin_ui %}
        <div class="mgmt-stf-mode-pills nav nav-pills">
          <a class="nav-link {% if teachers_mode != 'directory' %}active{% endif %}" href="{{ url_for('management.teachers') }}">
            <i class="bi bi-sliders"></i> Manage
          </a>
          <a class="nav-link {% if teachers_mode == 'directory' %}active{% endif %}" href="{{ url_for('management.teachers', teachers_view='directory', staff_dir_tab='current', staff_dir_q='') }}">
            <i class="bi bi-people"></i> Roster
          </a>
        </div>
        {% endif %}
        {% if teachers_mode != 'directory' %}
        <a href="{{ url_for('management.add_teacher_staff') }}" class="mgmt-stf-btn mgmt-stf-btn--primary">
          <i class="bi bi-plus-circle" aria-hidden="true"></i> Add staff
        </a>
        {% endif %}
        <a href="{{ url_for('management.management_dashboard') }}" class="mgmt-stf-btn mgmt-stf-btn--ghost">
          <i class="bi bi-house-door" aria-hidden="true"></i> Dashboard
        </a>
      </div>
    </header>

    {% if teachers_mode != 'directory' %}
    <div class="mgmt-stf-insights" role="list">
      <div class="mgmt-stf-insight" role="listitem">
        <span class="mgmt-stf-insight-icon"><i class="bi bi-people-fill" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stf-insight-value">{{ total_teachers or teachers|length }}</div>
          <div class="mgmt-stf-insight-label">Total staff</div>
        </div>
      </div>
      <div class="mgmt-stf-insight" role="listitem">
        <span class="mgmt-stf-insight-icon"><i class="bi bi-person-check-fill" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stf-insight-value">{{ teachers_with_accounts or 0 }}</div>
          <div class="mgmt-stf-insight-label">With accounts</div>
        </div>
      </div>
      <div class="mgmt-stf-insight" role="listitem">
        <span class="mgmt-stf-insight-icon"><i class="bi bi-person-x-fill" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stf-insight-value">{{ teachers_without_accounts or 0 }}</div>
          <div class="mgmt-stf-insight-label">Without accounts</div>
        </div>
      </div>
      <div class="mgmt-stf-insight" role="listitem">
        <span class="mgmt-stf-insight-icon"><i class="bi bi-calendar-check" aria-hidden="true"></i></span>
        <div>
          <div class="mgmt-stf-insight-value">{{ teachers|selectattr('employment_type', 'equalto', 'Full Time')|list|length }}</div>
          <div class="mgmt-stf-insight-label">Full time</div>
        </div>
      </div>
    </div>
    {% endif %}

    <div class="mgmt-stf-content">
"""

STF_FOOT = """
    </div>
  </div>
</div>
"""


def dedent_lines(lines):
    out = []
    for line in lines:
        if line.startswith("            "):
            out.append(line[12:])
        elif line.startswith("        "):
            out.append(line[8:])
        else:
            out.append(line)
    return out


def trim_trailing_container(lines):
    lines = list(lines)
    while lines and lines[-1].strip() in ("</div>", ""):
        if lines[-1].strip() == "</div>":
            lines.pop()
            break
        lines.pop()
    return lines


def main():
    stu_body = (ROOT / "templates/management/_management_students_body.html").read_text(encoding="utf-8").splitlines(keepends=True)
    stu_content = trim_trailing_container(stu_body[59:])
    (ROOT / "templates/management/_management_students.html").write_text(
        STU_HEAD + "".join(dedent_lines(stu_content)) + STU_FOOT, encoding="utf-8"
    )

    stf_body = (ROOT / "templates/management/_management_staff_body.html").read_text(encoding="utf-8").splitlines(keepends=True)
    start = 42
    if start < len(stf_body) and "Statistics Cards" in stf_body[start]:
        for i, line in enumerate(stf_body):
            if "<!-- Search & Filter Section -->" in line or "{% else %}" in line.strip():
                start = i
                break
    stf_content = trim_trailing_container(stf_body[start:])
    (ROOT / "templates/management/_management_staff.html").write_text(
        STF_HEAD + "".join(dedent_lines(stf_content)) + STF_FOOT, encoding="utf-8"
    )
    print("done")


if __name__ == "__main__":
    main()
