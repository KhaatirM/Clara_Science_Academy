#!/usr/bin/env python3
"""
Migration script to create 360-degree feedback tables.
"""

from app import create_app, db
from models import Feedback360, Feedback360Response, Feedback360Criteria

def create_360_feedback_tables():
    """Create 360-degree feedback tables."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the tables
            Feedback360.__table__.create(db.engine, checkfirst=True)
            Feedback360Response.__table__.create(db.engine, checkfirst=True)
            Feedback360Criteria.__table__.create(db.engine, checkfirst=True)
            
            print("✅ 360-degree feedback tables created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating 360-degree feedback tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    create_360_feedback_tables()

