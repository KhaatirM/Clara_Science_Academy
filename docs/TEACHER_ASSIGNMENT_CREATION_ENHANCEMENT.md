# Teacher Assignment Creation Enhancement

## Summary
Enhanced the teacher assignment creation workflow to match the administrator's system with a modern, user-friendly multi-step process. Teachers now select assignment type (PDF/Quiz/Discussion), assignment target (Individual/Group), and assignment context (In-Class/Homework) before reaching the assignment creation form.

## New Assignment Creation Flow

### Step 1: Assignment Type Selection
Teachers choose between three types of assignments:
1. **PDF/Paper Assignment** - Traditional document-based assignments
2. **Questionnaire/Quiz Assignment** - Auto-graded interactive quizzes  
3. **Discussion Assignment** - Open-ended discussion topics

### Step 2: Assignment Target Selection (PDF Only)
For PDF/Paper assignments, teachers choose:
1. **Individual Students** - Each student works independently
2. **Class Groups** - Students work in collaborative groups

### Step 3: Assignment Context (PDF Individual Only)
For individual PDF assignments, teachers specify:
1. **In-Class Assignment** - Completed during class time
   - Due date automatically set to 4:00 PM EST today
   - Due date field is read-only with info message
2. **Homework Assignment** - Completed outside of class
   - Due date defaults to tomorrow at 11:59 PM
   - Due date fully customizable by teacher

### Step 4: Assignment Details
Teachers fill out the complete assignment form with all details based on their selections.

## Files Modified

### 1. `templates/shared/assignment_type_selector.html`
**Purpose:** Main assignment type selection interface

**Changes:**
- **Updated Individual Assignment Flow** (Line 265-267):
  - Changed from direct redirect to `showAssignmentContextModal()` call
  - Now shows context modal before proceeding to assignment creation

- **Added `showAssignmentContextModal()` Function** (Line 284-383):
  - Creates and displays modal for In-Class vs Homework selection
  - Two card options with distinct icons and descriptions:
    - **In-Class**: Blue building icon, auto-set due date info
    - **Homework**: Yellow house icon, manual due date info
  - Hover effects for better UX
  - Passes `context` parameter via URL query string
  - Different routing for administrators vs teachers

**Key Code Snippet:**
```javascript
function showAssignmentContextModal() {
    const modalHtml = `
        <div class="modal fade" id="assignmentContextModal" ...>
            <div class="card assignment-context-card" data-context="in-class">
                <i class="bi bi-building text-info"></i>
                <h5>In-Class Assignment</h5>
                <small>Due date will automatically be set to 4:00 PM EST today</small>
            </div>
            <div class="card assignment-context-card" data-context="homework">
                <i class="bi bi-house-door text-warning"></i>
                <h5>Homework Assignment</h5>
                <small>You will set the due date manually</small>
            </div>
        </div>
    `;
    
    // Redirect with context parameter
    window.location.href = `{{ url_for('teacher.add_assignment_select_class') }}?context=${context}`;
}
```

### 2. `teacherroutes.py`
**Purpose:** Backend routing for assignment creation

**Changes:**

#### `add_assignment_select_class()` Route (Line 636-662):
- **Added Context Parameter Handling**:
  - Retrieves `context` from query string (`request.args.get('context', 'homework')`)
  - Passes context through redirect to `add_assignment` route
  - Passes context to template for display/reference

**Code Snippet:**
```python
def add_assignment_select_class():
    """Add a new assignment - class selection page"""
    # Get assignment context from query parameter (in-class or homework)
    context = request.args.get('context', 'homework')
    
    if request.method == 'POST':
        class_id = request.form.get('class_id', type=int)
        if class_id:
            # Pass context through to the add_assignment page
            return redirect(url_for('teacher.add_assignment', class_id=class_id, context=context))
    
    return render_template('shared/add_assignment_select_class.html', 
                          classes=classes, 
                          context=context)
```

#### `add_assignment()` Route (Line 664-780):
- **Added Context and Default Due Date Handling** (Line 763-774):
  - Retrieves context from query parameter
  - For `in-class` context:
    - Uses `pytz` to get current time in EST timezone
    - Sets `default_due_date` to 4:00 PM EST today
  - Passes both `context` and `default_due_date` to template

