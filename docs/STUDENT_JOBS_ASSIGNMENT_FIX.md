# Student Jobs Assignment Description Fix

## Summary
Added support for detailed job assignments for each cleaning team member by adding an `assignment_description` field to the `CleaningTeamMember` model.

## Changes Made

### 1. Database Model Update (`models.py`)
- Added `assignment_description` field to `CleaningTeamMember` model
- Field type: `db.Column(db.Text, nullable=True)`
- Allows storing specific job details for each team member

### 2. Backend Routes Update (`managementroutes.py`)
- Updated `/management/api/team-members/<team_id>` to include assignment descriptions
- Updated `/management/student-jobs` route to safely handle assignment descriptions
- Added error handling for cases where column doesn't exist yet

### 3. Template Update (`templates/management/student_jobs.html`)
- Updated team member display to show assignment descriptions
- Falls back to default text if no assignment is set

### 4. Migration Script
- Created `add_assignment_description_to_cleaning_teams.py`
- Adds the new column to existing database

## Migration Instructions

### For Production (Render):
```bash
# SSH into Render shell
render_shell_commands.py

# Run the migration
cd /opt/render/project
python add_assignment_description_to_cleaning_teams.py
```

### For Local Development:
```bash
python add_assignment_description_to_cleaning_teams.py
```

## What This Enables

1. **Detailed Job Assignments**: Each team member can now have a specific job description (e.g., "Sweep all 4 classrooms and main hallway", "Clean and replenish girls bathroom supplies")

2. **Flexible Team Management**: Schools can customize job assignments for each team member

3. **Better Organization**: Clear visibility of what each team member is responsible for

## Usage

When adding members to a team, the system will:
- Accept an optional assignment description
- Display the description in the team member cards
- Allow updating assignment descriptions for existing members

## Notes

- The migration script is idempotent (safe to run multiple times)
- Existing team members will have an empty assignment description until updated
- The column is nullable, so it's safe to add without affecting existing functionality

