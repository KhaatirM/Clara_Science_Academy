"""
Diagnostic script to check assignment_context values in the database
and identify why some in-class assignments are showing as homework.
"""

from app import create_app, db
from models import Assignment, GroupAssignment

def diagnose_assignment_context():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("DIAGNOSING ASSIGNMENT CONTEXT VALUES")
        print("=" * 70)
        
        # Check regular assignments
        print("\n[1] Regular Assignments - Context Value Analysis:")
        assignments = Assignment.query.all()
        
        context_values = {}
        problematic = []
        
        for assignment in assignments:
            context = assignment.assignment_context
            if context:
                context_lower = context.lower()
                context_values[context] = context_values.get(context, 0) + 1
                
                # Check if it should be in-class but might not be detected
                is_inclass = (
                    'in-class' in context_lower or 
                    'in_class' in context_lower or 
                    'inclass' in context_lower
                )
                
                if is_inclass and context != 'in-class':
                    problematic.append({
                        'id': assignment.id,
                        'title': assignment.title[:50],
                        'current_value': context,
                        'should_be': 'in-class'
                    })
        
        print(f"\n  Total assignments: {len(assignments)}")
        print(f"  Unique context values found:")
        for value, count in sorted(context_values.items()):
            print(f"    '{value}': {count} assignments")
        
        if problematic:
            print(f"\n  ⚠ Found {len(problematic)} assignments with problematic values:")
            for item in problematic[:10]:  # Show first 10
                print(f"    ID {item['id']}: '{item['current_value']}' -> should be 'in-class'")
                print(f"      Title: {item['title']}")
        
        # Check group assignments
        print("\n[2] Group Assignments - Context Value Analysis:")
        group_assignments = GroupAssignment.query.all()
        
        group_context_values = {}
        group_problematic = []
        
        for assignment in group_assignments:
            context = assignment.assignment_context
            if context:
                context_lower = context.lower()
                group_context_values[context] = group_context_values.get(context, 0) + 1
                
                # Check if it should be in-class but might not be detected
                is_inclass = (
                    'in-class' in context_lower or 
                    'in_class' in context_lower or 
                    'inclass' in context_lower
                )
                
                if is_inclass and context != 'in-class':
                    group_problematic.append({
                        'id': assignment.id,
                        'title': assignment.title[:50],
                        'current_value': context,
                        'should_be': 'in-class'
                    })
        
        print(f"\n  Total group assignments: {len(group_assignments)}")
        print(f"  Unique context values found:")
        for value, count in sorted(group_context_values.items()):
            print(f"    '{value}': {count} assignments")
        
        if group_problematic:
            print(f"\n  ⚠ Found {len(group_problematic)} group assignments with problematic values:")
            for item in group_problematic[:10]:  # Show first 10
                print(f"    ID {item['id']}: '{item['current_value']}' -> should be 'in-class'")
                print(f"      Title: {item['title']}")
        
        # Show sample assignments that might be incorrectly labeled
        print("\n[3] Sample Assignments (showing first 20):")
        print("  Regular Assignments:")
        for assignment in assignments[:20]:
            context = assignment.assignment_context or 'None'
            context_lower = context.lower() if context else ''
            is_inclass = (
                context_lower and (
                    'in-class' in context_lower or 
                    'in_class' in context_lower or 
                    'inclass' in context_lower
                )
            )
            badge = "IN-Class" if is_inclass else "Homework"
            print(f"    ID {assignment.id}: '{context}' -> Badge: {badge} | {assignment.title[:50]}")
        
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)
        if problematic or group_problematic:
            print("Run 'fix_assignment_context_and_creator.py' to normalize all values to 'in-class' or 'homework'")
        else:
            print("All context values appear to be normalized.")
            print("If badges are still incorrect, the issue may be in the template logic.")

if __name__ == '__main__':
    diagnose_assignment_context()

