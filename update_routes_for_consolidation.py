#!/usr/bin/env python3
"""
Migration script to update route files to use consolidated templates.
This script will help you update your route files to use the new role-specific templates.
"""

import os
import re
from pathlib import Path

# Template mapping - old templates to new consolidated templates
TEMPLATE_MAPPING = {
    # Students templates
    'director_students.html': 'role_students.html',
    'admin_students.html': 'role_students.html',
    'teacher_students.html': 'role_students.html',
    
    # Teachers/Staff templates
    'director_teachers_staff.html': 'role_teachers_staff.html',
    'admin_teachers_staff.html': 'role_teachers_staff.html',
    'teacher_teachers_staff.html': 'role_teachers_staff.html',
    
    # Classes templates
    'director_classes.html': 'role_classes.html',
    'admin_classes.html': 'role_classes.html',
    'teacher_my_classes.html': 'role_classes.html',
    
    # Assignments templates
    'director_assignments_list.html': 'role_assignments.html',
    'admin_assignments_list.html': 'role_assignments.html',
    'teacher_assignments_list.html': 'role_assignments.html',
    'student_assignments_list.html': 'role_assignments.html',
    
    # Dashboard templates
    'staff_home.html': 'role_dashboard.html',
    'it_dashboard.html': 'role_dashboard.html',
    'student_dashboard_layout.html': 'role_dashboard.html',
    
    # Student-specific templates
    'student_my_classes.html': 'role_student_dashboard.html',
    'student_grades_view.html': 'role_student_dashboard.html',
    'student_generic_section.html': 'role_student_dashboard.html',
    'student_submission_form.html': 'role_student_forms.html',
    
    # Generic section templates
    'director_generic_section.html': 'role_generic_section.html',
    'admin_generic_section.html': 'role_generic_section.html',
    'teacher_generic_section.html': 'role_generic_section.html',
    
    # Teacher forms templates
    'teacher_grade_form.html': 'role_teacher_forms.html',
    'teacher_view_assignment_submissions.html': 'role_teacher_forms.html',
    
    # Assignment forms templates
    'assignment_form.html': 'role_assignment_forms.html',
}

# Route files to update
ROUTE_FILES = [
    'directorroutes.py',
    'adminroutes.py',
    'teacherroutes.py',
    'studentroutes.py',
    'itroutes.py'
]

def update_route_file(file_path):
    """Update a single route file to use consolidated templates."""
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found, skipping...")
        return
    
    print(f"Updating {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Update template references
    for old_template, new_template in TEMPLATE_MAPPING.items():
        # Pattern to match render_template calls
        pattern = r'render_template\([\'"]([^\'"]*' + re.escape(old_template) + r')[^\'"]*[\'"]'
        
        def replace_template(match):
            full_call = match.group(0)
            # Replace the template name in the render_template call
            new_call = full_call.replace(old_template, new_template)
            print(f"  Replacing: {old_template} -> {new_template}")
            return new_call
        
        content = re.sub(pattern, replace_template, content)
    
    # Write back if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Updated {file_path}")
    else:
        print(f"  - No changes needed in {file_path}")

def create_backup(file_path):
    """Create a backup of the original file."""
    backup_path = file_path + '.backup'
    if os.path.exists(file_path) and not os.path.exists(backup_path):
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")

def main():
    """Main migration function."""
    print("=== Template Consolidation Migration Script ===")
    print("This script will update your route files to use the new consolidated templates.")
    print()
    
    # Create backups
    print("Creating backups...")
    for route_file in ROUTE_FILES:
        create_backup(route_file)
    
    print()
    print("Updating route files...")
    
    # Update each route file
    for route_file in ROUTE_FILES:
        update_route_file(route_file)
    
    print()
    print("=== Migration Summary ===")
    print("The following templates have been consolidated:")
    for old_template, new_template in TEMPLATE_MAPPING.items():
        print(f"  {old_template} -> {new_template}")
    
    print()
    print("Files that can be safely deleted after testing:")
    for old_template in TEMPLATE_MAPPING.keys():
        template_path = f"templates/{old_template}"
        if os.path.exists(template_path):
            print(f"  {template_path}")
    
    print()
    print("=== Next Steps ===")
    print("1. Test your application to ensure all routes work correctly")
    print("2. If everything works, you can delete the old template files")
    print("3. Update any remaining route files that weren't covered by this script")
    print("4. Consider updating your dashboard_layout.html to use the new templates")

if __name__ == "__main__":
    main() 