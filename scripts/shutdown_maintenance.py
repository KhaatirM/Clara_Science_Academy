#!/usr/bin/env python3
"""
Emergency Maintenance Shutdown Script
=====================================

This script can be run on OnRender using the shell command to immediately
shutdown maintenance mode if needed.

Usage on OnRender:
1. Go to your OnRender dashboard
2. Click on your service
3. Go to "Shell" tab
4. Run: python shutdown_maintenance.py

This script will:
- Connect to the database
- Set all maintenance sessions to inactive
- Provide confirmation of the shutdown
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import MaintenanceMode, db
    
    def shutdown_maintenance():
        """Shutdown all active maintenance sessions."""
        print("=" * 60)
        print("EMERGENCY MAINTENANCE SHUTDOWN")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            try:
                # Check current maintenance status
                active_maintenance = MaintenanceMode.query.filter_by(is_active=True).all()
                
                if not active_maintenance:
                    print("✅ No active maintenance sessions found.")
                    print("System is already in normal operation mode.")
                    return
                
                print(f"🔍 Found {len(active_maintenance)} active maintenance session(s):")
                for maintenance in active_maintenance:
                    print(f"   - ID: {maintenance.id}")
                    print(f"     Started: {maintenance.start_time}")
                    print(f"     End Time: {maintenance.end_time}")
                    print(f"     Reason: {maintenance.reason}")
                    print(f"     Message: {maintenance.maintenance_message}")
                    print()
                
                # Shutdown all maintenance sessions
                print("🛑 Shutting down maintenance mode...")
                MaintenanceMode.query.update({'is_active': False})
                db.session.commit()
                
                print("✅ SUCCESS: All maintenance sessions have been deactivated!")
                print("🌐 Users can now access the system normally.")
                print()
                print("Next steps:")
                print("1. Verify the system is accessible")
                print("2. Check application logs for any issues")
                print("3. Notify users that maintenance is complete")
                
            except Exception as e:
                print(f"❌ ERROR: Failed to shutdown maintenance mode: {str(e)}")
                print("Please check your database connection and try again.")
                return 1
                
        return 0
        
    if __name__ == "__main__":
        exit_code = shutdown_maintenance()
        sys.exit(exit_code)
        
except ImportError as e:
    print("❌ ERROR: Could not import required modules.")
    print(f"Import error: {str(e)}")
    print()
    print("Make sure you're running this script from the correct directory")
    print("and that all dependencies are installed.")
    sys.exit(1)
except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {str(e)}")
    sys.exit(1)
