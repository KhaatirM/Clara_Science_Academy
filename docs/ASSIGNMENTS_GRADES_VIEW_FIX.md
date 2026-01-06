# Assignments & Grades View - Group Assignments Fix

## Date: October 15, 2025

## Issues Fixed

### 1. Template Syntax Error
**Problem**: `expected token 'end of statement block', got '['` error when accessing the grades view.

**Root Cause**: Line 69 in `templates/management/assignments_and_grades.html` used invalid Jinja2 syntax:
```jinja2
{{ class_assignments[class_obj.id] }} assignments
```

**Solution**: Changed to valid Jinja2 syntax:
```jinja2
{{ class_assignments.get(class_obj.id, 0) }} assignments
```

### 2. Group Assignments Missing in Grades View
**Problem**: When viewing "Assignments & Grades" page and clicking "Grades" view, only individual assignments were displayed. Group assignments were completely missing from the table.

**Root Cause**: The `assignments_and_grades` route was fetching group assignments but:
1. Not processing their grade data
2. Not including them in the template loop
3. Only displaying `class_assignments` in the grades table

**Solution**: 
- Updated the route to process group assignment grades
- Modified the template to display both individual and group assignments
- Added visual distinction with badges (Individual = blue, Group = teal)

---

## Files Modified

### 1. `managementroutes.py` (lines 2379-2445)
**Changes**:
- Added processing for group assignment grades
- Used special key format `group_{group_assignment_id}` for group assignment grades
- Added `type` field to distinguish individual vs group assignments
- Included group assignment object in grade data for template use

**New Code**:
```python
# Get grade data for each group assignment
for group_assignment in group_assignments:
    # Get group grades for this assignment
    from models import GroupGrade
    group_grades = GroupGrade.query.filter_by(group_assignment_id=group_assignment.id).all()
    
    # Process group grade data safely
    graded_group_grades = []
    total_score = 0
    for gg in group_grades:
        if gg.grade_data is not None:
            try:
                # Handle both dict and JSON string cases
                if isinstance(gg.grade_data, dict):
                    grade_dict = gg.grade_data
                else:
                    import json
                    grade_dict = json.loads(gg.grade_data)
                
                if 'score' in grade_dict:
                    graded_group_grades.append(grade_dict)
                    total_score += grade_dict['score']
            except (json.JSONDecodeError, TypeError):
                # Skip invalid grade data
                continue
    
    # Use a special key format for group assignments
    assignment_grades[f'group_{group_assignment.id}'] = {
        'grades': group_grades,
        'total_submissions': len(group_grades),
        'graded_count': len(graded_group_grades),
        'average_score': round(total_score / len(graded_group_grades), 1) if graded_group_grades else 0,
        'type': 'group',
        'assignment': group_assignment  # Store the assignment object for template use
    }
```

### 2. `templates/management/assignments_and_grades.html` (lines 69, 419-521)
**Changes**:
- Fixed template syntax error on line 69
- Added group assignments loop to grades view
- Added visual badges to distinguish assignment types
- Updated action buttons for group assignments

**Template Updates**:
```jinja2
<!-- Individual Assignments -->
{% for assignment in class_assignments %}
    <!-- Individual assignment row with blue "Individual" badge -->
{% endfor %}

<!-- Group Assignments -->
{% for group_assignment in group_assignments %}
    {% set grade_info = assignment_grades.get('group_' ~ group_assignment.id, {}) %}
    <tr>
        <td>
            <strong>{{ group_assignment.title }}</strong><br>
            <small class="text-muted">{{ group_assignment.assignment_type or 'Group Assignment' }}</small>
            <span class="badge bg-info ms-2">Group</span>
        </td>
        <!-- ... rest of group assignment row ... -->
    </tr>
{% endfor %}
```

---

## Visual Improvements

### Assignment Type Badges
- **Individual Assignments**: Blue "Individual" badge
- **Group Assignments**: Teal "Group" badge

### Action Buttons
Group assignments have appropriate action buttons:
- **View**: `viewGroupAssignment({{ group_assignment.id }})`
- **Grade**: `gradeGroupAssignment({{ group_assignment.id }})`
- **Edit**: `editGroupAssignment({{ group_assignment.id }})`
- **Remove**: `removeGroupAssignment({{ group_assignment.id }})`

### Grade Data Processing
- Group assignments use special key format: `group_{group_assignment_id}`
- Grade statistics calculated separately for group vs individual assignments
- Both types included in overall class statistics

---

## Testing Results

✅ **Template Syntax Error**: Fixed - no more Jinja2 syntax errors  
✅ **Group Assignments Display**: Now visible in grades view  
✅ **Visual Distinction**: Clear badges differentiate assignment types  
✅ **Grade Statistics**: Group assignment grades properly calculated  
✅ **Action Buttons**: Appropriate buttons for group assignment management  

---

## URL Structure

The fixes apply to the following URL pattern:
```
/management/assignments-and-grades?class_id=6&view=grades
```

Where:
- `class_id=6` filters to a specific class
- `view=grades` shows the grades table view (not assignments view)

---

## Benefits

1. **Complete Data Visibility**: Administrators can now see all assignments (individual + group) in one view
2. **No Template Errors**: Fixed Jinja2 syntax error that was causing 500 errors
3. **Clear Visual Distinction**: Easy to identify assignment types at a glance
4. **Proper Grade Tracking**: Group assignment grades are properly calculated and displayed
5. **Consistent Interface**: Same action patterns for both assignment types

---

## Future Considerations

- Consider adding group assignment counts to the class selection cards
- May want to add filtering options (show only individual, only group, or both)
- Consider adding bulk actions for group assignments
- Could add group membership information in the grades view

