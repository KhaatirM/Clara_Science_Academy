#!/usr/bin/env python3
"""
Migration script to create enhanced group management tables.
"""

from app import create_app, db
from models import (
    GroupTemplate, PeerEvaluation, AssignmentRubric, GroupContract,
    ReflectionJournal, GroupProgress, AssignmentTemplate
)

def create_enhanced_group_tables():
    """Create the enhanced group management tables."""
    app = create_app()
    with app.app_context():
        try:
            # Create all new tables
            db.create_all()
            print("✅ Enhanced group management tables created successfully!")
            print("Created tables:")
            print("  - group_template")
            print("  - peer_evaluation") 
            print("  - assignment_rubric")
            print("  - group_contract")
            print("  - reflection_journal")
            print("  - group_progress")
            print("  - assignment_template")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
        
        return True

if __name__ == "__main__":
    create_enhanced_group_tables()
