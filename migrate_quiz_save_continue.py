#!/usr/bin/env python3
"""
Migration script to add quiz save and continue functionality to existing databases.
This script adds the necessary fields and creates the QuizProgress table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from datetime import datetime

def migrate_quiz_save_continue():
    """Add quiz save and continue functionality to existing database."""
    
    print("Starting migration process...")
    app = create_app()
    print("App created successfully")
    
    with app.app_context():
        print("App context entered")
        try:
            print("Starting quiz save and continue migration...")
            
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('assignment')]
            
            # Add new fields to Assignment table if they don't exist
            if 'allow_save_and_continue' not in existing_columns:
                print("Adding allow_save_and_continue column...")
                db.engine.execute('ALTER TABLE assignment ADD COLUMN allow_save_and_continue BOOLEAN DEFAULT FALSE')
                print("✓ Added allow_save_and_continue column")
            else:
                print("✓ allow_save_and_continue column already exists")
                
            if 'max_save_attempts' not in existing_columns:
                print("Adding max_save_attempts column...")
                db.engine.execute('ALTER TABLE assignment ADD COLUMN max_save_attempts INTEGER DEFAULT 10')
                print("✓ Added max_save_attempts column")
            else:
                print("✓ max_save_attempts column already exists")
                
            if 'save_timeout_minutes' not in existing_columns:
                print("Adding save_timeout_minutes column...")
                db.engine.execute('ALTER TABLE assignment ADD COLUMN save_timeout_minutes INTEGER DEFAULT 30')
                print("✓ Added save_timeout_minutes column")
            else:
                print("✓ save_timeout_minutes column already exists")
            
            # Create QuizProgress table if it doesn't exist
            tables = [table['name'] for table in inspector.get_table_names()]
            if 'quiz_progress' not in tables:
                print("Creating QuizProgress table...")
                db.engine.execute('''
                    CREATE TABLE quiz_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        assignment_id INTEGER NOT NULL,
                        current_question_id INTEGER,
                        answers_data TEXT,
                        progress_percentage INTEGER DEFAULT 0,
                        questions_answered INTEGER DEFAULT 0,
                        total_questions INTEGER DEFAULT 0,
                        last_saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_submitted BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (student_id) REFERENCES student (id),
                        FOREIGN KEY (assignment_id) REFERENCES assignment (id),
                        FOREIGN KEY (current_question_id) REFERENCES quiz_question (id),
                        UNIQUE(student_id, assignment_id)
                    )
                ''')
                print("✓ Created QuizProgress table")
            else:
                print("✓ QuizProgress table already exists")
            
            # Update existing quiz assignments to have save and continue enabled by default
            print("Updating existing quiz assignments...")
            result = db.engine.execute('''
                UPDATE assignment 
                SET allow_save_and_continue = TRUE, 
                    max_save_attempts = 10, 
                    save_timeout_minutes = 30
                WHERE assignment_type = 'quiz'
            ''')
            print(f"✓ Updated {result.rowcount} existing quiz assignments")
            
            db.session.commit()
            print("\n✅ Migration completed successfully!")
            print("\nFeatures added:")
            print("- Save and continue functionality for quizzes")
            print("- Progress tracking for students")
            print("- Configurable save attempts and timeout")
            print("- Progress bars in student dashboard")
            
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_quiz_save_continue()
