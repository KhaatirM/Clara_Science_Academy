#!/usr/bin/env python3
"""
Test script for the maintenance shutdown functionality
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import MaintenanceMode, db
    
    def test_maintenance_shutdown():
        """Test the maintenance shutdown functionality."""
        print("Testing Maintenance Shutdown Functionality")
        print("=" * 50)
        
        app = create_app()
        
        with app.app_context():
            try:
                # Check current maintenance status
                active_maintenance = MaintenanceMode.query.filter_by(is_active=True).all()
                print(f"Current active maintenance sessions: {len(active_maintenance)}")
                
                if active_maintenance:
                    for maintenance in active_maintenance:
                        print(f"  - ID: {maintenance.id}")
                        print(f"    Start: {maintenance.start_time}")
                        print(f"    End: {maintenance.end_time}")
                        print(f"    Reason: {maintenance.reason}")
                
                # Test shutdown
                print("\nTesting shutdown...")
                MaintenanceMode.query.update({'is_active': False})
                db.session.commit()
                
                # Verify shutdown
                active_after = MaintenanceMode.query.filter_by(is_active=True).all()
                print(f"Active maintenance sessions after shutdown: {len(active_after)}")
                
                if len(active_after) == 0:
                    print("✅ Test PASSED: Maintenance shutdown works correctly")
                else:
                    print("❌ Test FAILED: Maintenance sessions still active")
                    
            except Exception as e:
                print(f"❌ Test FAILED with error: {str(e)}")
                return False
                
        return True
        
    if __name__ == "__main__":
        success = test_maintenance_shutdown()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ Import error: {str(e)}")
    sys.exit(1)
