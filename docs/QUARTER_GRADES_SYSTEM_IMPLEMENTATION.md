# Quarter Grades System Implementation

## Overview
Implemented a new **QuarterGrade table** that automatically calculates and stores quarter grades for each student in each class. The system refreshes grades every 3 hours and handles late assignments, voided assignments, and late enrollments properly.

## What Was Implemented

### 1. **New Database Table: `QuarterGrade`**

Located in `models.py` (lines 636-669):

```python
class QuarterGrade(db.Model):
    """
    Stores calculated quarter grades that refresh automatically.
    One record per student per class per quarter.
    """
    - student_id (FK to Student)
    - class_id (FK to Class)
    - school_year_id (FK to SchoolYear)
    - quarter ('Q1', 'Q2', 'Q3', 'Q4')
    - letter_grade ('A', 'B+', etc.)
    - percentage (float)
    - assignments_count (int)
    - last_calculated (timestamp)
    - created_at (timestamp)
```

**Key Features:**
- Unique constraint prevents duplicates
- Indexed for performance
- Tracks when last calculated for 3-hour refresh logic

### 2. **Quarter Grade Calculator Module**

Created `utils/quarter_grade_calculator.py` with:

#### `calculate_quarter_grade_for_student_class()`
- Calculates grade for specific student/class/quarter
- **Only includes assignments for that quarter**
- **Excludes voided assignments** (`is_voided == False`)
- **Handles late enrollments**: Checks if student enrolled after quarter ended
- Returns: `{letter_grade, percentage, assignments_count}`

#### `update_quarter_grade()`
- Updates or creates quarter grade record
- **3-Hour Refresh Rule**: Only recalculates if:
  - Grade doesn't exist yet
  - Last calculated > 3 hours ago
  - `force=True` parameter passed
- Handles enrollment edge cases

#### `update_all_quarter_grades_for_student()`
- Updates all quarters for all enrolled classes
- Used when generating report cards

#### `get_quarter_grades_for_report()`
- Retrieves formatted quarter grades for PDF generation
- Returns: `{'Q1': {'Math [4th]': {letter, percentage}, ...}, ...}`

### 3. **Updated PDF Generation**

In `managementroutes.py` (lines 892-910):
- Calls `update_all_quarter_grades_for_student()` when generating report card
- Respects 3-hour refresh interval
- Pulls grades from database instead of recalculating on every PDF generation
- Passes `calculated_grades_by_quarter` to template

### 4. **Migration Script**

Created `migrations_scripts/create_quarter_grade_table.py`:
- Creates `quarter_grade` table
- Adds indexes for performance
- PostgreSQL compatible

## How It Works

### When Generating a Report Card:

1. **User generates Q2 report card** for a student
2. System calls `update_all_quarter_grades_for_student()`
3. For each enrolled class:
   - Checks if Q1 grade exists and is < 3 hours old
     - If yes: Uses existing grade
     - If no: Recalculates from assignments
   - Checks if Q2 grade exists and is < 3 hours old
     - If yes: Uses existing grade
     - If no: Recalculates from assignments
   - Same for Q3, Q4
4. Pulls all quarter grades from `QuarterGrade` table
5. Displays in PDF:
   - Q1 column: Shows Q1 letter grade
   - Q2 column: Shows Q2 letter grade
   - Q3 column: Shows "—" (not ended yet)
   - Q4 column: Shows "—" (not ended yet)

### When Assignment Grades Change:

**Scenario**: Teacher updates a Q1 assignment grade 2 months after Q1 ended

1. Grade is updated in database
2. Next time someone generates a report card (after 3 hours):
   - System recalculates Q1 grade
   - Updates `QuarterGrade` record
   - PDF shows updated grade
3. If < 3 hours since last calculation:
   - Uses cached grade from database
   - Won't reflect change until 3-hour window passes

### Handling Edge Cases:

**Late Enrollment:**
- Student enrolled on 11/15, but Q1 ended on 11/1
- System checks: `enrollment.enrolled_at >= quarter.end_date`
- Result: No Q1 grade calculated (student wasn't enrolled)

**Voided Assignments:**
- Assignment is voided after quarter ends
- Filter: `Grade.is_voided == False`
- Result: Voided assignment excluded from calculation

**Quarter-Specific Assignments:**
- Filter: `Assignment.quarter == 'Q1'`
- Result: Only Q1 assignments affect Q1 grade

## Deployment Steps

### 1. Deploy Code
```bash
git add .
git commit -m "Implement QuarterGrade system with 3-hour refresh"
git push
```

### 2. Run Migration on Render
```bash
# SSH into Render or use Render Shell
python migrations_scripts/create_quarter_grade_table.py
```

### 3. Initial Population (Optional)
To populate existing grades, you can force recalculation:
```python
from utils.quarter_grade_calculator import update_all_quarter_grades_for_student
from models import Student, SchoolYear

school_year = SchoolYear.query.filter_by(is_active=True).first()
students = Student.query.all()

for student in students:
    update_all_quarter_grades_for_student(
        student.id, 
        school_year.id, 
        force=True  # Forces recalculation
    )
```

## Benefits

1. ✅ **Performance**: Grades calculated once every 3 hours instead of on every view
2. ✅ **Accuracy**: Reflects late assignments and grade changes
3. ✅ **Proper Handling**: Excludes voided assignments, handles late enrollments
4. ✅ **Quarter-Specific**: Only assignments for that quarter affect the grade
5. ✅ **Consistent**: Same grades shown to students and on PDFs
6. ✅ **Scalable**: Database-backed with indexes for performance

## Files Modified

- `models.py` - Added QuarterGrade model
- `app.py` - Added imports
- `managementroutes.py` - Updated PDF generation to use QuarterGrade
- `utils/quarter_grade_calculator.py` - NEW calculator module
- `migrations_scripts/create_quarter_grade_table.py` - NEW migration script
- `QUARTER_GRADES_SYSTEM_IMPLEMENTATION.md` - This documentation

## Testing

After deployment:
1. Generate a report card for a student with grades in multiple quarters
2. Verify Q1, Q2, Q3, Q4 columns show correct letter grades (not all "—")
3. Update an assignment grade
4. Wait 3+ hours or force recalculate
5. Generate report card again - should show updated grade

## Future Enhancements

- Add background job to refresh all quarter grades every 3 hours automatically
- Add admin interface to manually trigger grade refresh
- Add grade history tracking to see when grades changed
- Add notification when quarter grades are finalized

