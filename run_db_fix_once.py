#!/usr/bin/env python3
"""
One-time database fix script for Render production.
This script can be run manually or as part of deployment.
"""

import os
import sys

def main():
    """Run the database fix once."""
    print("🔧 Running one-time database fix for production...")
    
    try:
        # Import and run the database fix function
        from app import run_production_database_fix
        run_production_database_fix()
        print("✅ Database fix completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
