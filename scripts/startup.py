#!/usr/bin/env python3
"""
Startup script for Render deployment that automatically fixes database issues.
- With --migrate-only: run DB fix scripts only and exit (for Render releaseCommand).
- Without: run DB fix scripts then start the Flask app (legacy) or use for local.
"""

import os
import sys
import subprocess
import time

def run_database_fix():
    """Run the database fix script if needed."""
    try:
        print("🔧 Checking database configuration...")

        # Run DB fixes whenever DATABASE_URL is present (production-like environments, including Render release phase).
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            is_render = bool(os.getenv('RENDER'))
            print(f"✓ DATABASE_URL detected (Render={is_render}), running database fix scripts...")
            
            # Run the database fix scripts
            scripts_to_run = [
                'add_missing_grade_and_assignment_columns.py',  # assignment_category, category_weight, etc.
                'fix_production_assignment_columns_postgres.py',
                'fix_production_status_override_columns.py',
                'fix_school_day_attendance_table.py',
                'fix_allow_student_edit_posts_column.py',
                'fix_group_size_max_nullable.py',
                'fix_bug_report_table_schema.py',
                'fix_class_table_schema.py',
                'fix_production_voided_fields.py',
                'fix_production_teacher_staff_deleted_fields.py',
                'fix_production_student_deleted_fields.py',
                'add_quiz_sections.py'
            ]
            
            # Get the maintenance_scripts directory path and project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_dir = os.path.join(project_root, 'maintenance_scripts')
            
            all_success = True
            for script in scripts_to_run:
                script_path = os.path.join(script_dir, script)
                if not os.path.exists(script_path):
                    print(f"⚠️  Script not found: {script_path}, skipping...")
                    continue
                print(f"🔧 Running {script}...")
                result = subprocess.run(
                    [sys.executable, script_path],
                    cwd=project_root,  # Ensure app is importable from project root
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    print(f"✅ {script} completed successfully!")
                    if result.stdout.strip():
                        print(result.stdout)
                else:
                    print(f"❌ {script} failed:")
                    print(result.stderr)
                    all_success = False
            
            if all_success:
                print("✅ All database fixes completed successfully!")
                
                # Additional fallback: Ensure all tables exist
                try:
                    print("🔧 Ensuring all database tables exist...")
                    from models import db
                    db.create_all()
                    print("✅ Database tables verified!")
                except Exception as e:
                    print(f"⚠️  Warning: Could not verify database tables: {e}")
                
                return True
            else:
                print("⚠️  Some database fixes failed, continuing with startup...")
                return False
                
        else:
            print("ℹ️  DATABASE_URL not set; skipping database fix scripts")
            return True
            
    except subprocess.TimeoutExpired:
        print("⏰ Database fix timed out, continuing with startup...")
        return False
    except Exception as e:
        print(f"❌ Error running database fix: {e}")
        print("Continuing with application startup...")
        return False

def main():
    """Main startup function."""
    # Render release phase: only run DB fixes then exit so the web service can start with gunicorn
    if '--migrate-only' in sys.argv:
        print("🚀 Render release: running database fixes only...")
        run_database_fix()
        print("✅ Release phase complete.")
        sys.exit(0)

    print("🚀 Starting Clara Science Academy Application...")
    print("=" * 50)
    
    # Run database fix first
    db_fix_success = run_database_fix()
    
    print("\n" + "=" * 50)
    
    if db_fix_success:
        print("✅ Startup checks completed successfully!")
    else:
        print("⚠️  Startup checks completed with warnings!")
    
    print("🌐 Starting Flask application...")
    
    # Start the main Flask application
    try:
        from app import create_app
        app = create_app()
        
        # Get port from environment or use default
        port = int(os.getenv('PORT', 5000))
        
        print(f"🎯 Application starting on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
