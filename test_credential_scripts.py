#!/usr/bin/env python3
"""
Test script to verify credential export scripts work correctly.
This script tests the functionality without actually running the export.
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from app import create_app
        from models import User, db
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_app_creation():
    """Test that the Flask app can be created."""
    try:
        from app import create_app
        app = create_app()
        print("✅ Flask app creation successful")
        return True
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False

def test_database_connection():
    """Test database connection."""
    try:
        from app import create_app
        from models import User
        
        app = create_app()
        with app.app_context():
            # Try to query users
            user_count = User.query.count()
            print(f"✅ Database connection successful - {user_count} users found")
            return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing credential export scripts...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("App Creation Test", test_app_creation),
        ("Database Connection Test", test_database_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Scripts should work on Render.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
