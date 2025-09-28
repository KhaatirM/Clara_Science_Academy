#!/usr/bin/env python3
"""
File Analysis and Cleanup Tool
Analyzes the codebase and categorizes files for cleanup
"""

import os
import glob
from collections import defaultdict

def analyze_files():
    """Analyze all files in the project and categorize them."""
    
    # Define file categories
    categories = {
        'core_app': [],           # Main application files
        'routes': [],             # Route handlers
        'models_db': [],          # Database models and migrations
        'utilities': [],          # Utility scripts and helpers
        'sample_data': [],        # Sample data generation scripts
        'password_mgmt': [],      # Password management scripts
        'production_fixes': [],   # Production database fixes
        'documentation': [],      # README and documentation files
        'templates': [],          # HTML templates
        'static_assets': [],      # CSS, JS, images
        'config_deploy': [],      # Configuration and deployment files
        'backups': []             # Backup files
    }
    
    # Core application files
    core_files = [
        'app.py', 'config.py', 'extensions.py', 'run.py', 'wsgi.py',
        'startup.py', 'decorators.py'
    ]
    
    # Route files
    route_files = [
        'authroutes.py', 'teacherroutes.py', 'studentroutes.py', 
        'managementroutes.py', 'techroutes.py'
    ]
    
    # Database and models
    db_files = [
        'models.py', 'create_db.py', 'recreate_db.py'
    ]
    
    # Sample data scripts
    sample_files = [
        'add_sample_announcements.py', 'add_sample_assignments.py',
        'add_sample_attendance.py', 'add_sample_classes.py',
        'add_sample_notifications.py', 'add_sample_schedules.py',
        'add_school_year.py', 'add_semester_column.py',
        'create_academic_periods_table.py', 'create_calendar_events_table.py'
    ]
    
    # Password management
    password_files = [
        'password_manager.py', 'individual_passwords.py', 'show_passwords.py',
        'reset_and_show_passwords.py', 'quick_individual_passwords.py',
        'admin_user_manager.py', 'export_user_credentials.py',
        'get_user_credentials.py', 'quick_export.py', 'verify_users.py'
    ]
    
    # Production fixes
    fix_files = [
        'fix_announcement_table.py', 'fix_bug_report_table_schema.py',
        'fix_postgres_class_schema.py', 'fix_production_assignment_columns_postgres.py',
        'fix_production_assignment_status.py', 'fix_production_password_fields.py',
        'fix_school_day_attendance_table.py', 'render_shell_fix.py'
    ]
    
    # Documentation
    doc_files = [
        'AUTOMATIC_BUG_REPORTING_README.md', 'AUTOMATIC_DB_MIGRATION_SETUP.md',
        'COMPREHENSIVE_REPORTING_ANALYTICS_README.md', 'DATABASE_FIX_README.md',
        'ENHANCED_GROUP_FEATURES_README.md', 'GRADE_LEVELS_MIGRATION_GUIDE.md',
        'GROUP_MANAGEMENT_README.md', 'MIGRATION_GUIDE.md',
        'PASSWORD_CHANGE_SYSTEM_README.md', 'PASSWORD_SCRIPTS_README.md',
        'PRODUCTION_DATABASE_FIX_README.md', 'PRODUCTION_FIX_README.md',
        'RENDER_CREDENTIAL_EXPORT_README.md'
    ]
    
    # Configuration and deployment
    config_files = [
        'requirements.txt', 'render.yaml', 'fix_assignment_columns_production.sql',
        'create_bug_report_migration.py', 'update_routes_for_consolidation.py',
        'gpa_scheduler.py', 'shutdown_maintenance.py'
    ]
    
    # Categorize files
    all_files = glob.glob('*.py') + glob.glob('*.md') + glob.glob('*.sql') + glob.glob('*.yaml') + glob.glob('*.txt')
    
    for file in all_files:
        if file in core_files:
            categories['core_app'].append(file)
        elif file in route_files:
            categories['routes'].append(file)
        elif file in db_files:
            categories['models_db'].append(file)
        elif file in sample_files:
            categories['sample_data'].append(file)
        elif file in password_files:
            categories['password_mgmt'].append(file)
        elif file in fix_files:
            categories['production_fixes'].append(file)
        elif file in doc_files:
            categories['documentation'].append(file)
        elif file in config_files:
            categories['config_deploy'].append(file)
        else:
            # Check if it's a template or static file
            if file.endswith('.html'):
                categories['templates'].append(file)
            elif file.endswith(('.css', '.js', '.png', '.jpg', '.pdf')):
                categories['static_assets'].append(file)
            else:
                categories['utilities'].append(file)
    
    # Count templates
    template_files = glob.glob('templates/*.html')
    categories['templates'] = template_files
    
    # Count static assets
    static_files = glob.glob('static/**/*', recursive=True)
    static_files = [f for f in static_files if os.path.isfile(f)]
    categories['static_assets'] = static_files
    
    # Print analysis
    print("=" * 80)
    print("FILE ANALYSIS AND CLEANUP PLAN")
    print("=" * 80)
    
    total_files = 0
    for category, files in categories.items():
        if files:
            print(f"\n{category.upper().replace('_', ' ')}: {len(files)} files")
            for file in files[:5]:  # Show first 5 files
                print(f"  - {file}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
            total_files += len(files)
    
    print(f"\n{'='*80}")
    print(f"TOTAL FILES TO ANALYZE: {total_files}")
    print("=" * 80)
    
    # Create 10 groups for analysis
    print("\nCLEANUP GROUPS (10 groups):")
    print("=" * 50)
    
    groups = [
        ("GROUP 1", "Core Application Files", categories['core_app']),
        ("GROUP 2", "Route Handlers", categories['routes']),
        ("GROUP 3", "Database & Models", categories['models_db']),
        ("GROUP 4", "Sample Data Scripts", categories['sample_data']),
        ("GROUP 5", "Password Management", categories['password_mgmt']),
        ("GROUP 6", "Production Fixes", categories['production_fixes']),
        ("GROUP 7", "Documentation", categories['documentation']),
        ("GROUP 8", "Configuration & Deployment", categories['config_deploy']),
        ("GROUP 9", "Templates (Sample)", categories['templates'][:20]),  # First 20 templates
        ("GROUP 10", "Utilities & Remaining", categories['utilities'])
    ]
    
    for group_id, group_name, files in groups:
        print(f"\n{group_id}: {group_name} ({len(files)} files)")
        if files:
            for file in files[:3]:
                print(f"  - {file}")
            if len(files) > 3:
                print(f"  ... and {len(files) - 3} more")
    
    return categories, groups

if __name__ == '__main__':
    categories, groups = analyze_files()

