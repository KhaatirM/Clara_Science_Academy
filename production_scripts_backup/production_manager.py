#!/usr/bin/env python3
"""
Unified Production Management System

This script consolidates all production fixes, migrations, and database management
functionality into a single, comprehensive system.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import db
    from sqlalchemy import text
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

class ProductionManager:
    """Manages all production operations for the application."""
    
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_context.pop()
    
    def get_database_info(self) -> Dict:
        """Get information about the current database."""
        try:
            db_url = str(db.engine.url)
            is_postgres = 'postgresql' in db_url
            
            # Get table names
            with db.engine.connect() as connection:
                if is_postgres:
                    result = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
                    tables = [row[0] for row in result]
                else:
                    result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                    tables = [row[0] for row in result]
            
            return {
                'url': db_url,
                'type': 'PostgreSQL' if is_postgres else 'SQLite',
                'is_postgres': is_postgres,
                'tables': tables
            }
        except Exception as e:
            print(f"Error getting database info: {e}")
            return {}
    
    def fix_class_table_schema(self) -> bool:
        """Fix Class table schema issues."""
        try:
            db_info = self.get_database_info()
            if not db_info:
                return False
            
            is_postgres = db_info['is_postgres']
            
            # Check if class table exists
            if 'class' not in db_info['tables']:
                print("Class table does not exist. Creating...")
                db.create_all()
                return True
            
            # Columns to add
            columns_to_add = [
                ('room_number', 'VARCHAR(20)' if is_postgres else 'TEXT'),
                ('schedule', 'VARCHAR(200)' if is_postgres else 'TEXT'),
                ('max_students', 'INTEGER'),
                ('description', 'TEXT'),
                ('is_active', 'BOOLEAN DEFAULT TRUE' if is_postgres else 'INTEGER DEFAULT 1'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if is_postgres else 'DATETIME'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if is_postgres else 'DATETIME')
            ]
            
            with db.engine.connect() as connection:
                for column_name, column_def in columns_to_add:
                    try:
                        if is_postgres:
                            sql = f"ALTER TABLE class ADD COLUMN IF NOT EXISTS {column_name} {column_def}"
                        else:
                            # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
                            sql = f"ALTER TABLE class ADD COLUMN {column_name} {column_def}"
                        
                        connection.execute(text(sql))
                        print(f"✅ Added column: {column_name}")
                        
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                            print(f"ℹ️  Column {column_name} already exists")
                        else:
                            print(f"⚠️  Warning adding {column_name}: {e}")
            
            db.session.commit()
            print("✅ Class table schema fix completed")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing class table schema: {e}")
            db.session.rollback()
            return False
    
    def fix_bug_report_table_schema(self) -> bool:
        """Fix BugReport table schema issues."""
        try:
            db_info = self.get_database_info()
            if not db_info:
                return False
            
            is_postgres = db_info['is_postgres']
            
            # Check if bug_report table exists
            if 'bug_report' not in db_info['tables']:
                print("Bug report table does not exist. Creating...")
                db.create_all()
                return True
            
            # Columns to add
            columns_to_add = [
                ('title', 'VARCHAR(200)' if is_postgres else 'TEXT'),
                ('description', 'TEXT'),
                ('contact_email', 'VARCHAR(100)' if is_postgres else 'TEXT'),
                ('page_url', 'VARCHAR(500)' if is_postgres else 'TEXT'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if is_postgres else 'DATETIME'),
                ('resolved_by', 'INTEGER')
            ]
            
            with db.engine.connect() as connection:
                for column_name, column_def in columns_to_add:
                    try:
                        if is_postgres:
                            sql = f"ALTER TABLE bug_report ADD COLUMN IF NOT EXISTS {column_name} {column_def}"
                        else:
                            sql = f"ALTER TABLE bug_report ADD COLUMN {column_name} {column_def}"
                        
                        connection.execute(text(sql))
                        print(f"✅ Added column: {column_name}")
                        
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                            print(f"ℹ️  Column {column_name} already exists")
                        else:
                            print(f"⚠️  Warning adding {column_name}: {e}")
            
            db.session.commit()
            print("✅ Bug report table schema fix completed")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing bug report table schema: {e}")
            db.session.rollback()
            return False
    
    def fix_school_day_attendance_table(self) -> bool:
        """Create or fix SchoolDayAttendance table."""
        try:
            db_info = self.get_database_info()
            if not db_info:
                return False
            
            is_postgres = db_info['is_postgres']
            
            # Check if table exists
            if 'school_day_attendance' in db_info['tables']:
                print("School day attendance table already exists")
                return True
            
            # Create the table
            create_table_sql = f"""
            CREATE TABLE school_day_attendance (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                student_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'present',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """ if is_postgres else """
            CREATE TABLE school_day_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                student_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'present',
                notes TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
            """
            
            with db.engine.connect() as connection:
                connection.execute(text(create_table_sql))
            
            db.session.commit()
            print("✅ School day attendance table created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating school day attendance table: {e}")
            db.session.rollback()
            return False
    
    def fix_assignment_columns(self) -> bool:
        """Fix Assignment table columns."""
        try:
            db_info = self.get_database_info()
            if not db_info:
                return False
            
            is_postgres = db_info['is_postgres']
            
            # Check if assignment table exists
            if 'assignment' not in db_info['tables']:
                print("Assignment table does not exist. Creating...")
                db.create_all()
                return True
            
            # Columns to add/update
            columns_to_add = [
                ('assignment_type', 'VARCHAR(50) DEFAULT \'pdf_paper\'' if is_postgres else 'TEXT DEFAULT \'pdf_paper\''),
                ('status', 'VARCHAR(20) DEFAULT \'Active\'' if is_postgres else 'TEXT DEFAULT \'Active\''),
                ('file_attachments', 'TEXT'),
                ('created_by', 'INTEGER'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if is_postgres else 'DATETIME')
            ]
            
            with db.engine.connect() as connection:
                for column_name, column_def in columns_to_add:
                    try:
                        if is_postgres:
                            sql = f"ALTER TABLE assignment ADD COLUMN IF NOT EXISTS {column_name} {column_def}"
                        else:
                            sql = f"ALTER TABLE assignment ADD COLUMN {column_name} {column_def}"
                        
                        connection.execute(text(sql))
                        print(f"✅ Added column: {column_name}")
                        
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                            print(f"ℹ️  Column {column_name} already exists")
                        else:
                            print(f"⚠️  Warning adding {column_name}: {e}")
            
            db.session.commit()
            print("✅ Assignment table schema fix completed")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing assignment table schema: {e}")
            db.session.rollback()
            return False
    
    def run_all_production_fixes(self) -> bool:
        """Run all production fixes in sequence."""
        print("🔧 Running all production fixes...")
        
        fixes = [
            ("Class Table Schema", self.fix_class_table_schema),
            ("Bug Report Table Schema", self.fix_bug_report_table_schema),
            ("School Day Attendance Table", self.fix_school_day_attendance_table),
            ("Assignment Table Schema", self.fix_assignment_columns)
        ]
        
        success_count = 0
        total_fixes = len(fixes)
        
        for fix_name, fix_function in fixes:
            print(f"\n🔧 Running: {fix_name}")
            if fix_function():
                success_count += 1
                print(f"✅ {fix_name} completed successfully")
            else:
                print(f"❌ {fix_name} failed")
        
        print(f"\n📊 Production fixes summary:")
        print(f"✅ Successful: {success_count}/{total_fixes}")
        print(f"❌ Failed: {total_fixes - success_count}/{total_fixes}")
        
        return success_count == total_fixes
    
    def check_production_health(self) -> Dict:
        """Check the health of the production database."""
        print("🏥 Checking production database health...")
        
        health_report = {
            'database_info': self.get_database_info(),
            'tables_status': {},
            'issues_found': [],
            'recommendations': []
        }
        
        db_info = health_report['database_info']
        if not db_info:
            health_report['issues_found'].append("Cannot connect to database")
            return health_report
        
        # Check critical tables
        critical_tables = ['user', 'student', 'teacher_staff', 'class', 'assignment']
        
        for table in critical_tables:
            if table in db_info['tables']:
                health_report['tables_status'][table] = '✅ Exists'
            else:
                health_report['tables_status'][table] = '❌ Missing'
                health_report['issues_found'].append(f"Critical table '{table}' is missing")
        
        # Check for common schema issues
        if 'class' in db_info['tables']:
            try:
                with db.engine.connect() as connection:
                    if db_info['is_postgres']:
                        result = connection.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'class'"))
                        columns = [row[0] for row in result]
                    else:
                        result = connection.execute(text("PRAGMA table_info(class)"))
                        columns = [row[1] for row in result]
                
                required_columns = ['room_number', 'schedule', 'max_students', 'description']
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    health_report['issues_found'].append(f"Class table missing columns: {missing_columns}")
                    health_report['recommendations'].append("Run: fix_class_table_schema")
            
            except Exception as e:
                health_report['issues_found'].append(f"Error checking class table: {e}")
        
        return health_report
    
    def display_health_report(self, health_report: Dict):
        """Display a formatted health report."""
        print("\n" + "=" * 60)
        print("🏥 PRODUCTION DATABASE HEALTH REPORT")
        print("=" * 60)
        
        # Database info
        db_info = health_report['database_info']
        if db_info:
            print(f"Database Type: {db_info['type']}")
            print(f"Tables Count: {len(db_info['tables'])}")
        
        # Tables status
        print("\n📋 Tables Status:")
        for table, status in health_report['tables_status'].items():
            print(f"  {status} {table}")
        
        # Issues
        if health_report['issues_found']:
            print("\n⚠️  Issues Found:")
            for issue in health_report['issues_found']:
                print(f"  • {issue}")
        
        # Recommendations
        if health_report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in health_report['recommendations']:
                print(f"  • {rec}")
        
        if not health_report['issues_found']:
            print("\n✅ All checks passed! Database is healthy.")
        
        print("=" * 60)

def main():
    """Main function with command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python production_manager.py [command]")
        print("Commands:")
        print("  health           - Check production database health")
        print("  fix-all          - Run all production fixes")
        print("  fix-class        - Fix class table schema")
        print("  fix-bug-report   - Fix bug report table schema")
        print("  fix-attendance   - Fix school day attendance table")
        print("  fix-assignments  - Fix assignment table schema")
        print("  info             - Show database information")
        return
    
    command = sys.argv[1].lower()
    
    with ProductionManager() as manager:
        if command == 'health':
            health_report = manager.check_production_health()
            manager.display_health_report(health_report)
        elif command == 'fix-all':
            manager.run_all_production_fixes()
        elif command == 'fix-class':
            manager.fix_class_table_schema()
        elif command == 'fix-bug-report':
            manager.fix_bug_report_table_schema()
        elif command == 'fix-attendance':
            manager.fix_school_day_attendance_table()
        elif command == 'fix-assignments':
            manager.fix_assignment_columns()
        elif command == 'info':
            db_info = manager.get_database_info()
            print("Database Information:")
            print(f"Type: {db_info.get('type', 'Unknown')}")
            print(f"Tables: {len(db_info.get('tables', []))}")
            print(f"Tables: {', '.join(db_info.get('tables', []))}")
        else:
            print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()
