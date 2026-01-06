"""
Emergency patch script to fix grade display issue on Render production.
This updates the template file in place to properly display grades.

Run on Render Shell:
    python patch_teacher_grade_template.py
"""

import os
import re

def patch_template():
    """Patch the teacher grading template to fix grade display."""
    
    template_path = 'templates/teachers/teacher_grade_assignment.html'
    
    if not os.path.exists(template_path):
        print(f"❌ Template file not found: {template_path}")
        return
    
    print("=" * 70)
    print("PATCHING TEACHER GRADE TEMPLATE")
    print("=" * 70)
    
    # Read current file
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_path = template_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Backup created: {backup_path}")
    
    # Pattern to find the problematic section
    old_pattern = r'{%\s*set\s+score_value\s*=\s*grade_data\.get\([\'"]score[\'"]\s*,\s*0\)\|float\s*%}'
    
    # Check if old pattern exists
    if 'grade_data.get(\'score\'' in content or 'grade_data.get("score"' in content:
        print("⚠️  Found old .get() syntax - replacing...")
        
        # Replace the grade data access section
        content = re.sub(
            r'{%\s*if\s+grade_data\s*%}\s*{%\s*set\s+is_voided.*?{%\s*endif\s*%}',
            '''{% if grade_data %}
                        {% set is_voided = grade_data.is_voided|default(false) %}
                        {% if grade_data.score is defined and grade_data.score is not none %}
                            {% set score_value = grade_data.score|float %}
                        {% elif grade_data['score'] is defined and grade_data['score'] is not none %}
                            {% set score_value = grade_data['score']|float %}
                        {% endif %}
                        {% set comment_data = grade_data.comment|default('') or grade_data.feedback|default('') %}
                    {% endif %}''',
            content,
            flags=re.DOTALL
        )
        
        # Write updated content
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Template patched successfully!")
        print("\n" + "=" * 70)
        print("RESTART REQUIRED")
        print("=" * 70)
        print("\nThe template has been updated, but you need to restart the service:")
        print("1. Go to Render Dashboard")
        print("2. Click 'Manual Deploy' → 'Deploy latest commit'")
        print("\nOr the app will auto-restart in a few minutes.")
        
    else:
        print("✅ Template already uses correct syntax - no patch needed!")
        print("   If grades still don't show, try restarting the Render service.")

if __name__ == '__main__':
    patch_template()

