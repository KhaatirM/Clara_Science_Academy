#!/usr/bin/env python3
"""
Fix the bug_report table schema to match the current model
This script updates the existing table to have the correct columns
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def fix_bug_report_table_schema():
    """Fix the bug_report table schema to match the current model"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 Fixing bug_report table schema...")
            
            # Check if table exists
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'bug_report' not in existing_tables:
                print("❌ bug_report table doesn't exist. Creating it...")
                db.create_all()
                print("✅ bug_report table created successfully!")
                return True
            
            # Get current columns
            columns = [col['name'] for col in inspector.get_columns('bug_report')]
            print(f"Current columns: {columns}")
            
            # Check if we need to add the title column
            if 'title' not in columns:
                print("📝 Adding missing 'title' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN title VARCHAR(200)"))
                print("✅ Added 'title' column")
            
            # Check if we need to add the description column
            if 'description' not in columns:
                print("📝 Adding missing 'description' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN description TEXT"))
                print("✅ Added 'description' column")
            
            # Check if we need to add the contact_email column
            if 'contact_email' not in columns:
                print("📝 Adding missing 'contact_email' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN contact_email VARCHAR(120)"))
                print("✅ Added 'contact_email' column")
            
            # Check if we need to add the page_url column
            if 'page_url' not in columns:
                print("📝 Adding missing 'page_url' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN page_url VARCHAR(500)"))
                print("✅ Added 'page_url' column")
            
            # Check if we need to add the updated_at column
            if 'updated_at' not in columns:
                print("📝 Adding missing 'updated_at' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN updated_at DATETIME"))
                print("✅ Added 'updated_at' column")
            
            # Check if we need to add the resolved_by column
            if 'resolved_by' not in columns:
                print("📝 Adding missing 'resolved_by' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN resolved_by INTEGER"))
                print("✅ Added 'resolved_by' column")
            
            # Check if we need to add the resolution_notes column
            if 'resolution_notes' not in columns:
                print("📝 Adding missing 'resolution_notes' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN resolution_notes TEXT"))
                print("✅ Added 'resolution_notes' column")
            
            # Check if we need to add the resolved_at column
            if 'resolved_at' not in columns:
                print("📝 Adding missing 'resolved_at' column...")
                db.session.execute(text("ALTER TABLE bug_report ADD COLUMN resolved_at DATETIME"))
                print("✅ Added 'resolved_at' column")
            
            db.session.commit()
            print("✅ bug_report table schema updated successfully!")
            
            # Verify the schema
            print("\n🔍 Verifying updated schema...")
            updated_columns = [col['name'] for col in inspector.get_columns('bug_report')]
            print(f"Updated columns: {updated_columns}")
            
            # Check if all required columns are present
            required_columns = [
                'id', 'user_id', 'title', 'description', 'contact_email', 
                'severity', 'status', 'browser_info', 'user_agent', 'ip_address', 
                'page_url', 'created_at', 'updated_at', 'resolved_at', 
                'resolved_by', 'resolution_notes'
            ]
            
            missing_columns = [col for col in required_columns if col not in updated_columns]
            if missing_columns:
                print(f"⚠️  Still missing columns: {missing_columns}")
                return False
            else:
                print("✅ All required columns are present!")
                return True
            
        except Exception as e:
            print(f"❌ Error fixing bug_report table schema: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

def migrate_existing_data():
    """Migrate existing data from old schema to new schema"""
    app = create_app()
    
    with app.app_context():
        try:
            print("\n🔄 Migrating existing data...")
            
            # Check if there's data to migrate
            result = db.session.execute(text("SELECT COUNT(*) FROM bug_report"))
            count = result.scalar()
            
            if count == 0:
                print("✅ No existing data to migrate")
                return True
            
            print(f"📊 Found {count} existing bug reports to migrate...")
            
            # Migrate data from old columns to new columns
            # Map error_message to description if title is empty
            db.session.execute(text("""
                UPDATE bug_report 
                SET description = COALESCE(description, error_message),
                    title = COALESCE(title, error_type, 'Bug Report')
                WHERE description IS NULL OR title IS NULL
            """))
            
            db.session.commit()
            print("✅ Data migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error migrating data: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🚀 Starting Bug Report Table Schema Fix...")
    print("=" * 60)
    
    # Step 1: Fix the schema
    print("Step 1: Fixing table schema...")
    if not fix_bug_report_table_schema():
        print("❌ Schema fix failed.")
        exit(1)
    
    # Step 2: Migrate existing data
    print("\nStep 2: Migrating existing data...")
    if not migrate_existing_data():
        print("❌ Data migration failed.")
        exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Bug Report Table Schema Fix Completed Successfully!")
    print("\nThe bug_report table now matches the current model and should work correctly.")
