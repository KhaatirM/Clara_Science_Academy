"""
Migration script to create the BugReport table for automatic error reporting.
Run this script to add the bug reporting functionality to your database.
"""

from app import create_app
from models import db, BugReport
from sqlalchemy import text

def create_bug_report_table():
    """Create the BugReport table in the database."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the table already exists
            result = db.session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='bug_report'
            """))
            
            if result.fetchone():
                print("BugReport table already exists. Skipping creation.")
                return True
            
            # Create the BugReport table
            db.session.execute(text("""
                CREATE TABLE bug_report (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_type VARCHAR(50) NOT NULL,
                    error_message TEXT NOT NULL,
                    error_traceback TEXT,
                    user_id INTEGER,
                    user_role VARCHAR(50),
                    url VARCHAR(500),
                    method VARCHAR(10),
                    user_agent VARCHAR(500),
                    ip_address VARCHAR(45),
                    request_data TEXT,
                    browser_info TEXT,
                    severity VARCHAR(20) DEFAULT 'medium' NOT NULL,
                    status VARCHAR(20) DEFAULT 'open' NOT NULL,
                    assigned_to INTEGER,
                    resolution_notes TEXT,
                    resolved_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    FOREIGN KEY (assigned_to) REFERENCES teacher_staff (id)
                )
            """))
            
            db.session.commit()
            print("✅ BugReport table created successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error creating BugReport table: {e}")
            db.session.rollback()
            return False

def add_bug_report_indexes():
    """Add useful indexes to the BugReport table for better performance."""
    app = create_app()
    
    with app.app_context():
        try:
            # Add indexes for common queries
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_bug_report_status ON bug_report(status)",
                "CREATE INDEX IF NOT EXISTS idx_bug_report_severity ON bug_report(severity)",
                "CREATE INDEX IF NOT EXISTS idx_bug_report_created_at ON bug_report(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_bug_report_user_id ON bug_report(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_bug_report_assigned_to ON bug_report(assigned_to)",
                "CREATE INDEX IF NOT EXISTS idx_bug_report_error_type ON bug_report(error_type)"
            ]
            
            for index_sql in indexes:
                db.session.execute(text(index_sql))
            
            db.session.commit()
            print("✅ BugReport indexes created successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error creating BugReport indexes: {e}")
            db.session.rollback()
            return False

def test_bug_report_functionality():
    """Test the bug report functionality by creating a sample report."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create a test bug report
            test_report = BugReport(
                error_type='test_error',
                error_message='This is a test error report to verify the system is working',
                error_traceback='Test traceback information',
                severity='low',
                status='open'
            )
            
            db.session.add(test_report)
            db.session.commit()
            
            print(f"✅ Test bug report created with ID: {test_report.id}")
            
            # Clean up test report
            db.session.delete(test_report)
            db.session.commit()
            
            print("✅ Test bug report cleaned up successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error testing bug report functionality: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🚀 Starting Bug Report Migration...")
    print("=" * 50)
    
    # Step 1: Create the table
    print("Step 1: Creating BugReport table...")
    if not create_bug_report_table():
        print("❌ Migration failed at table creation step.")
        exit(1)
    
    # Step 2: Add indexes
    print("\nStep 2: Adding indexes...")
    if not add_bug_report_indexes():
        print("❌ Migration failed at index creation step.")
        exit(1)
    
    # Step 3: Test functionality
    print("\nStep 3: Testing functionality...")
    if not test_bug_report_functionality():
        print("❌ Migration failed at testing step.")
        exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Bug Report Migration Completed Successfully!")
    print("\nThe automatic bug reporting system is now active and will:")
    print("• Capture server-side errors automatically")
    print("• Capture client-side JavaScript errors")
    print("• Send notifications to tech staff")
    print("• Provide a management interface for bug reports")
    print("\nTech staff can access bug reports at: /tech/bug-reports")
