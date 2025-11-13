# Assignment Redo System Documentation

## Overview
The Assignment Redo System allows teachers, School Administrators, and Directors to grant students permission to redo PDF/Paper assignments with flexible deadlines and automatic grade calculation.

## Features

### 🎯 Core Functionality
- **Grant Redo Permissions**: Allow specific students to redo assignments
- **Flexible Deadlines**: Set custom redo deadlines per student
- **Smart Grade Calculation**: 
  - Keeps the higher of the two grades
  - Applies 10% penalty if redo is submitted late
- **Track Attempts**: View original vs redo submissions
- **Notifications**: Students receive notifications when granted redo opportunities

### 📊 Database Model
**Table**: `assignment_redo`

**Fields**:
- `id`: Primary key
- `assignment_id`: Foreign key to assignment
- `student_id`: Foreign key to student
- `granted_by`: Teacher/admin who granted the redo
- `granted_at`: Timestamp when redo was granted
- `redo_deadline`: New deadline for redo submission
- `reason`: Optional reason for granting redo
- `is_used`: Has student submitted the redo?
- `redo_submission_id`: Links to the redo submission
- `redo_submitted_at`: When redo was submitted
- `original_grade`: Grade before redo
- `redo_grade`: Grade from redo attempt
- `final_grade`: Final calculated grade (higher grade, with penalty if late)
- `was_redo_late`: Was the redo submitted after the deadline?

## API Endpoints

### 1. Grant Redo Permission
**Route**: `POST /management/grant-redo/<assignment_id>`
**Access**: Directors, School Administrators
**Parameters**:
- `student_ids[]`: Array of student IDs
- `redo_deadline`: New deadline (YYYY-MM-DD format)
- `reason`: Optional reason for granting redo

**Response**:
```json
{
  "success": true,
  "message": "Redo permission granted to 5 student(s)."
}
```

### 2. Revoke Redo Permission
**Route**: `POST /management/revoke-redo/<redo_id>`
**Access**: Directors, School Administrators
**Note**: Cannot revoke if student has already used the redo

**Response**:
```json
{
  "success": true,
  "message": "Redo permission revoked successfully."
}
```

### 3. View Assignment Redos
**Route**: `GET /management/assignment/<assignment_id>/redos`
**Access**: Directors, School Administrators, Teachers
**Returns**: List of all redo permissions for an assignment

**Response**:
```json
{
  "success": true,
  "redos": [
    {
      "id": 1,
      "student_name": "John Doe",
      "student_id": 123,
      "granted_at": "11/13/2025 02:30 PM",
      "redo_deadline": "11/20/2025",
      "reason": "Excused absence",
      "is_used": false,
      "redo_submitted_at": null,
      "original_grade": 65.0,
      "redo_grade": null,
      "final_grade": null,
      "was_redo_late": false
    }
  ]
}
```

## Grade Calculation Logic

### Standard Redo (Submitted on time)
```
final_grade = max(original_grade, redo_grade)
```

### Late Redo (Submitted after deadline)
```
capped_redo_grade = redo_grade - 10
final_grade = max(original_grade, capped_redo_grade)
```

**Example 1**: 
- Original grade: 65%
- Redo grade: 85% (on time)
- Final grade: **85%**

**Example 2**:
- Original grade: 65%
- Redo grade: 90% (late)
- Capped redo grade: 80% (90% - 10%)
- Final grade: **80%**

**Example 3**:
- Original grade: 75%
- Redo grade: 70% (on time)
- Final grade: **75%** (original is higher)

## Usage Flow

### For Teachers/Administrators:
1. Navigate to Assignments & Grades
2. Select an assignment to grade
3. Click "Grant Redo" button next to student names
4. Select students, set redo deadline, and provide optional reason
5. Students receive notifications
6. Monitor redo submissions in grading interface

### For Students:
1. Receive notification about redo opportunity
2. See redo assignments in "Redo Opportunities" section on dashboard
3. Submit redo before new deadline
4. View final calculated grade

## Restrictions

- **Assignment Type**: Only available for PDF/Paper assignments
- **Revocation**: Cannot revoke after student has submitted redo
- **Access**: Only Teachers, School Administrators, and Directors can grant redos

## Installation

1. Run the migration script:
```bash
python add_assignment_redo_table.py
```

2. Restart the application to load the new model

## Future Enhancements (Optional)
- Allow teachers to set maximum redo attempts per assignment
- Add bulk redo granting for entire classes
- Export redo statistics and reports
- Email notifications in addition to in-app notifications
- Extend to Quiz and Discussion assignments (when needed)

## Technical Notes

- **Model Location**: `models.py` (Line 676-711)
- **Routes Location**: `managementroutes.py` (Line 5990-6176)
- **Database**: Uses SQLite/PostgreSQL depending on environment
- **Notifications**: Integrated with existing notification system

