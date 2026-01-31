# Group Assignment Creation Page Enhancements

## Overview
This document describes the enhancements made to the Group Assignment Creation Page to bring it to feature parity with individual paper/PDF assignments.

## Date: 2025-01-30

## Changes Made

### 1. Database Model Updates

#### GroupAssignment Model (`models.py`)
Added the following fields to match the Assignment model:

- **`open_date`** (DateTime, nullable): When the assignment becomes available to students
  - NULL = available immediately
  
- **`close_date`** (DateTime, nullable): When the assignment closes for submissions
  - NULL = closes at due_date

These fields were already present in the Assignment model and are now available for GroupAssignment as well.

### 2. Template Updates

#### A. `teacher_create_group_assignment.html`
Enhanced the teacher's group assignment creation form with:

**New Fields Added:**
1. **Assignment Status** (Required)
   - Active / Inactive dropdown
   - Active assignments are visible to students

2. **Quarter** (Required)
   - Q1, Q2, Q3, Q4 selection
   - Auto-populated based on current date

3. **Open Date & Time** (Optional)
   - When assignment becomes available
   - Leave blank for immediate availability

4. **Close Date & Time** (Optional)
   - When assignment closes for submissions
   - Leave blank to close at due date

5. **Assignment Category** (Optional)
   - Homework, Tests, Quizzes, Projects, Classwork, Participation, Extra Credit
   - Used for weighted grading

6. **Category Weight** (Optional)
   - Percentage weight (0-100%)
   - Used in weighted grade calculations

**Advanced Grading Options Section:**
1. **Extra Credit**
   - Toggle to allow extra credit
   - Maximum extra credit points field
   - Students can earn points beyond total points

2. **Late Penalty**
   - Toggle to enable late penalties
   - Penalty per day (percentage)
   - Maximum penalty days (0 = unlimited)

3. **Grade Scale**
   - Preset options: Standard, Strict, Lenient
   - Defines letter grade conversion thresholds

**JavaScript Enhancements:**
- Auto-populate quarter based on current date
- Toggle visibility of extra credit options
- Toggle visibility of late penalty options
- Form validation

#### B. `create_group_pdf_assignment.html`
Enhanced the management/admin group PDF assignment creation form with the same fields as above:

**New Sections:**
1. **Assignment Settings** - Status and Category
2. **Due Date & Academic Period** - Reorganized with new date fields
3. **Advanced Grading Options** - Complete grading configuration

### 3. Route Handler Updates

#### A. `teacher_routes/groups.py` - `save_group_assignment()`
Updated to process new form fields:

```python
# New fields processed:
- open_date_str
- close_date_str
- quarter (now required from form)
- assignment_status
- assignment_category
- category_weight
- allow_extra_credit
- max_extra_credit_points
- late_penalty_enabled
- late_penalty_per_day
- late_penalty_max_days
- grade_scale_preset
```

**Grade Scale Presets:**
- **Standard**: A=90, B=80, C=70, D=60
- **Strict**: A=93, B=85, C=77, D=70
- **Lenient**: A=88, B=78, C=68, D=58

#### B. `management_routes/classes.py` - `admin_create_group_pdf_assignment()`
Updated to process the same new fields for management/admin users.

### 4. Database Migration

#### Migration Script: `maintenance_scripts/add_group_assignment_fields.py`
Created a migration script to add the new columns to existing databases:

**Columns Added:**
- `open_date` (TIMESTAMP/DATETIME)
- `close_date` (TIMESTAMP/DATETIME)

**Features:**
- Detects database type (PostgreSQL vs SQLite)
- Checks for existing columns before adding
- Provides detailed output of migration process
- Safe to run multiple times (idempotent)

#### Production Database Fix: `app.py`
Updated `run_production_database_fix()` to automatically add these columns in production:

```python
# Checks for and adds:
- open_date (TIMESTAMP)
- close_date (TIMESTAMP)
```

### 5. Feature Parity Achieved

Group assignments now have the same capabilities as individual assignments:

| Feature | Individual Assignment | Group Assignment |
|---------|----------------------|------------------|
| Assignment Status | ✓ | ✓ |
| Quarter Selection | ✓ | ✓ |
| Open Date & Time | ✓ | ✓ |
| Close Date & Time | ✓ | ✓ |
| Assignment Category | ✓ | ✓ |
| Category Weight | ✓ | ✓ |
| Extra Credit | ✓ | ✓ |
| Late Penalties | ✓ | ✓ |
| Grade Scale | ✓ | ✓ |

## User Roles Affected

These enhancements are available to:
- **Teachers** - Via teacher group assignment creation
- **School Administrators** - Via management group assignment creation
- **Directors** - Via management group assignment creation

## Usage Examples

### Example 1: Assignment with Open/Close Dates
```
Title: Group Research Project
Open Date: 2025-02-01 08:00 AM
Due Date: 2025-02-15 11:59 PM
Close Date: 2025-02-16 11:59 PM
```
- Assignment becomes available on Feb 1
- Due on Feb 15
- Accepts late submissions until Feb 16

### Example 2: Assignment with Late Penalty
```
Title: Weekly Discussion
Due Date: 2025-02-10 11:59 PM
Late Penalty: 10% per day
Maximum Days: 3 days
```
- 10% deducted for each day late
- No submissions accepted after 3 days

### Example 3: Assignment with Extra Credit
```
Title: Bonus Project
Total Points: 100
Allow Extra Credit: Yes
Max Extra Credit: 20 points
```
- Students can earn up to 120 points total

## Testing Recommendations

1. **Create a group assignment** with all new fields populated
2. **Verify database** contains correct values for open_date and close_date
3. **Test date validation** - ensure close_date > due_date > open_date
4. **Test advanced grading** options are saved correctly
5. **Test with different user roles** (Teacher, School Admin, Director)
6. **Verify backward compatibility** with existing group assignments

## Migration Instructions

### For Development/Local:
```bash
cd "c:\Users\admin\Documents\Clara_science_app"
python maintenance_scripts/add_group_assignment_fields.py
```

### For Production:
The `run_production_database_fix()` function in `app.py` will automatically add these columns on the next deployment.

## Notes

- All new fields are optional except Quarter and Assignment Status
- Existing group assignments will have NULL values for open_date and close_date
- NULL open_date means assignment is available immediately
- NULL close_date means assignment closes at due_date
- The migration is backward compatible and safe to run multiple times

## Future Enhancements

Potential future improvements:
1. Add time zone support for dates
2. Add recurring assignment templates
3. Add assignment scheduling/publishing
4. Add assignment analytics dashboard
5. Add bulk assignment operations

## Related Files

### Modified Files:
- `models.py` - Added open_date and close_date fields
- `teacher_routes/groups.py` - Updated save_group_assignment()
- `management_routes/classes.py` - Updated admin_create_group_pdf_assignment()
- `templates/teachers/teacher_create_group_assignment.html` - Enhanced UI
- `templates/shared/create_group_pdf_assignment.html` - Enhanced UI
- `app.py` - Updated production database fix

### New Files:
- `maintenance_scripts/add_group_assignment_fields.py` - Migration script
- `docs/GROUP_ASSIGNMENT_ENHANCEMENTS.md` - This documentation

## Support

For issues or questions about these enhancements, please contact the development team.
