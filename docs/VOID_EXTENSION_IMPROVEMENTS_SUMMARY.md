# Void & Extension Functionality Improvements

## Summary
This document outlines the comprehensive improvements made to the Teacher Assignment Void and Extension functionality in the Clara Science Academy application.

## Issues Addressed

### 1. Void Assignment - Student Selection
**Problem:** The void assignment button automatically voided the assignment for ALL students without giving teachers the option to select specific students.

**Solution:** 
- Enhanced the void assignment modal to include student selection with checkboxes
- Added "Select All" and "Deselect All" buttons for convenience
- Teachers can now choose which students should have the assignment voided
- Updated the modal to dynamically load students from the class

### 2. Extension Functionality - Not Working
**Problem:** The extension button didn't work at all for teachers - it was calling endpoints but not saving any data to the database.

**Solution:**
- Implemented full extension grant functionality in `teacher_routes/assignments.py`
- Created logic to save extension data to the `AssignmentExtension` model
- Added support for updating existing extensions if a student already has one
- Extension data now includes:
  - Extended due date (date and time)
  - Reason for extension
  - Granted by (teacher ID)
  - Timestamp of when granted

### 3. Graded Count Display - Showing 0/0
**Problem:** Assignment cards displayed "0/0 Graded" even though students were enrolled and grades were entered.

**Solution:**
- Fixed the `assignments_and_grades` route in `teacherroutes.py`
- Grade data calculation was only happening for "grades" view mode
- Moved grade data calculation outside the view mode conditional
- Now correctly counts:
  - Total submissions (grades in database)
  - Graded count (grades with valid score data)
  - Average score across all graded submissions
- Fixed to exclude voided grades from counts

## Files Modified

### 1. `templates/teachers/assignments_and_grades.html`
**Changes:**
- **Void Modal Enhancement:**
  - Changed modal size from `modal-dialog` to `modal-dialog-lg modal-dialog-centered modal-dialog-scrollable`
  - Added hidden input for `class_id`
  - Added student selection container with loading spinner
  - Added "Select Students to Void For" section with Select All/Deselect All buttons
  - Updated warning text from "Mark it as 'Voided' for all students" to "Mark it as 'Voided' for selected students"

- **JavaScript Functions:**
  - Updated `openVoidModal()` to accept and store `classId` parameter
  - Added `loadStudentsForVoid(classId)` function to fetch students via API
  - Added `renderVoidStudentCheckboxes(students)` to display student checkboxes
  - Added `selectAllVoidStudents()` and `deselectAllVoidStudents()` helper functions
  - Updated void form submission to:
    - Check that at least one student is selected
    - Use the `/teacher/void-assignment/${assignmentId}` endpoint
    - Send student IDs via form data
    - Display success message with count of voided students

- **Button Updates:**
  - Updated individual assignment void button onclick: `openVoidModal({{ assignment.id }}, '{{ assignment.title }}', 'individual', {{ assignment.class_id }})`
  - Updated group assignment void button onclick: `openVoidModal({{ group_assignment.id }}, '{{ group_assignment.title }}', 'group', {{ group_assignment.class_id }})`

### 2. `teacher_routes/assignments.py`
**Changes:**
- **`grant_extensions()` Route (Line 348-429):**
  - Completely rewrote the function to actually save extensions
  - Added imports for `AssignmentExtension`, `Student`, `datetime`, and `jsonify`
  - Parses `extended_due_date` from datetime-local input format
  - Validates assignment authorization
  - Retrieves teacher from `get_teacher_or_admin()`
  - For each selected student:
    - Checks if extension already exists
    - Updates existing extension or creates new one
    - Stores: assignment_id, student_id, extended_due_date, reason, granted_by, is_active
  - Returns JSON response with success status and granted count
  - Includes error handling with rollback on failure

### 3. `teacherroutes.py`
**Changes:**
- **`assignments_and_grades()` Route (Line 1796-1826):**
  - Moved grade data calculation BEFORE the `if view_mode == 'grades':` conditional
  - Now calculates `grade_data` dictionary for ALL assignments regardless of view mode
  - Fixed query to exclude voided grades: `Grade.query.filter_by(assignment_id=assignment.id, is_voided=False).all()`
  - Properly handles both dict and JSON string formats for `grade_data`
  - Calculates:
    - `total_submissions`: Count of all non-voided grades
    - `graded_count`: Count of grades with valid score data
    - `average_score`: Average of all valid scores
  - Removed duplicate grade_data calculation that was inside the grades view conditional

## API Endpoints Used

### Existing Endpoints (Already Functional)
1. **GET `/teacher/class/<class_id>/students-for-extensions`** (Line 1169 in `teacherroutes.py`)
   - Returns list of students enrolled in a class
   - Used by both extension and void modals
   - Response format:
     ```json
     {
       "success": true,
       "students": [
         {
           "id": 1,
           "first_name": "John",
           "last_name": "Doe",
           "grade_level": 7,
           "email": "john.doe@example.com"
         }
       ]
     }
     ```

