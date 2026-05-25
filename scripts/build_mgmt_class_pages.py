"""Build management class hub partials and scoped CSS."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates/management"
CSS = ROOT / "static/css"

ACCENT_OLD = [
    ("#4facfe", "#0d9488"),
    ("#00f2fe", "#14b8a6"),
    ("#667eea", "#0d9488"),
    ("#764ba2", "#0f766e"),
    ("rgba(79, 172, 254", "rgba(13, 148, 136"),
    ("#4285f4", "#0d9488"),
]


def shell_css(p: str, title: str) -> str:
    return f"""/* {title} — matches management home / report cards */
.{p} {{
  --{p}-bg: var(--hub-mgmt-bg, linear-gradient(165deg, #e8f0ec 0%, #dce8e4 45%, #d4e2de 100%));
  --{p}-surface: var(--hub-surface, rgba(255, 255, 255, 0.94));
  --{p}-border: var(--hub-border, rgba(255, 255, 255, 0.92));
  --{p}-text: var(--hub-text, #0f172a);
  --{p}-muted: var(--hub-muted, #64748b);
  --{p}-accent: var(--hub-mgmt-accent, #0d9488);
  --{p}-accent-deep: var(--hub-mgmt-accent-deep, #0f766e);
  --{p}-accent-soft: var(--hub-mgmt-accent-soft, rgba(13, 148, 136, 0.12));
  --{p}-radius: 20px;
  padding: 0 0 2rem;
}}
.{p}-shell {{
  background: var(--{p}-bg);
  border-radius: 24px;
  padding: clamp(1.25rem, 3vw, 2rem);
  margin: 0 -0.25rem;
}}
.{p}-shell--director {{
  --{p}-accent: var(--hub-mgmt-director-accent, #7c3aed);
  --{p}-accent-deep: var(--hub-mgmt-director-accent-deep, #6d28d9);
  --{p}-accent-soft: var(--hub-mgmt-director-accent-soft, rgba(124, 58, 237, 0.12));
  --{p}-bg: var(--hub-mgmt-director-bg, linear-gradient(165deg, #f0ecf5 0%, #e8e4f0 45%, #e2dce8 100%));
}}
.{p}-hero {{
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}}
.{p}-eyebrow {{
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--{p}-muted);
  margin: 0 0 0.35rem;
}}
.{p}-title {{
  font-size: clamp(1.45rem, 3.2vw, 1.9rem);
  font-weight: 800;
  color: var(--{p}-text);
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin: 0 0 0.4rem;
}}
.{p}-subtitle {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.92rem;
  color: var(--{p}-muted);
  margin: 0;
}}
.{p}-hero-actions {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}}
.{p}-role-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
}}
.{p}-role-badge--director {{
  background: linear-gradient(135deg, #ede9fe, #ddd6fe);
  color: #5b21b6;
  border: 1px solid rgba(124, 58, 237, 0.2);
}}
.{p}-role-badge--admin {{
  background: linear-gradient(135deg, #ccfbf1, #99f6e4);
  color: #115e59;
  border: 1px solid rgba(13, 148, 136, 0.25);
}}
.{p}-btn {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s, filter 0.15s;
}}
.{p}-btn--ghost {{
  color: #334155;
  background: var(--{p}-surface);
  border-color: rgba(148, 163, 184, 0.35);
}}
.{p}-btn--ghost:hover {{
  background: #fff;
  border-color: var(--{p}-accent);
  color: var(--{p}-accent-deep);
}}
.{p}-btn--primary {{
  color: #fff;
  background: linear-gradient(135deg, var(--{p}-accent), var(--{p}-accent-deep));
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2);
}}
.{p}-btn--primary:hover {{
  color: #fff;
  filter: brightness(1.05);
}}
.{p}-insights {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}}
@media (min-width: 768px) {{
  .{p}-insights {{ grid-template-columns: repeat(4, 1fr); }}
}}
.{p}-insight {{
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.85rem 1rem;
  background: var(--{p}-surface);
  border: 1px solid var(--{p}-border);
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}}
.{p}-insight-icon {{
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  background: var(--{p}-accent-soft);
  color: var(--{p}-accent-deep);
}}
.{p}-insight-value {{
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--{p}-text);
  line-height: 1.2;
}}
.{p}-insight-label {{
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--{p}-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 0.15rem;
}}
.{p}-content {{
  display: flex;
  flex-direction: column;
  gap: 1rem;
}}
"""


def scope_css(text: str, prefix: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.endswith("{") and not stripped.startswith("@") and not stripped.startswith("/*"):
            sel = stripped[:-1].strip()
            if sel.startswith(".") or sel.startswith("#"):
                line = f"{prefix} {sel} {{"
        for old, new in ACCENT_OLD:
            line = line.replace(old, new)
        lines.append(line)
    return "\n".join(lines)


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_content(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start:end])


def wrap_partial(
    prefix: str,
    eyebrow: str,
    title: str,
    subtitle_icon: str,
    subtitle: str,
    insights_html: str,
    hero_actions: str,
    body: str,
) -> str:
    p = prefix
    return f"""{{# Management hub — administrators & directors #}}
{{% set is_director = sidebar_role_canonical == 'Director' %}}

<div class="{p} container-fluid px-0 px-md-1">
  <div class="{p}-shell{{% if is_director %}} {p}-shell--director{{% endif %}}">

    <header class="{p}-hero">
      <div>
        <p class="{p}-eyebrow">{eyebrow}</p>
        <h1 class="{p}-title">{title}</h1>
        <p class="{p}-subtitle">
          <i class="bi {subtitle_icon}" aria-hidden="true"></i>
          {subtitle}
        </p>
      </div>
      <div class="{p}-hero-actions">
        {{% if is_director %}}
        <span class="{p}-role-badge {p}-role-badge--director">
          <i class="bi bi-award-fill" aria-hidden="true"></i> Director
        </span>
        {{% elif has_mgmt_role_access %}}
        <span class="{p}-role-badge {p}-role-badge--admin">
          <i class="bi bi-shield-fill" aria-hidden="true"></i> Administrator
        </span>
        {{% endif %}}
{hero_actions}
      </div>
    </header>

{insights_html}
    <div class="{p}-content">
{body}
    </div>
  </div>
</div>
"""


def build_classes():
    src = TPL / "enhanced_classes.html"
    lines = read_lines(src)
    # filters through grid (skip header + stats)
    body = slice_content(lines, 79, 276)  # enhanced-filters .. end grid container
    modal_script = slice_content(lines, 278, 562)  # modal + scripts

    total_enroll = "{{ classes|map(attribute='enrollments')|map('selectattr', 'is_active')|map('list')|map('length')|sum }}"
    teachers = "{{ classes|map(attribute='teacher')|select|unique|list|length }}"
    assignments = "{{ classes|map(attribute='assignments')|map('list')|map('length')|sum }}"

    insights = f"""    <div class="mgmt-cls-insights" role="list">
      <div class="mgmt-cls-insight" role="listitem">
        <span class="mgmt-cls-insight-icon"><i class="bi bi-house-door-fill"></i></span>
        <div><div class="mgmt-cls-insight-value">{{{{ classes|length }}}}</div><div class="mgmt-cls-insight-label">Total classes</div></div>
      </div>
      <div class="mgmt-cls-insight" role="listitem">
        <span class="mgmt-cls-insight-icon"><i class="bi bi-people-fill"></i></span>
        <div><div class="mgmt-cls-insight-value">{total_enroll}</div><div class="mgmt-cls-insight-label">Enrollments</div></div>
      </div>
      <div class="mgmt-cls-insight" role="listitem">
        <span class="mgmt-cls-insight-icon"><i class="bi bi-person-badge"></i></span>
        <div><div class="mgmt-cls-insight-value">{teachers}</div><div class="mgmt-cls-insight-label">Teachers</div></div>
      </div>
      <div class="mgmt-cls-insight" role="listitem">
        <span class="mgmt-cls-insight-icon"><i class="bi bi-journal-check"></i></span>
        <div><div class="mgmt-cls-insight-value">{assignments}</div><div class="mgmt-cls-insight-label">Assignments</div></div>
      </div>
    </div>
"""

    hero_actions = """        {% if has_mgmt_role_access %}
        <button type="button" class="mgmt-cls-btn mgmt-cls-btn--primary" data-bs-toggle="modal" data-bs-target="#createClassModal">
          <i class="bi bi-plus-circle" aria-hidden="true"></i> Create class
        </button>
        {% endif %}
        <a href="{{ url_for('management.management_dashboard') }}" class="mgmt-cls-btn mgmt-cls-btn--ghost">
          <i class="bi bi-house-door" aria-hidden="true"></i> Dashboard
        </a>"""

    partial = wrap_partial(
        "mgmt-cls",
        "Course catalog",
        "Classes",
        "bi-book",
        "Manage classes, schedules, and enrollments",
        insights,
        hero_actions,
        body + "\n" + modal_script,
    )
    (TPL / "_management_classes.html").write_text(partial, encoding="utf-8")

    rd = (CSS / "management_role_dashboard.css").read_text(encoding="utf-8")
    start = rd.find("CLASSES TAB STYLES")
    end = rd.find("TEACHERS TAB STYLES", start)
    block = rd[start:end] if start >= 0 else ""
    enh = (CSS / "management_enhanced_classes.css").read_text(encoding="utf-8")
    out = shell_css("mgmt-cls", "Classes hub") + "\n\n" + scope_css(block + "\n" + enh, ".mgmt-cls-content")
    (CSS / "management_admin_classes.css").write_text(out, encoding="utf-8")


def build_view_class():
    src = TPL / "view_class.html"
    lines = read_lines(src)
    body = slice_content(lines, 26, 363)  # alerts through announcement include

    insights = """    <div class="mgmt-vc-insights" role="list">
      <div class="mgmt-vc-insight" role="listitem">
        <span class="mgmt-vc-insight-icon"><i class="bi bi-people-fill"></i></span>
        <div><div class="mgmt-vc-insight-value">{{ enrolled_students|length }}</div><div class="mgmt-vc-insight-label">Students</div></div>
      </div>
      <div class="mgmt-vc-insight" role="listitem">
        <span class="mgmt-vc-insight-icon"><i class="bi bi-journal-text"></i></span>
        <div><div class="mgmt-vc-insight-value">{{ assignment_count|default(assignments|length) }}</div><div class="mgmt-vc-insight-label">Assignments</div></div>
      </div>
      <div class="mgmt-vc-insight" role="listitem">
        <span class="mgmt-vc-insight-icon"><i class="bi bi-person-badge"></i></span>
        <div><div class="mgmt-vc-insight-value">{% if teacher %}1{% else %}0{% endif %}</div><div class="mgmt-vc-insight-label">Teacher</div></div>
      </div>
      <div class="mgmt-vc-insight" role="listitem">
        <span class="mgmt-vc-insight-icon"><i class="bi bi-mortarboard"></i></span>
        <div><div class="mgmt-vc-insight-value">{{ class_info.get_grade_levels_display() or 'All' }}</div><div class="mgmt-vc-insight-label">Grades</div></div>
      </div>
    </div>
"""

    hero_actions = """        <a href="{{ url_for('management.manage_class_roster', class_id=class_info.id) }}" class="mgmt-vc-btn mgmt-vc-btn--ghost">
          <i class="bi bi-people" aria-hidden="true"></i> Roster
        </a>
        <a href="{{ url_for('management.class_grades', class_id=class_info.id) }}" class="mgmt-vc-btn mgmt-vc-btn--ghost">
          <i class="bi bi-graph-up" aria-hidden="true"></i> Grades
        </a>
        <a href="{{ url_for('management.edit_class', class_id=class_info.id) }}" class="mgmt-vc-btn mgmt-vc-btn--ghost">
          <i class="bi bi-pencil" aria-hidden="true"></i> Edit
        </a>
        <a href="{{ url_for('management.classes') }}" class="mgmt-vc-btn mgmt-vc-btn--primary">
          <i class="bi bi-grid" aria-hidden="true"></i> All classes
        </a>"""

    partial = wrap_partial(
        "mgmt-vc",
        "Class overview",
        "{{ class_info.name }}",
        "bi-building",
        "{{ class_info.subject }} · {{ class_info.get_grade_levels_display() or 'All grades' }}",
        insights,
        hero_actions,
        body,
    )
    (TPL / "_management_view_class.html").write_text(partial, encoding="utf-8")

    vc_css = (CSS / "management_view_class.css").read_text(encoding="utf-8")
    out = shell_css("mgmt-vc", "View class") + "\n\n" + scope_css(vc_css, ".mgmt-vc-content")
    (CSS / "management_admin_view_class.css").write_text(out, encoding="utf-8")


def build_roster():
    src = TPL / "_recover_roster.html"
    if not src.exists():
        src = TPL / "manage_class_roster.html"
    lines = read_lines(src)
    dash = next(i for i, l in enumerate(lines) if "{% block dashboard_content %}" in l)
    end = len(lines)
    for i in range(dash + 1, len(lines)):
        if lines[i].strip() == "{% endblock %}":
            end = i
            break
    body = slice_content(lines, 113, end)

    cap_pct = "{{ ((enrolled_students|length / class_info.max_students) * 100)|round if class_info.max_students else 0 }}"
    insights = f"""    <div class="mgmt-rst-insights" role="list">
      <div class="mgmt-rst-insight" role="listitem">
        <span class="mgmt-rst-insight-icon"><i class="bi bi-people-fill"></i></span>
        <div><div class="mgmt-rst-insight-value">{{{{ enrolled_students|length }}}}</div><div class="mgmt-rst-insight-label">Enrolled</div></div>
      </div>
      <div class="mgmt-rst-insight" role="listitem">
        <span class="mgmt-rst-insight-icon"><i class="bi bi-person-check-fill"></i></span>
        <div><div class="mgmt-rst-insight-value">{{{{ (enrolled_students|selectattr('user')|list)|length }}}}</div><div class="mgmt-rst-insight-label">With accounts</div></div>
      </div>
      <div class="mgmt-rst-insight" role="listitem">
        <span class="mgmt-rst-insight-icon"><i class="bi bi-diagram-3-fill"></i></span>
        <div><div class="mgmt-rst-insight-value">{cap_pct}%</div><div class="mgmt-rst-insight-label">Capacity</div></div>
      </div>
      <div class="mgmt-rst-insight" role="listitem">
        <span class="mgmt-rst-insight-icon"><i class="bi bi-door-open"></i></span>
        <div><div class="mgmt-rst-insight-value">{{{{ class_info.max_students }}}}</div><div class="mgmt-rst-insight-label">Max seats</div></div>
      </div>
    </div>
"""

    hero_actions = """        <a href="{{ url_for('management.class_grades', class_id=class_info.id) }}" class="mgmt-rst-btn mgmt-rst-btn--ghost">
          <i class="bi bi-graph-up" aria-hidden="true"></i> Grades
        </a>
        <a href="{{ url_for('management.view_class', class_id=class_info.id) }}" class="mgmt-rst-btn mgmt-rst-btn--ghost">
          <i class="bi bi-building" aria-hidden="true"></i> Class view
        </a>
        <a href="{{ url_for('management.classes') }}" class="mgmt-rst-btn mgmt-rst-btn--primary">
          <i class="bi bi-grid" aria-hidden="true"></i> All classes
        </a>"""

    partial = wrap_partial(
        "mgmt-rst",
        "Enrollment",
        "{{ class_info.name }}",
        "bi-people-fill",
        "{{ class_info.subject }} · manage who is in this class",
        insights,
        hero_actions,
        body.rstrip(),
    )
    (TPL / "_management_class_roster.html").write_text(partial, encoding="utf-8")

    rst_css = (CSS / "management_manage_class_roster.css").read_text(encoding="utf-8")
    out = shell_css("mgmt-rst", "Class roster") + "\n\n" + scope_css(rst_css, ".mgmt-rst-content")
    (CSS / "management_admin_class_roster.css").write_text(out, encoding="utf-8")


def build_grades():
    src = TPL / "class_grades.html"
    lines = read_lines(src)
    # find end of dashboard_content
    end = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "{% endblock %}" and i > 10:
            end = i
            break
    body = slice_content(lines, 72, end)

    insights = """    <div class="mgmt-grd-insights" role="list">
      <div class="mgmt-grd-insight" role="listitem">
        <span class="mgmt-grd-insight-icon"><i class="bi bi-people-fill"></i></span>
        <div><div class="mgmt-grd-insight-value">{{ enrolled_students|length }}</div><div class="mgmt-grd-insight-label">Students</div></div>
      </div>
      <div class="mgmt-grd-insight" role="listitem">
        <span class="mgmt-grd-insight-icon"><i class="bi bi-journal-text"></i></span>
        <div><div class="mgmt-grd-insight-value">{{ all_assignments|length }}</div><div class="mgmt-grd-insight-label">Assignments</div></div>
      </div>
      <div class="mgmt-grd-insight" role="listitem">
        <span class="mgmt-grd-insight-icon"><i class="bi bi-collection"></i></span>
        <div><div class="mgmt-grd-insight-value">{{ assignments|length }} / {{ group_assignments|length }}</div><div class="mgmt-grd-insight-label">Indiv / group</div></div>
      </div>
      <div class="mgmt-grd-insight" role="listitem">
        <span class="mgmt-grd-insight-icon"><i class="bi bi-calendar3"></i></span>
        <div><div class="mgmt-grd-insight-value">{{ class_info.schedule or 'TBD' }}</div><div class="mgmt-grd-insight-label">Schedule</div></div>
      </div>
    </div>
"""

    hero_actions = """        <a href="{{ url_for('management.manage_class_roster', class_id=class_info.id) }}" class="mgmt-grd-btn mgmt-grd-btn--ghost">
          <i class="bi bi-people" aria-hidden="true"></i> Roster
        </a>
        <a href="{{ url_for('management.view_class', class_id=class_info.id) }}" class="mgmt-grd-btn mgmt-grd-btn--ghost">
          <i class="bi bi-building" aria-hidden="true"></i> Class view
        </a>
        <a href="{{ url_for('management.classes') }}" class="mgmt-grd-btn mgmt-grd-btn--primary">
          <i class="bi bi-grid" aria-hidden="true"></i> All classes
        </a>"""

    partial = wrap_partial(
        "mgmt-grd",
        "Gradebook",
        "{{ class_info.name }}",
        "bi-graph-up",
        "{{ class_info.subject }} · assignments and student performance",
        insights,
        hero_actions,
        body.rstrip(),
    )
    (TPL / "_management_class_grades.html").write_text(partial, encoding="utf-8")

    grd_css = (CSS / "management_class_grades.css").read_text(encoding="utf-8")
    ag_css = (CSS / "management_assignments_and_grades.css").read_text(encoding="utf-8")
    out = shell_css("mgmt-grd", "Class grades") + "\n\n" + scope_css(grd_css + "\n" + ag_css, ".mgmt-grd-content")
    (CSS / "management_admin_class_grades.css").write_text(out, encoding="utf-8")


def patch_wrappers():
    """Only update thin wrapper templates (must run after partials exist)."""
    configs = [
        ("enhanced_classes.html", "_management_classes.html", "management_admin_classes.css", "Classes Management", ""),
        ("view_class.html", "_management_view_class.html", "management_admin_view_class.css", None, "assistant_approval.css"),
        ("manage_class_roster.html", "_management_class_roster.html", "management_admin_class_roster.css", None, ""),
        ("class_grades.html", "_management_class_grades.html", "management_admin_class_grades.css", None, ""),
    ]
    for fname, partial, css_file, fixed_title, extra_css in configs:
        path = TPL / fname
        orig = path.read_text(encoding="utf-8")
        if fixed_title:
            title_part = f"{{% block title %}}{fixed_title}{{% endblock %}}\n\n"
        else:
            t_start = orig.index("{% block title %}")
            t_end = orig.index("{% endblock %}", t_start) + len("{% endblock %}")
            title_part = orig[t_start:t_end] + "\n\n"
        extra_links = ""
        if extra_css:
            extra_links = f'<link rel="stylesheet" href="{{{{ url_for(\'static\', filename=\'css/{extra_css}\') }}}}">\n'
        text = f"""{{% extends "shared/dashboard_layout.html" %}}

{title_part}{{% block extra_css %}}
{extra_links}<link rel="stylesheet" href="{{{{ url_for('static', filename='css/{css_file}') }}}}">
{{% endblock %}}

{{% block dashboard_content %}}
{{% include 'management/{partial}' %}}
{{% endblock %}}
"""
        path.write_text(text, encoding="utf-8")


def main():
    build_classes()
    build_view_class()
    build_roster()
    build_grades()
    patch_wrappers()
    patch_role_dashboard()
    print("done")


def rebuild_roster_only():
    """Rebuild roster partial without touching wrapper templates."""
    build_roster()


def patch_role_dashboard():
    path = TPL / "role_dashboard.html"
    lines = read_lines(path)
    cls_start = next(i for i, l in enumerate(lines) if l.strip() == "{% elif section == 'classes' %}")
    asn_start = next(i for i, l in enumerate(lines) if l.strip() == "{% elif section == 'assignments' %}")
    insert = [
        "    {% elif section == 'classes' %}\n",
        "        {% include 'management/_management_classes.html' %}\n",
        "\n",
    ]
    new_lines = lines[:cls_start] + insert + lines[asn_start:]
    text = "".join(new_lines)
    old = """{% elif section == 'teachers' %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_staff.css') }}">
{% endif %}"""
    new = old.replace("{% endif %}", """{% elif section == 'classes' %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_classes.css') }}">
{% endif %}""")
    if old in text:
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
