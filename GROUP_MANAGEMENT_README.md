# Group Management System

This document describes the new group management functionality added to the Clara Science Academy application for teachers.

## Overview

The group management system allows teachers to:
- Create and manage student groups within their classes
- Create group assignments for collaborative work
- Assign students to groups with optional group leaders
- Grade group assignments with individual student scores
- Track group submissions and progress

## New Features

### 1. Student Groups
- **Create Groups**: Teachers can create named groups with descriptions and optional size limits
- **Manage Members**: Add/remove students from groups and designate group leaders
- **Group Overview**: View all groups in a class with member counts and details

### 2. Group Assignments
- **Create Group Assignments**: Design assignments specifically for group work
- **Flexible Collaboration**: Choose between group-only, individual-only, or both
- **Size Controls**: Set minimum and maximum group sizes
- **File Attachments**: Upload assignment instructions, rubrics, or reference materials

### 3. Group Grading
- **Individual Scoring**: Grade each student individually within their group
- **Comments**: Add personalized feedback for each student
- **Submission Tracking**: Monitor which groups have submitted work

## Database Schema

### New Tables

#### `student_group`
- `id`: Primary key
- `name`: Group name
- `description`: Optional group description
- `class_id`: Foreign key to class
- `created_by`: Foreign key to teacher
- `max_students`: Optional group size limit
- `is_active`: Soft delete flag
- `created_at`: Creation timestamp

#### `student_group_member`
- `id`: Primary key
- `group_id`: Foreign key to student_group
- `student_id`: Foreign key to student
- `joined_at`: When student joined group
- `is_leader`: Boolean for group leader designation

#### `group_assignment`
- `id`: Primary key
- `title`: Assignment title
- `description`: Assignment description
- `class_id`: Foreign key to class
- `due_date`: Assignment due date
- `quarter`: Academic quarter
- `semester`: Academic semester (optional)
- `academic_period_id`: Foreign key to academic period
- `school_year_id`: Foreign key to school year
- `group_size_min`: Minimum group size
- `group_size_max`: Maximum group size
- `allow_individual`: Allow individual submissions
- `collaboration_type`: 'group', 'individual', or 'both'
- File attachment fields for assignment materials

#### `group_submission`
- `id`: Primary key
- `group_assignment_id`: Foreign key to group_assignment
- `group_id`: Foreign key to student_group (nullable for individual)
- `submitted_by`: Foreign key to student (who submitted)
- `submission_text`: Text submission
- `submitted_at`: Submission timestamp
- `is_late`: Late submission flag
- File attachment fields for submission materials

#### `group_grade`
- `id`: Primary key
- `group_assignment_id`: Foreign key to group_assignment
- `group_id`: Foreign key to student_group (nullable for individual)
- `student_id`: Foreign key to student
- `grade_data`: JSON string with grade details
- `graded_by`: Foreign key to teacher
- `graded_at`: Grading timestamp
- `comments`: Teacher comments

## User Interface

### Teacher Navigation
The class management interface now includes:
- **Manage Groups** button in class view
- **Group Assignments** button in class view
- Dedicated group management pages
- Group assignment creation and grading interfaces

### Key Pages

1. **Class Groups** (`/class/<id>/groups`)
   - Overview of all groups in a class
   - Create new groups
   - Manage existing groups

2. **Create Group** (`/class/<id>/groups/create`)
   - Form to create new groups
   - Set group name, description, and size limits

3. **Manage Group** (`/group/<id>/manage`)
   - Add/remove students from groups
   - Set group leaders
   - View group membership

4. **Group Assignments** (`/class/<id>/group-assignments`)
   - List all group assignments for a class
   - Create new group assignments

5. **Create Group Assignment** (`/class/<id>/group-assignment/create`)
   - Comprehensive form for creating group assignments
   - Set collaboration type, group sizes, due dates
   - Upload assignment materials

6. **View Group Assignment** (`/group-assignment/<id>/view`)
   - Assignment details and submissions
   - Group overview and statistics

7. **Grade Group Assignment** (`/group-assignment/<id>/grade`)
   - Grade individual students within groups
   - Add comments and feedback

## Installation & Setup

### 1. Database Migration
Run the migration script to create the new tables:

```bash
python create_group_tables_migration.py
```

### 2. Verify Installation
1. Log in as a teacher
2. Navigate to one of your classes
3. Look for the new "Manage Groups" and "Group Assignments" buttons
4. Test creating a group and group assignment

## Usage Guide

### Creating Groups
1. Go to your class page
2. Click "Manage Groups"
3. Click "Create Group"
4. Enter group name, description, and optional size limit
5. Save the group

### Managing Group Members
1. From the groups page, click "Manage Group" on any group
2. Add students from the available student list
3. Optionally set a group leader
4. Remove students if needed

### Creating Group Assignments
1. Go to your class page
2. Click "Group Assignments"
3. Click "Create Group Assignment"
4. Fill in assignment details:
   - Title and description
   - Due date and academic period
   - Group size requirements
   - Collaboration type (group/individual/both)
   - Upload any assignment materials
5. Save the assignment

### Grading Group Assignments
1. From the group assignments page, click "Grade Assignment"
2. Enter scores (0-100) for each student
3. Add comments for individual students
4. Save all grades

## Best Practices

### Group Management
- Create groups with clear, descriptive names
- Set appropriate group size limits based on assignment requirements
- Designate group leaders for better organization
- Regularly review and update group memberships

### Group Assignments
- Provide clear instructions for group work
- Set realistic due dates considering group coordination time
- Use file attachments for rubrics and reference materials
- Consider allowing individual submissions as a fallback

### Grading
- Grade students individually within groups to ensure fairness
- Provide specific feedback in comments
- Consider group dynamics when assigning individual scores
- Use the group leader designation to help with organization

## Technical Notes

### Security
- All routes are protected with `@login_required` and `@teacher_required`
- Teachers can only access groups and assignments for their own classes
- Directors have access to all classes

### Performance
- Database queries are optimized with proper relationships
- Group membership is cached in templates for efficiency
- File uploads are handled securely with proper validation

### Error Handling
- Comprehensive form validation
- User-friendly error messages
- Graceful handling of missing data

## Future Enhancements

Potential future improvements could include:
- Group chat functionality
- Peer evaluation features
- Group progress tracking
- Automated group formation based on criteria
- Integration with existing messaging system
- Group assignment templates
- Advanced reporting and analytics

## Support

For technical support or questions about the group management system, please contact the development team or refer to the main application documentation.