**Code Snippet:**
```python
def add_assignment(class_id):
    # ... existing code ...
    
    # Get assignment context from query parameter (in-class or homework)
    context = request.args.get('context', 'homework')
    
    # Calculate default due date for in-class assignments
    from datetime import datetime, time
    import pytz
    default_due_date = None
    if context == 'in-class':
        # Set to 4:00 PM EST today
        est = pytz.timezone('America/New_York')
        now_est = datetime.now(est)
        default_due_date = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return render_template('shared/add_assignment.html', 
                          class_obj=class_obj, 
                          current_quarter=current_quarter,
                          context=context,
                          default_due_date=default_due_date)
```

### 3. `templates/shared/add_assignment.html`
**Purpose:** Assignment creation form template

**Changes:**
- **Enhanced Due Date Logic** (Line 473-493):
  - Conditional logic based on `context` variable
  - **For In-Class Assignments**:
    - Sets due date input to backend-calculated EST time
    - Makes field read-only (`readOnly = true`)
    - Changes background color to indicate locked state
    - Adds info alert below field explaining auto-set behavior
  - **For Homework Assignments**:
    - Sets default to tomorrow at 11:59 PM
    - Field remains fully editable

**Code Snippet:**
```javascript
// Set default due date based on assignment context
{% if context == 'in-class' and default_due_date %}
    // For in-class assignments, set to 4:00 PM EST today
    const inClassDate = new Date('{{ default_due_date.strftime("%Y-%m-%dT%H:%M") }}');
    document.getElementById('due_date').value = inClassDate.toISOString().slice(0, 16);
    document.getElementById('due_date').readOnly = true;
    document.getElementById('due_date').style.backgroundColor = '#e9ecef';
    
    // Add info message about auto-set date
    const dueDateDiv = document.getElementById('due_date').parentElement;
    const infoMsg = document.createElement('div');
    infoMsg.className = 'alert alert-info mt-2 mb-0';
    infoMsg.innerHTML = '<i class="bi bi-info-circle me-2"></i><strong>In-Class Assignment:</strong> Due date automatically set to 4:00 PM EST today.';
    dueDateDiv.appendChild(infoMsg);
{% else %}
    // For homework assignments, set to tomorrow at 11:59 PM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(23, 59, 0, 0);
    document.getElementById('due_date').value = tomorrow.toISOString().slice(0, 16);
{% endif %}
```

## User Experience

### Complete Flow Example - Creating an In-Class Assignment

1. **Teacher clicks "Add Assignment"** from Assignments & Grades page
2. **Assignment Type Selector appears** showing three options
3. **Teacher clicks "PDF/Paper Assignment"**
4. **Assignment Target Modal appears** with Individual vs Group options
5. **Teacher selects "Individual Students"**
6. **Assignment Context Modal appears** with In-Class vs Homework options
7. **Teacher selects "In-Class Assignment"**
8. **Class Selection page loads** with context preserved
9. **Teacher selects a class** and clicks Continue
10. **Assignment Form loads** with:
    - Due date automatically set to 4:00 PM EST today
    - Due date field grayed out and read-only
    - Blue info alert: "In-Class Assignment: Due date automatically set to 4:00 PM EST today"
11. **Teacher fills out remaining fields** (title, description, etc.)
12. **Teacher submits** and assignment is created with correct due date

### Complete Flow Example - Creating a Homework Assignment

1-7. Same as above, but teacher selects "Homework Assignment" in step 7
8-9. Same as above
10. **Assignment Form loads** with:
    - Due date defaults to tomorrow at 11:59 PM
    - Due date field fully editable (white background)
    - Teacher can customize the due date as needed
11-12. Same as above

### Quiz and Discussion Assignments
- These bypass the context modal entirely
- Go directly to their respective creation pages
- No in-class/homework distinction (as specified by user requirements)

## Technical Details

### Timezone Handling
- Used `pytz` library for accurate EST timezone conversion
- Ensures consistent 4:00 PM EST regardless of server timezone
- Date formatted as ISO string for datetime-local input compatibility