2. **POST `/teacher/void-assignment/<assignment_id>`** (Line 1586 in `teacherroutes.py`)
   - Accepts form data with `student_ids[]`, `assignment_type`, `void_reason`
   - Voids assignment for selected students
   - Returns JSON with success status and voided count

### Updated Endpoints
1. **POST `/teacher/grant-extensions`** (Line 348 in `teacher_routes/assignments.py`)
   - Now fully functional with database persistence
   - Accepts form data:
     - `assignment_id`: ID of the assignment
     - `student_ids[]`: Array of student IDs
     - `extended_due_date`: New due date in 'YYYY-MM-DDTHH:MM' format
     - `reason`: Optional reason for extension
   - Returns JSON:
     ```json
     {
       "success": true,
       "granted_count": 5
     }
     ```

## Database Schema

### AssignmentExtension Model (Already Exists)
Located in `models.py` at line 1305:

```python
class AssignmentExtension(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    extended_due_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    assignment = db.relationship('Assignment', backref='extensions')
    student = db.relationship('Student', backref='assignment_extensions')
    granter = db.relationship('TeacherStaff', backref='granted_extensions')
```

**Note:** The model already existed but wasn't being used. Now it's fully integrated.

## User Experience Improvements

### Void Assignment Flow
1. Teacher clicks "Void" button on an assignment card
2. Modal opens showing:
   - Assignment name
   - Warning about voiding consequences
   - List of all students in the class with checkboxes
   - "Select All" and "Deselect All" buttons
   - Optional reason text area
3. Teacher selects specific students to void for
4. Teacher clicks "Void Assignment"
5. Success message shows number of students affected
6. Page reloads to show updated assignment status

### Extension Grant Flow
1. Teacher clicks "Extend" button on an assignment card
2. Modal opens showing:
   - Assignment name and current due date
   - New due date picker (datetime-local input)
   - List of all students in the class with checkboxes
   - "Select All" and "Deselect All" buttons
   - Optional reason text area
3. Teacher selects new due date
4. Teacher selects students to grant extension to
5. Teacher clicks "Grant Extensions"
6. Success message shows number of students granted extensions
7. Page reloads with updated data

### Graded Count Display
- Assignment cards now accurately show:
  - "13/13 Graded" when all students have been graded
  - "8/13 Graded" when 8 out of 13 have been graded
  - "0/13 Graded" when no students have been graded
- Progress bar updates to reflect actual grading progress
- Average score displays correctly

## Testing Recommendations

### Manual Testing Steps

#### Test 1: Void Assignment with Student Selection
1. Navigate to Assignments & Grades page
2. Click "Void" button on any assignment
3. Verify modal shows list of students
4. Select 2-3 students (not all)
5. Enter a reason (e.g., "Student transferred to another class")
6. Click "Void Assignment"
7. Verify success message shows correct count
8. Check database that only selected students have `is_voided=True` in their grades

#### Test 2: Grant Extensions
1. Navigate to Assignments & Grades page
2. Click "Extend" button on any assignment
3. Verify modal shows list of students
4. Select a new due date (e.g., 2 days from now)
5. Select 3-4 students
6. Enter a reason (e.g., "Medical absence")
7. Click "Grant Extensions"
8. Verify success message
9. Check database for `assignment_extension` entries

#### Test 3: Graded Count Display
1. Create a new assignment with 10 students enrolled
2. Grade 5 students
3. Navigate to Assignments & Grades page
4. Verify card shows "5/10 Graded"
5. Verify progress bar is at 50%
6. Grade remaining 5 students
7. Refresh page
8. Verify card shows "10/10 Graded"
9. Verify progress bar is at 100%

## Security Considerations

1. **Authorization Checks:**
   - All routes verify teacher has access to the class
   - `is_authorized_for_class()` function used consistently
   - Directors and School Administrators have elevated permissions

2. **CSRF Protection:**
   - All forms include CSRF token
   - Forms validated on backend

3. **Input Validation:**
   - Student IDs validated and converted to integers
   - Date format validated before parsing
   - Assignment and student existence checked before operations

## Future Enhancements

1. **Extension History:**
   - Display extension history on assignment detail page
   - Show which students have extensions and their new due dates

2. **Void Reversal:**
   - Add ability to un-void assignments for specific students
   - Track void/unvoid history

3. **Bulk Operations:**
   - Add ability to void/extend multiple assignments at once
   - CSV export of extension and void data

4. **Notifications:**
   - Send email/notification to students when extension is granted
   - Notify students when assignment is voided

5. **Extension Display:**
   - Show extension icon on student's assignment list
   - Display extended due date prominently

## Conclusion

All three major issues have been resolved:
- ✅ Void assignment now supports student selection
- ✅ Extension functionality fully implemented and working
- ✅ Graded count displays accurately

The system is now more flexible, accurate, and user-friendly for teachers managing assignments and grades.

