#!/usr/bin/env python3
"""
Startup script for Render deployment that automatically fixes database issues.
This script runs before the main application starts to ensure the database is properly configured.
"""

import os
import sys
import subprocess
import time

def run_database_fix():
    """Run the database fix script if needed."""
    try:
        print("🔧 Checking database configuration...")
        
        # Check if we're in production (Render environment)
        if os.getenv('RENDER'):
            print("✓ Running in Render production environment")
            
            # Check if DATABASE_URL is available
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                print("⚠️  DATABASE_URL not found, skipping database fix")
                return True
            
            print("✓ DATABASE_URL found, running database fix...")
            
            # Run the database fix scripts
            scripts_to_run = [
                'fix_production_assignment_columns_postgres.py',
                'fix_school_day_attendance_table.py',
                'fix_bug_report_table_schema.py',
                'fix_class_table_schema.py'
            ]
            
            all_success = True
            for script in scripts_to_run:
                print(f"🔧 Running {script}...")
                result = subprocess.run([
                    sys.executable, 
                    script
                ], capture_output=True, text=True, timeout=60)
                
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
            print("ℹ️  Running in development environment, skipping database fix")
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
