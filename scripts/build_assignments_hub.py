"""Wrap assignments_and_grades.html in management hub shell."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "templates/management/assignments_and_grades.html"
PARTIAL = ROOT / "templates/management/_management_assignments_and_grades.html"
WRAPPER = SRC

HERO_START = """{# Assignments & grades hub #}
{% set is_director = sidebar_role_canonical == 'Director' %}
{% set use_management_assignments_urls = (request.blueprint == 'management') %}
{% set bulk_void_use_mgmt_urls = current_user.role in ['Director', 'School Administrator'] or has_perm('assignments_grades:manage') %}
{% set bulk_void_enrolled_class_id = selected_class.id if selected_class else 0 %}

<div class="mgmt-asg container-fluid px-0 px-md-1">
  <div class="mgmt-asg-shell{% if is_director %} mgmt-asg-shell--director{% endif %}">

    <header class="mgmt-asg-hero">
      <div>
        <p class="mgmt-asg-eyebrow">Assignments &amp; grades</p>
        <h1 class="mgmt-asg-title">
          {% if show_class_selection %}Assignments &amp; grades{% else %}{{ selected_class.name if selected_class else 'Assignments &amp; grades' }}{% endif %}
        </h1>
        <p class="mgmt-asg-subtitle">
          <i class="bi bi-clipboard-data" aria-hidden="true"></i>
          {% if show_class_selection %}Select a class to view and manage assignments{% else %}Manage assignments and grades for this class{% endif %}
        </p>
      </div>
      <div class="mgmt-asg-hero-actions">
        {% if is_director %}
        <span class="mgmt-asg-role-badge mgmt-asg-role-badge--director"><i class="bi bi-award-fill"></i> Director</span>
        {% elif has_mgmt_role_access %}
        <span class="mgmt-asg-role-badge mgmt-asg-role-badge--admin"><i class="bi bi-shield-fill"></i> Administrator</span>
        {% endif %}
        {% if not show_class_selection %}
        <a href="{{ url_for('management.assignments_and_grades') }}" class="mgmt-asg-btn mgmt-asg-btn--ghost"><i class="bi bi-arrow-left"></i> All classes</a>
        {% endif %}
        <a href="{% if use_management_assignments_urls %}{{ url_for('management.redo_dashboard') }}{% else %}{{ url_for('teacher.redo_dashboard') }}{% endif %}" class="mgmt-asg-btn mgmt-asg-btn--ghost">
          <i class="bi bi-arrow-repeat"></i> Redo{% if redo_request_count and redo_request_count > 0 %}<span class="mgmt-asg-count-badge">{{ redo_request_count }}</span>{% endif %}
        </a>
        <a href="{% if use_management_assignments_urls %}{{ url_for('management.view_extension_requests') }}{% else %}{{ url_for('teacher.view_extension_requests') }}{% endif %}" class="mgmt-asg-btn mgmt-asg-btn--ghost">
          <i class="bi bi-clock-history"></i> Extensions{% if extension_request_count and extension_request_count > 0 %}<span class="mgmt-asg-count-badge">{{ extension_request_count }}</span>{% endif %}
        </a>
        {% if selected_class %}
        <a href="{{ url_for('teacher.assignments.pending_assistant_assignments', class_id=selected_class.id) }}" class="mgmt-asg-btn mgmt-asg-btn--ghost">
          <i class="bi bi-person-badge"></i> Proposals{% if pending_assistant_count and pending_assistant_count > 0 %}<span class="mgmt-asg-count-badge">{{ pending_assistant_count }}</span>{% endif %}
        </a>
        {% endif %}
        {% if selected_class and (use_management_assignments_urls or 'Teacher' in (current_user.role or '') or can_assignments_admin_ui) %}
        <button type="button" class="mgmt-asg-btn mgmt-asg-btn--ghost" data-bs-toggle="modal" data-bs-target="#bulkVoidModal"><i class="bi bi-slash-circle"></i> Bulk void</button>
        {% endif %}
        <button type="button" class="mgmt-asg-btn mgmt-asg-btn--primary" onclick="createAssignment()"><i class="bi bi-plus-circle"></i> New assignment</button>
      </div>
    </header>

    {% if show_class_selection %}
    <div class="mgmt-asg-insights" role="list">
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-house-door-fill"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ accessible_classes|length }}</div><div class="mgmt-asg-insight-label">Classes</div></div>
      </div>
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-journal-check"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ class_assignments.values()|sum }}</div><div class="mgmt-asg-insight-label">Assignments</div></div>
      </div>
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-people-fill"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ unique_student_count or 0 }}</div><div class="mgmt-asg-insight-label">Students</div></div>
      </div>
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-person-badge"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ accessible_classes|map(attribute='teacher')|select|unique|list|length }}</div><div class="mgmt-asg-insight-label">Teachers</div></div>
      </div>
    </div>
    {% elif selected_class %}
    <div class="mgmt-asg-insights" role="list">
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-journal-text"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ class_assignments|length + (group_assignments|length if group_assignments else 0) }}</div><div class="mgmt-asg-insight-label">Total assignments</div></div>
      </div>
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-check-circle"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ class_assignments|selectattr('status', 'equalto', 'Active')|list|length }}</div><div class="mgmt-asg-insight-label">Active</div></div>
      </div>
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-hourglass-split"></i></span>
        <div><div class="mgmt-asg-insight-value">{{ enrolled_students|length if enrolled_students is defined else 0 }}</div><div class="mgmt-asg-insight-label">Students</div></div>
      </div>
      <div class="mgmt-asg-insight" role="listitem">
        <span class="mgmt-asg-insight-icon"><i class="bi bi-graph-up"></i></span>
        <div>
          <div class="mgmt-asg-insight-value">
            {% set total_avg = 0 %}{% set count = 0 %}
            {% if assignment_grades %}
            {% for grade_info in assignment_grades.values() %}
              {% if grade_info.average_score > 0 %}{% set total_avg = total_avg + grade_info.average_score %}{% set count = count + 1 %}{% endif %}
            {% endfor %}
            {% endif %}
            {% if count > 0 %}{{ (total_avg / count)|round(1) }}%{% else %}N/A{% endif %}
          </div>
          <div class="mgmt-asg-insight-label">Avg score</div>
        </div>
      </div>
    </div>
    {% endif %}

    <div class="mgmt-asg-content">
"""

FOOTER = """
    </div>
  </div>
</div>
"""


def main():
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    start = None
    end = None
    for i, line in enumerate(lines):
        if start is None and '<div class="container-fluid px-2 px-md-4">' in line:
            start = i
        if '{% endblock %}' in line and start is not None and i > start + 10:
            end = i
            break
    if start is None or end is None:
        raise SystemExit(f"markers not found: {start}, {end}")

    body_lines = []
    skip_until = None
    for i in range(start, end):
        line = lines[i]
        # skip old header block (container open through header closing div before show_class_selection stats)
        if i == start:
            continue  # skip container-fluid open
        if '<!-- Modern Assignments Header -->' in line:
            skip_until = 'assignments-admin-header'
            continue
        if skip_until:
            if '</div>' in line and 'assignments-admin-header' in ''.join(lines[max(start,i-25):i]):
                pass
            # skip until we've passed the header section - detect line 79 area `</div>\n` after btn-assignments-add
        if '<!-- Statistics Cards -->' in line and 'show_class_selection' in ''.join(lines[i:i+5]):
            skip_until = 'stats_selection'
            continue
        if skip_until == 'stats_selection' and '<!-- Classes Grid -->' in line:
            skip_until = None
            body_lines.append(line)
            continue
        if '<!-- Quick Stats Cards -->' in line:
            skip_until = 'stats_class'
            continue
        if skip_until == 'stats_class' and '<!-- View Toggle Buttons -->' in line:
            skip_until = None
            body_lines.append(line)
            continue
        if skip_until == 'assignments-admin-header':
            if '{% if show_class_selection %}' in line:
                skip_until = None
                body_lines.append(line)
            continue
        if skip_until in ('stats_selection', 'stats_class'):
            continue
        body_lines.append(line)

    partial = HERO_START + "".join(body_lines) + FOOTER
    PARTIAL.write_text(partial, encoding="utf-8")

    wrapper = """{% extends "shared/dashboard_layout.html" %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/assignments.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_assignments.css') }}?v=1">
<link rel="stylesheet" href="{{ url_for('static', filename='css/assistant_approval.css') }}">
{% endblock %}

{% block title %}Assignments & Grades Management{% endblock %}

{% block dashboard_content %}
{% include 'management/_management_assignments_and_grades.html' %}
{% endblock %}
"""
    WRAPPER.write_text(wrapper, encoding="utf-8")
    print("built partial and wrapper", len(body_lines), "body lines")


if __name__ == "__main__":
    main()
