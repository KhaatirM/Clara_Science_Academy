#!/usr/bin/env python3
"""
Emergency Fix Script for Assignment Creation Issue
Run this on Render shell: python fix_assignment_creation.py
"""

from app import create_app
from extensions import db
from models import Assignment, Class, SchoolYear
from datetime import datetime

app = create_app()

def main():
    with app.app_context():
        print("="*70)
        print("ASSIGNMENT CREATION DIAGNOSTIC & FIX")
        print("="*70)
        
        # Step 1: Check current state
        print("\n[1] Checking current state...")
        total_assignments = Assignment.query.count()
        print(f"    Total assignments in database: {total_assignments}")
        
        class_11 = Class.query.filter_by(id=11).first()
        if class_11:
            print(f"    Class 11: {class_11.name} - {class_11.subject}")
            class_11_assignments = Assignment.query.filter_by(class_id=11).count()
            print(f"    Assignments for class 11: {class_11_assignments}")
        else:
            print("    ✗ Class 11 not found!")
            return
        
        # Step 2: Check active school year
        print("\n[2] Checking school year...")
        school_year = SchoolYear.query.filter_by(is_active=True).first()
        if school_year:
            print(f"    Active school year: {school_year.name} (ID: {school_year.id})")
        else:
            print("    ✗ ERROR: No active school year found!")
            print("    This is likely the problem. Creating active school year...")
            # Try to find ANY school year
            any_sy = SchoolYear.query.first()
            if any_sy:
                any_sy.is_active = True
                db.session.commit()
                print(f"    ✓ Activated school year: {any_sy.name}")
                school_year = any_sy
            else:
                print("    ✗ No school years exist at all!")
                return
        
        # Step 3: Test creating an assignment
        print("\n[3] Testing assignment creation...")
        test_assignment = Assignment()
        test_assignment.title = f"TEST - Created by fix script at {datetime.now()}"
        test_assignment.description = "This is a test assignment created by the diagnostic script"
        test_assignment.due_date = datetime(2025, 10, 30, 23, 59, 0)
        test_assignment.class_id = 11
        test_assignment.school_year_id = school_year.id
        test_assignment.quarter = "1"
        test_assignment.status = "Active"
        test_assignment.assignment_type = "pdf"
        
        try:
            db.session.add(test_assignment)
            db.session.commit()
            print(f"    ✓ SUCCESS: Test assignment created with ID: {test_assignment.id}")
            print(f"    Title: {test_assignment.title}")
            print(f"    Class: {test_assignment.class_id}")
            print(f"    Quarter: {test_assignment.quarter}")
            
            # Verify it's queryable
            verify = Assignment.query.filter_by(id=test_assignment.id).first()
            if verify:
                print(f"    ✓ VERIFIED: Assignment is in database and queryable")
            else:
                print(f"    ✗ WARNING: Assignment saved but not queryable!")
                
        except Exception as e:
            print(f"    ✗ ERROR creating test assignment: {e}")
            print(f"    Error type: {type(e).__name__}")
            db.session.rollback()
            return
        
        # Step 4: Check recent assignments
        print("\n[4] Checking 10 most recent assignments...")
        recent = Assignment.query.order_by(Assignment.created_at.desc()).limit(10).all()
        for i, assignment in enumerate(recent, 1):
            print(f"    {i}. ID:{assignment.id} | Class:{assignment.class_id} | {assignment.title[:40]} | Created:{assignment.created_at}")
        
        # Step 5: Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        final_count = Assignment.query.filter_by(class_id=11).count()
        print(f"Current assignments for class 11: {final_count}")
        
        if final_count > class_11_assignments:
            print("✓ Assignment creation is WORKING!")
            print("\nThe issue might be:")
            print("  1. Form validation in the web interface")
            print("  2. JavaScript blocking submission")
            print("  3. CSRF token issues")
            print("  4. Browser caching old JavaScript")
            print("\nRECOMMENDED FIX:")
            print("  - Clear browser cache and try again")
            print("  - Check browser console for JavaScript errors")
            print("  - Try from a different browser/incognito mode")
        else:
            print("✗ There may still be an issue")
            print("\nPossible causes:")
            print("  1. No active school year (check above)")
            print("  2. Database constraints")
            print("  3. Code not deployed properly")
        
        print("\n" + "="*70)

if __name__ == "__main__":
    main()

