"""Reorder update sections in home.html by date (newest first)."""
import re

path = "templates/shared/home.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the update-sections div boundaries
start_marker = '                <div class="update-sections">'
end_marker = '                </div>\n            </div>\n            <div class="modal-footer">'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)
if start_idx == -1 or end_idx == -1:
    print("Could not find markers")
    exit(1)

inner = content[start_idx + len(start_marker):end_idx]

# Split by section comments - each section runs from "<!-- March X" to the next (or end)
# Pattern finds start of each section
section_starts = list(re.finditer(r'\s+<!-- March \d+, 2026[^>]+ -->', inner))
sections = []
for i, m in enumerate(section_starts):
    start = m.start()
    if i + 1 < len(section_starts):
        # Section runs until the next section's comment
        block = inner[start:section_starts[i + 1].start()]
    else:
        block = inner[start:]
    # Extract date for sorting
    day_m = re.search(r'March (\d+), 2026', block[:100])
    day = int(day_m.group(1)) if day_m else 0
    sections.append((day, i, block))  # i preserves order within same date

# Sort by day descending (newest first), then by original index to keep same-day order
sections.sort(key=lambda x: (-x[0], x[1]))

new_inner = "".join(s[2] for s in sections)
new_content = (
    content[:start_idx + len(start_marker)] +
    new_inner +
    content[end_idx:]
)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Reordered update sections by date (newest first): March 10, 9, 4, 1")
