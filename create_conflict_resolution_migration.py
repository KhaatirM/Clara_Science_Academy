#!/usr/bin/env python3
"""
Migration script to create conflict resolution tables.
"""

from app import create_app, db
from models import GroupConflict, ConflictResolution, ConflictParticipant

def create_conflict_resolution_tables():
    """Create conflict resolution tables."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the tables
            GroupConflict.__table__.create(db.engine, checkfirst=True)
            ConflictResolution.__table__.create(db.engine, checkfirst=True)
            ConflictParticipant.__table__.create(db.engine, checkfirst=True)
            
            print("✅ Conflict resolution tables created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating conflict resolution tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    create_conflict_resolution_tables()

