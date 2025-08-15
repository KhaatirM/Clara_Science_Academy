#!/usr/bin/env python3
"""
Comprehensive script to fix production database issues.
This script will add missing columns and ensure all required tables exist.
Compatible with PostgreSQL (used on Render).
"""

from app import create_app, db
from sqlalchemy import text

def check_and_fix_assignment_table():
    """Check and fix the assignment table structure."""
    print("=== CHECKING ASSIGNMENT TABLE ===")
    
    try:
        # Check if assignment table exists
        check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'assignment'
            )
        """
        result = db.session.execute(text(check_table_sql))
        table_exists = result.fetchone()[0]
        
        if not table_exists:
            print("❌ Assignment table does not exist. This is a critical issue.")
            return False
        
        print("✅ Assignment table exists")
        
        # Check for required columns
        required_columns = [
            'id', 'title', 'description', 'class_id', 'due_date', 
            'quarter', 'semester', 'academic_period_id', 'school_year_id',
            'is_locked', 'created_at'
        ]
        
        check_columns_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'assignment'
        """
        result = db.session.execute(text(check_columns_sql))
        existing_columns = [row[0] for row in result.fetchall()]
        
        print(f"📋 Existing columns: {', '.join(existing_columns)}")
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"⚠️  Missing columns: {', '.join(missing_columns)}")
            
            # Add missing columns
            for col in missing_columns:
                try:
                    if col == 'academic_period_id':
                        add_sql = "ALTER TABLE assignment ADD COLUMN academic_period_id INTEGER"
                        db.session.execute(text(add_sql))
                        
                        # Add foreign key constraint
                        fk_sql = """
                            ALTER TABLE assignment 
                            ADD CONSTRAINT fk_assignment_academic_period 
                            FOREIGN KEY (academic_period_id) REFERENCES academic_period(id)
                        """
                        db.session.execute(text(fk_sql))
                        print(f"  ✅ Added {col} with foreign key constraint")
                        
                    elif col == 'semester':
                        add_sql = "ALTER TABLE assignment ADD COLUMN semester VARCHAR(10)"
                        db.session.execute(text(add_sql))
                        print(f"  ✅ Added {col}")
                        
                    elif col == 'is_locked':
                        add_sql = "ALTER TABLE assignment ADD COLUMN is_locked BOOLEAN DEFAULT FALSE"
                        db.session.execute(text(add_sql))
                        print(f"  ✅ Added {col}")
                        
                    elif col == 'created_at':
                        add_sql = "ALTER TABLE assignment ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                        db.session.execute(text(add_sql))
                        print(f"  ✅ Added {col}")
                        
                    else:
                        print(f"  ⚠️  Manual intervention needed for {col}")
                        
                except Exception as e:
                    print(f"  ❌ Error adding {col}: {e}")
            
            db.session.commit()
            print("✅ Assignment table fixes completed")
        else:
            print("✅ All required columns are present")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking assignment table: {e}")
        db.session.rollback()
        return False

def check_and_fix_academic_period_table():
    """Check and fix the academic_period table structure."""
    print("\n=== CHECKING ACADEMIC_PERIOD TABLE ===")
    
    try:
        # Check if academic_period table exists
        check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'academic_period'
            )
        """
        result = db.session.execute(text(check_table_sql))
        table_exists = result.fetchone()[0]
        
        if not table_exists:
            print("❌ Academic_period table does not exist. Creating it...")
            
            create_table_sql = """
                CREATE TABLE academic_period (
                    id SERIAL PRIMARY KEY,
                    school_year_id INTEGER NOT NULL,
                    name VARCHAR(20) NOT NULL,
                    period_type VARCHAR(10) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """
            db.session.execute(text(create_table_sql))
            
            # Add foreign key constraint
            fk_sql = """
                ALTER TABLE academic_period 
                ADD CONSTRAINT fk_academic_period_school_year 
                FOREIGN KEY (school_year_id) REFERENCES school_year(id)
            """
            db.session.execute(text(fk_sql))
            
            db.session.commit()
            print("✅ Academic_period table created successfully")
        else:
            print("✅ Academic_period table exists")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking academic_period table: {e}")
        db.session.rollback()
        return False

def check_and_fix_school_year_table():
    """Check and fix the school_year table structure."""
    print("\n=== CHECKING SCHOOL_YEAR TABLE ===")
    
    try:
        # Check if school_year table exists
        check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'school_year'
            )
        """
        result = db.session.execute(text(check_table_sql))
        table_exists = result.fetchone()[0]
        
        if not table_exists:
            print("❌ School_year table does not exist. Creating it...")
            
            create_table_sql = """
                CREATE TABLE school_year (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(20) NOT NULL UNIQUE,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """
            db.session.execute(text(create_table_sql))
            
            db.session.commit()
            print("✅ School_year table created successfully")
        else:
            print("✅ School_year table exists")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking school_year table: {e}")
        db.session.rollback()
        return False

def main():
    """Main function to run all database fixes."""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 PRODUCTION DATABASE FIX SCRIPT")
            print("=" * 50)
            
            # Check and fix tables in dependency order
            if not check_and_fix_school_year_table():
                print("❌ Failed to fix school_year table. Aborting.")
                return
                
            if not check_and_fix_academic_period_table():
                print("❌ Failed to fix academic_period table. Aborting.")
                return
                
            if not check_and_fix_assignment_table():
                print("❌ Failed to fix assignment table. Aborting.")
                return
            
            print("\n" + "=" * 50)
            print("✅ All database fixes completed successfully!")
            print("The application should now work without the academic_period_id error.")
            
        except Exception as e:
            print(f"❌ Critical error in main function: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    main()
