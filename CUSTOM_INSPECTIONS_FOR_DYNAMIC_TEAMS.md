# Custom Inspections for Dynamic Teams

## Summary
Added support for custom inspection types for different team types, including Lunch Duty and Experiment Duty teams with their own inspection criteria and point systems.

## Features Added

### 1. **Team Type System**
- Added `team_type` field to `CleaningTeam` model
- Types: `cleaning`, `lunch_duty`, `experiment_duty`, `other`
- Allows different inspection criteria for each team type

### 2. **Inspection Type Tracking**
- Added `inspection_type` field to `CleaningInspection` model
- Automatically set based on the team's type when inspection is saved
- Allows filtering and reporting by inspection type

### 3. **Lunch Duty Inspections**
Custom criteria for lunch/serving duty:
- **Major Deductions (-10 points each):**
  - Food spilled on serving area
  - Not ready on time for lunch service
  - Trash not emptied and replaced
- **Moderate Deductions (-5 points each):**
  - Utensils or supplies missing
  - Serving counters not wiped down
  - Tables not cleared properly

### 4. **Experiment Duty Inspections**
Custom criteria for experiment setup duty:
- **Major Deductions (-10 points each):**
  - Required equipment missing or not set up
  - Safety equipment not properly placed
  - Experiment setup not ready on time
- **Moderate Deductions (-5 points each):**
  - Lab supplies or materials missing
  - Lab area not cleaned before experiment
  - Equipment not returned to storage

### 5. **Dynamic Inspection Modal**
- Inspection modal automatically shows relevant criteria based on team type
- Uses JavaScript to toggle between different inspection sections
- Shows/hides sections for: Computer, Cleaning, Lunch Duty, Experiment Duty

## Technical Implementation

### Backend Changes
**File**: `managementroutes.py`
- Updated `api_create_dynamic_team()` to set `team_type` when creating teams
- Updated `api_save_inspection()` to automatically determine and set `inspection_type` based on team's type

### Frontend Changes
**File**: `templates/management/student_jobs.html`
- Added lunch duty and experiment duty inspection sections to modal
- Updated `toggleInspectionSections()` to show appropriate section based on team type
- Updated `calculateScore()` and `submitInspection()` to handle new deduction types
- Updated team creation modal to include new team type options

### Database Schema Changes
**File**: `models.py`
- Added `team_type` field to `CleaningTeam` model
- Added `inspection_type` field to `CleaningInspection` model

## Migration Instructions

Run the migration script on the production server:

```bash
cd ~/project/src
python add_team_and_inspection_types.py
```

This will add:
1. `team_type` column to `cleaning_team` table (default: 'cleaning')
2. `inspection_type` column to `cleaning_inspection` table (default: 'cleaning')

## Usage

### Creating a Custom Team
1. Click "Create New Team" button
2. Enter team name and description
3. Select team type:
   - **Cleaning Team**: Traditional cleaning inspections
   - **Lunch Duty Team**: Lunch/serving duty inspections
   - **Experiment Duty Team**: Lab setup inspections
   - **Other**: Generic team type
4. Select team members
5. Click "Create Team"

### Conducting Inspections
1. Click "Record Inspection" on any team card
2. Select the team from the dropdown
3. Relevant inspection criteria automatically appear based on team type
4. Fill out the inspection form
5. Submit inspection
6. Score is calculated and saved automatically

## Point System

All team types use the same baseline:
- **Starting Points**: 100
- **Bonus Points Maximum**: +15 points
- **Score Threshold**: Below 60 points requires re-do

### Lunch Duty Point Deductions
- Major violations: -10 points each
- Moderate issues: -5 points each
- Bonus opportunities available

### Experiment Duty Point Deductions
- Major violations: -10 points each
- Moderate issues: -5 points each
- Bonus opportunities available

## Future Enhancements
- Add more team types as needed
- Customize deduction amounts per team type
- Add team-specific bonus categories
- Export inspection reports by type
- Dashboard showing performance by team type

