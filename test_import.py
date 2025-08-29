#!/usr/bin/env python3
"""Test file to check imports"""

try:
    print("Testing basic imports...")
    from flask import Flask
    print("✓ Flask imported successfully")
    
    print("Testing managementroutes import...")
    from managementroutes import management_blueprint
    print("✓ managementroutes imported successfully")
    
    print("All imports successful!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()

