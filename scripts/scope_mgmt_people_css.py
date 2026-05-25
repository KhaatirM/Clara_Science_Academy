"""Generate scoped student/staff content CSS from management_role_dashboard.css."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "static/css/management_role_dashboard.css"

ACCENT_OLD = [
    ("#4facfe", "#0d9488"),
    ("#00f2fe", "#14b8a6"),
    ("#667eea", "#0d9488"),
    ("#764ba2", "#0f766e"),
    ("rgba(79, 172, 254", "rgba(13, 148, 136"),
]

SHELL_STU = ROOT / "static/css/_mgmt_stu_shell.css"
SHELL_STF = ROOT / "static/css/_mgmt_stf_shell.css"


def extract_block(text, start_marker, end_marker):
    start = text.find(start_marker)
    if start < 0:
        return ""
    end = text.find(end_marker, start)
    if end < 0:
        end = len(text)
    return text[start:end]


def scope_css(block, prefix):
    lines = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("/*") or stripped.startswith("*"):
            lines.append(line)
            continue
        if stripped.endswith("{") and not stripped.startswith("@"):
            sel = stripped[:-1].strip()
            if sel.startswith("."):
                line = f"{prefix} {sel} {{"
            elif sel.startswith("#"):
                line = f"{prefix} {sel} {{"
        for old, new in ACCENT_OLD:
            line = line.replace(old, new)
        lines.append(line)
    return "\n".join(lines)


def shell_css(variant):
    p = "mgmt-stu" if variant == "stu" else "mgmt-stf"
    other = "mgmt-stf" if variant == "stu" else "mgmt-stu"
    return f"""/* {variant} shell — matches management home / report cards */
.{p} {{
  --{p}-bg: linear-gradient(165deg, #e8f0ec 0%, #dce8e4 45%, #d4e2de 100%);
  --{p}-surface: rgba(255, 255, 255, 0.94);
  --{p}-border: rgba(255, 255, 255, 0.92);
  --{p}-text: #0f172a;
  --{p}-muted: #64748b;
  --{p}-accent: #0d9488;
  --{p}-accent-deep: #0f766e;
  --{p}-accent-soft: rgba(13, 148, 136, 0.12);
  --{p}-shadow: 0 4px 6px rgba(15, 23, 42, 0.04), 0 18px 40px rgba(15, 23, 42, 0.08);
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
  --{p}-accent: #7c3aed;
  --{p}-accent-deep: #6d28d9;
  --{p}-accent-soft: rgba(124, 58, 237, 0.12);
  --{p}-bg: linear-gradient(165deg, #f0ecf5 0%, #e8e4f0 45%, #e2dce8 100%);
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
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}}
.{p}-btn--ghost {{
  color: #334155;
  background: var(--{p}-surface);
  border: 1px solid rgba(148, 163, 184, 0.35);
}}
.{p}-btn--ghost:hover {{
  background: #fff;
  border-color: var(--{p}-accent);
  color: var(--{p}-accent-deep);
}}
.{p}-btn--primary {{
  color: #fff;
  background: linear-gradient(135deg, var(--{p}-accent), var(--{p}-accent-deep));
  border: 1px solid transparent;
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
.{p}-mode-pills {{
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  padding: 0.2rem;
  background: var(--{p}-surface);
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 999px;
}}
.{p}-mode-pills .nav-link {{
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  padding: 0.4rem 0.85rem;
}}
.{p}-mode-pills .nav-link.active {{
  background: var(--{p}-accent-soft);
  color: var(--{p}-accent-deep);
}}
"""


def main():
    text = SRC.read_text(encoding="utf-8")
    stu_block = extract_block(text, "STUDENTS TAB STYLES", "TEACHERS TAB STYLES")
    tea_block = extract_block(text, "TEACHERS TAB STYLES", "CLASSES TAB STYLES")
    if not tea_block:
        tea_block = extract_block(text, "TEACHERS TAB STYLES", "ASSIGNMENTS TAB")

    stu_out = shell_css("stu") + "\n\n/* Scoped content */\n" + scope_css(stu_block, ".mgmt-stu-content")
    stf_out = shell_css("stf") + "\n\n/* Scoped content */\n" + scope_css(tea_block, ".mgmt-stf-content")

    (ROOT / "static/css/management_admin_students.css").write_text(stu_out, encoding="utf-8")
    (ROOT / "static/css/management_admin_staff.css").write_text(stf_out, encoding="utf-8")
    print("wrote CSS files")


if __name__ == "__main__":
    main()
