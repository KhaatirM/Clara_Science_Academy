#!/usr/bin/env python3
"""
Migration script to create comprehensive reporting and analytics tables.
This script adds the final set of tables for the enhanced group management system.
"""

from app import create_app, db
from models import (
    GroupWorkReport, IndividualContribution, TimeTracking, 
    CollaborationMetrics, ReportExport, AnalyticsDashboard, PerformanceBenchmark
)

def create_reporting_analytics_tables():
    """Create all reporting and analytics tables."""
    app = create_app()
    
    with app.app_context():
        try:
            print("Creating comprehensive reporting and analytics tables...")
            
            # Create each table individually
            GroupWorkReport.__table__.create(db.engine, checkfirst=True)
            print("✓ Created GroupWorkReport table")
            
            IndividualContribution.__table__.create(db.engine, checkfirst=True)
            print("✓ Created IndividualContribution table")
            
            TimeTracking.__table__.create(db.engine, checkfirst=True)
            print("✓ Created TimeTracking table")
            
            CollaborationMetrics.__table__.create(db.engine, checkfirst=True)
            print("✓ Created CollaborationMetrics table")
            
            ReportExport.__table__.create(db.engine, checkfirst=True)
            print("✓ Created ReportExport table")
            
            AnalyticsDashboard.__table__.create(db.engine, checkfirst=True)
            print("✓ Created AnalyticsDashboard table")
            
            PerformanceBenchmark.__table__.create(db.engine, checkfirst=True)
            print("✓ Created PerformanceBenchmark table")
            
            print("\n🎉 All comprehensive reporting and analytics tables created successfully!")
            print("\nTables created:")
            print("- GroupWorkReport: Comprehensive group work reports and analytics")
            print("- IndividualContribution: Individual student contributions tracking")
            print("- TimeTracking: Time spent on group assignments and activities")
            print("- CollaborationMetrics: Collaboration metrics and group dynamics")
            print("- ReportExport: Report exports and downloads tracking")
            print("- AnalyticsDashboard: Dashboard configurations and saved views")
            print("- PerformanceBenchmark: Performance benchmarks and standards")
            
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    create_reporting_analytics_tables()
