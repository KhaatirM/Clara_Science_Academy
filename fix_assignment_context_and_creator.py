"""
Script to fix assignment_context values and help identify assignments that need creator information.
This script will:
1. Check and report assignment_context values
2. Fix any incorrect assignment_context values (in_class -> in-class, etc.)
3. Report assignments without creators (for manual review)
"""

from app import create_app, db
from models import Assignment, GroupAssignment
from sqlalchemy import text

def fix_assignment_context():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("FIXING ASSIGNMENT CONTEXT VALUES")
        print("=" * 70)
        
        # Check regular assignments
        print("\n[1] Checking regular assignments...")
        assignments = Assignment.query.all()
        
        context_counts = {}
        fixed_count = 0
        
        for assignment in assignments:
            context = assignment.assignment_context
            if context:
                context_lower = context.lower()
                context_counts[context] = context_counts.get(context, 0) + 1
                
                # Fix variations of in-class
                if context_lower in ['in_class', 'inclass', 'in-class']:
                    if context != 'in-class':
                        print(f"  Fixing assignment {assignment.id} ({assignment.title[:50]}): '{context}' -> 'in-class'")
                        assignment.assignment_context = 'in-class'
                        fixed_count += 1
                # Ensure homework is consistent
                elif context_lower in ['homework', 'hw']:
                    if context != 'homework':
                        assignment.assignment_context = 'homework'
                        fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✓ Fixed {fixed_count} regular assignment context values")
        else:
            print("  No fixes needed for regular assignments")
        
        print(f"\n  Context value distribution:")
        for context, count in sorted(context_counts.items()):
            print(f"    '{context}': {count}")
        
        # Check group assignments
        print("\n[2] Checking group assignments...")
        group_assignments = GroupAssignment.query.all()
        
        group_context_counts = {}
        group_fixed_count = 0
        
        for assignment in group_assignments:
            context = assignment.assignment_context
            if context:
                context_lower = context.lower()
                group_context_counts[context] = group_context_counts.get(context, 0) + 1
                
                # Fix variations of in-class
                if context_lower in ['in_class', 'inclass', 'in-class']:
                    if context != 'in-class':
                        print(f"  Fixing group assignment {assignment.id} ({assignment.title[:50]}): '{context}' -> 'in-class'")
                        assignment.assignment_context = 'in-class'
                        group_fixed_count += 1
                # Ensure homework is consistent
                elif context_lower in ['homework', 'hw']:
                    if context != 'homework':
                        assignment.assignment_context = 'homework'
                        group_fixed_count += 1
        
        if group_fixed_count > 0:
            db.session.commit()
            print(f"\n✓ Fixed {group_fixed_count} group assignment context values")
        else:
            print("  No fixes needed for group assignments")
        
        print(f"\n  Context value distribution:")
        for context, count in sorted(group_context_counts.items()):
            print(f"    '{context}': {count}")
        
        # Report assignments without creators
        print("\n[3] Checking assignments without creators...")
        assignments_without_creator = Assignment.query.filter(Assignment.created_by.is_(None)).all()
        group_assignments_without_creator = GroupAssignment.query.filter(GroupAssignment.created_by.is_(None)).all()
        
        print(f"\n  Regular assignments without creator: {len(assignments_without_creator)}")
        if assignments_without_creator:
            print("  Sample assignments (first 10):")
            for assignment in assignments_without_creator[:10]:
                print(f"    ID: {assignment.id} | Title: {assignment.title[:50]} | Class: {assignment.class_id} | Created: {assignment.created_at}")
        
        print(f"\n  Group assignments without creator: {len(group_assignments_without_creator)}")
        if group_assignments_without_creator:
            print("  Sample group assignments (first 10):")
            for assignment in group_assignments_without_creator[:10]:
                print(f"    ID: {assignment.id} | Title: {assignment.title[:50]} | Class: {assignment.class_id} | Created: {assignment.created_at}")
        
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✓ Fixed {fixed_count} regular assignment context values")
        print(f"✓ Fixed {group_fixed_count} group assignment context values")
        print(f"⚠ {len(assignments_without_creator)} regular assignments need creator information")
        print(f"⚠ {len(group_assignments_without_creator)} group assignments need creator information")
        print("\nNote: Assignments without creators will show 'Unknown' in the interface.")
        print("New assignments will automatically have their creator tracked.")

if __name__ == '__main__':
    fix_assignment_context()

