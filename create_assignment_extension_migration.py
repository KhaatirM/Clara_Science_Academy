#!/usr/bin/env python3
"""
Migration script to create AssignmentExtension table
Run this on Render after deploying the updated code
"""

from flask import Flask
from flask_migrate import Migrate, upgrade
import os

# Create Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
from extensions import db, migrate
db.init_app(app)
migrate.init_app(app, db)

def create_assignment_extension_table():
    """Create the AssignmentExtension table"""
    with app.app_context():
        try:
            # Check if table already exists
            result = db.engine.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'assignment_extension'
                );
            """).fetchone()
            
            if result[0]:
                print("AssignmentExtension table already exists. Skipping creation.")
                return
            
            # Create the table
            db.engine.execute("""
                CREATE TABLE assignment_extension (
                    id SERIAL PRIMARY KEY,
                    assignment_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    extended_due_date TIMESTAMP NOT NULL,
                    reason TEXT,
                    granted_by INTEGER NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (assignment_id) REFERENCES assignment (id),
                    FOREIGN KEY (student_id) REFERENCES student (id),
                    FOREIGN KEY (granted_by) REFERENCES teacher_staff (id)
                );
            """)
            
            # Create indexes for better performance
            db.engine.execute("""
                CREATE INDEX idx_assignment_extension_assignment_id ON assignment_extension (assignment_id);
            """)
            
            db.engine.execute("""
                CREATE INDEX idx_assignment_extension_student_id ON assignment_extension (student_id);
            """)
            
            db.engine.execute("""
                CREATE INDEX idx_assignment_extension_active ON assignment_extension (is_active);
            """)
            
            print("✅ AssignmentExtension table created successfully!")
            print("✅ Indexes created for better performance!")
            
        except Exception as e:
            print(f"❌ Error creating AssignmentExtension table: {e}")
            raise

if __name__ == "__main__":
    create_assignment_extension_table()