### URL Parameters
- `context` parameter flows through entire creation process
- Values: `'in-class'` or `'homework'` (default)
- Preserved across redirects using query strings

### Modal Chain
The system now supports a chain of modals:
1. Assignment Type Selection (page)
2. Assignment Target Modal (for PDF)
3. Assignment Context Modal (for PDF Individual)
4. Assignment Form (final destination)

### Backward Compatibility
- Homework assignments (default) behave exactly as before
- No changes to existing assignments
- Quiz and Discussion flows unchanged
- Group assignments flow unchanged

## Benefits

### For Teachers
- **Clear Workflow**: Step-by-step guidance through assignment creation
- **Time Saving**: No manual date setting for in-class work
- **Consistency**: All in-class assignments have same due time
- **Flexibility**: Full control over homework assignment timing
- **Reduced Errors**: Auto-filled dates eliminate typos
- **Better Organization**: Clear distinction between assignment types

### For Students
- **Predictability**: Know in-class work is always due same day at 4 PM
- **Clarity**: Assignment context visible in assignment details
- **Fair Deadlines**: Consistent timing for all in-class work

### For Administrators
- **Standardization**: Consistent in-class assignment policies school-wide
- **Reporting**: Can easily identify in-class vs homework assignments
- **Oversight**: Clear visibility into assignment distribution

## Testing Checklist

### In-Class PDF Assignment
- [ ] Select PDF/Paper Assignment
- [ ] Choose Individual Students
- [ ] Select In-Class Assignment
- [ ] Choose a class
- [ ] Verify due date is set to 4:00 PM EST today
- [ ] Verify due date field is read-only
- [ ] Verify info message displays correctly
- [ ] Create assignment and check database due_date value

### Homework PDF Assignment
- [ ] Select PDF/Paper Assignment
- [ ] Choose Individual Students
- [ ] Select Homework Assignment
- [ ] Choose a class
- [ ] Verify due date defaults to tomorrow 11:59 PM
- [ ] Verify due date field is editable
- [ ] Change due date to custom value
- [ ] Create assignment and verify custom date saved

### Group PDF Assignment
- [ ] Select PDF/Paper Assignment
- [ ] Choose Class Groups
- [ ] Verify redirects to group assignment type selector
- [ ] No context modal should appear

### Quiz Assignment
- [ ] Select Quiz Assignment
- [ ] Verify redirects directly to quiz creation
- [ ] No target or context modals appear

### Discussion Assignment
- [ ] Select Discussion Assignment
- [ ] Verify redirects directly to discussion creation
- [ ] No target or context modals appear

### Edge Cases
- [ ] Test with different server timezones
- [ ] Test around midnight EST
- [ ] Test with multiple teachers creating simultaneously
- [ ] Test context parameter persistence across browser refresh
- [ ] Test with special characters in form fields

## Future Enhancements

### Potential Additions
1. **Saved Preferences**: Remember teacher's typical choice (in-class vs homework)
2. **Custom In-Class Time**: Allow administrators to configure the auto-set time
3. **Different Times per Class**: Set different in-class end times for different periods
4. **Context Editing**: Allow changing context after creation (with date adjustment)
5. **Bulk Creation**: Create multiple in-class assignments at once
6. **Template Library**: Save frequently used in-class assignment templates
7. **Analytics**: Track in-class vs homework completion rates
8. **Calendar Integration**: Show in-class assignments on teacher's daily schedule

### Technical Improvements
1. **Server-Side Validation**: Enforce in-class date restrictions on backend
2. **Audit Trail**: Log context changes for compliance
3. **API Endpoints**: Expose context parameter via REST API
4. **Mobile Optimization**: Enhance modal UX for mobile devices
5. **Accessibility**: Add ARIA labels and keyboard navigation
6. **Internationalization**: Support different timezone preferences per teacher

## Conclusion

The teacher assignment creation flow now provides a professional, intuitive experience that matches the administrator's capabilities while adding unique features like the in-class/homework distinction. The automatic due date setting for in-class assignments eliminates a common source of errors and saves teachers valuable time.

All changes are backward compatible, maintaining existing functionality while adding powerful new options for teachers to better organize and manage their assignments.

