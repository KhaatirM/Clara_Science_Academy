# Admin View Redirect Fixes - Summary

## Issue
When School Administrators and Directors click buttons in the Class Management view (accessed via "View Class"), they are redirected to teacher views instead of staying in the management context. This affects:

1. Group Assignments
2. Deadline Reminders  
3. Reports & Analytics
4. 360° Feedback
5. Reflection Journals
6. Conflict Resolution

## Root Cause
Templates were using `role_prefix` variable or hardcoded teacher routes without properly checking and passing the `admin_view=true` parameter through all navigation links and action buttons.

## Solution Pattern
For each affected template, we need to:

1. **Check for `admin_view` parameter** in the route
2. **Pass `admin_view=true` in URLs** when admin_view is active
3. **Use conditional back buttons** that route to `management.view_class` when `admin_view=true`, otherwise to `teacher.view_class`
4. **Apply to ALL links and forms** in the template, not just the header

### Template Fix Pattern

```jinja
{# Header back button #}
{% if admin_view %}
  <a href="{{ url_for('management.view_class', class_id=class_obj.id) }}">Back to Management</a>
{% else %}
  <a href="{{ url_for('teacher.view_class', class_id=class_obj.id) }}">Back to Class</a>
{% endif %}

{# Action buttons - append admin_view parameter #}
<a href="{{ url_for('teacher.some_action', id=item.id) }}{% if admin_view %}?admin_view=true{% endif %}">Action</a>

{# Forms - include admin_view in action URL #}
<form action="{{ url_for('teacher.some_action', id=item.id) }}{% if admin_view %}?admin_view=true{% endif %}">
  ...
</form>
```

## Templates Fixed ✅

### 1. Group Assignments (`teacher_class_group_assignments.html`)
- ✅ Fixed header "Back" button to check `admin_view`
- ✅ Fixed "Create Group Assignment" button
- ✅ Fixed "View Details" action button
- ✅ Fixed "Grade Assignment" action button
- ✅ Fixed "Create Your First Group Assignment" button
- ✅ Removed `role_prefix` conditional logic

### 2. Deadline Reminders (`teacher_class_deadline_reminders.html`)
- ✅ Fixed header "Back" button to check `admin_view`
- ✅ Fixed "Create Reminder" button
- ✅ Fixed "Edit" action button
- ✅ Fixed "Toggle Active/Inactive" form action
- ✅ Fixed "Send Now" form action
- ✅ Fixed "Delete" form action
- ✅ Fixed "Create First Reminder" button
- ✅ Fixed Quick Actions section buttons
- ✅ Removed `role_prefix` conditional logic

## Templates Still Need Fixing ⚠️

### 3. Reports & Analytics (`teacher_class_analytics.html`)
**Status:** Pending
**What needs fixing:**
- Back button
- All navigation links within analytics sections
- Export/download buttons
- Any drill-down links

### 4. 360° Feedback (`teacher_class_360_feedback.html`)
**Status:** Pending
**What needs fixing:**
- Back button
- "Create 360° Feedback" button
- "View Details" links
- "Edit" links
- "Delete" form actions
- Any student/group selection links

### 5. Reflection Journals (`teacher_class_reflection_journals.html`)
**Status:** Pending
**What needs fixing:**
- Back button
- "View Journal" links
- "Comment" links
- Any filtering/sorting links

### 6. Conflict Resolution (`teacher_class_conflicts.html`)
**Status:** Pending
**What needs fixing:**
- Back button
- "Add Conflict" button
- "View Conflict" links
- "Resolve" buttons
- "Edit" links
- "Delete" form actions

## Related Templates That May Need Fixes

These templates are accessed from the main class views and should also be checked:

- `teacher_view_group_assignment.html` - View details of a group assignment
- `teacher_grade_group_assignment.html` - Grade a group assignment
- `teacher_group_assignment_type_selector.html` - Select type when creating
- `teacher_edit_deadline_reminder.html` - Edit a reminder
- `teacher_create_deadline_reminder.html` - Create new reminder
- `teacher_group_analytics.html` - Group-specific analytics
- `teacher_view_360_feedback.html` - View feedback details
- `teacher_create_360_feedback.html` - Create new feedback
- `teacher_view_reflection_journal.html` - View journal details
- `teacher_view_conflict.html` - View conflict details
- `teacher_resolve_conflict.html` - Resolve conflict interface

## Additional Task: Assignments & Grades Tab

**Status:** Pending

Need to add Group Assignments and their grades to the management `assignments_and_grades` tab.

### Current State
- Management Assignments & Grades tab shows regular assignments only
- Group assignments are not visible in this tab

### Required Changes
1. Update `managementroutes.py` - `assignments_and_grades()` function to include group assignments
2. Update `templates/management/assignments_and_grades.html` to display group assignments alongside regular assignments
3. Ensure group assignment grading links work correctly from management view
4. Add appropriate filtering/sorting for group vs regular assignments

## Testing Checklist

For each fixed template, verify:
- [ ] Clicking buttons from management view stays in management context
- [ ] Back buttons return to `management.view_class`
- [ ] All action buttons (View, Edit, Grade, Delete, etc.) maintain admin_view
- [ ] Form submissions maintain admin_view
- [ ] After completing an action, user returns to management view (not teacher view)
- [ ] Links to create new items maintain admin_view
- [ ] Teacher access still works normally (without admin_view parameter)

## Next Steps

1. Complete fixes for remaining templates (Analytics, 360 Feedback, Reflection Journals, Conflict Resolution)
2. Fix related sub-templates that are accessed from main templates
3. Add Group Assignments to Assignments & Grades tab
4. Test all workflows from management view
5. Verify teacher view still works correctly

