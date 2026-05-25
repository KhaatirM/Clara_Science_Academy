"""Replace students/teachers blocks in role_dashboard.html with includes."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "templates/management/role_dashboard.html"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

def find_line(prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].strip().startswith(prefix):
            return i
    return -1

stu_start = find_line("{% elif section == 'students' %}")
tea_start = find_line("{% elif section == 'teachers' %}", stu_start + 1)
cls_start = find_line("{% elif section == 'classes' %}", tea_start + 1)

if stu_start < 0 or tea_start < 0 or cls_start < 0:
    raise SystemExit(f"markers not found: {stu_start}, {tea_start}, {cls_start}")

stu_include = [
    "    {% elif section == 'students' %}\n",
    "        {% include 'management/_management_students.html' %}\n",
    "\n",
]
tea_include = [
    "    {% elif section == 'teachers' %}\n",
    "        {% include 'management/_management_staff.html' %}\n",
    "\n",
]

new_lines = lines[:stu_start] + stu_include + tea_include + lines[cls_start:]
text = "".join(new_lines)

# Patch extra_css
old_css = """{% if section == 'home' %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_home.css') }}">
{% endif %}"""

new_css = """{% if section == 'home' %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_home.css') }}">
{% elif section == 'students' %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_students.css') }}">
{% elif section == 'teachers' %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/management_admin_staff.css') }}">
{% endif %}"""

if old_css not in text:
    raise SystemExit("extra_css block not found")
text = text.replace(old_css, new_css, 1)

path.write_text(text, encoding="utf-8")
print(f"patched: removed {tea_start - stu_start} + {cls_start - tea_start} lines, kept {len(new_lines)} lines")
