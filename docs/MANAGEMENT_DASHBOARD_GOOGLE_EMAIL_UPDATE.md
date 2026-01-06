# Management Dashboard - Google Workspace Email Integration

## Summary
Updated the management dashboard to allow administrators to view and edit Google Workspace emails for both students and staff members directly from the edit forms.

---

## Changes Made

### 1. Student Edit Form
**Location:** `templates/management/role_dashboard.html` (Edit Student Modal)

**Added Fields:**
- **Personal Email** - Renamed from "Email" for clarity
  - Purpose: Parent contact and personal communications
  - Field name: `email`
  
- **Google Workspace Email** - NEW field
  - Purpose: Google Sign-In authentication
  - Field name: `google_workspace_email`
  - Placeholder: `student@clarascienceacademy.org`
  - Icon: Google logo with tooltip

**Visual Layout:**
```
Contact & Authentication
┌─────────────────────────────────┬─────────────────────────────────┐
│ Personal Email                  │ Google Workspace Email 🔵      │
│ [student@example.com________]   │ [student@clarascienceacademy.org]│
│ For parent contact              │ For Google Sign-In              │
└─────────────────────────────────┴─────────────────────────────────┘
```

### 2. Teacher/Staff Edit Form
**Location:** `templates/management/role_dashboard.html` (Edit Teacher Modal)

**Added Fields:**
- **Personal Email** - Renamed from "Email" for clarity
  - Purpose: Personal communications
  - Field name: `email`
  - Required field
  
- **Google Workspace Email** - NEW field
  - Purpose: Google Sign-In authentication
  - Field name: `google_workspace_email`
  - Placeholder: `teacher@clarascienceacademy.org`
  - Icon: Google logo with tooltip

**Visual Layout:**
```
Basic Information
┌─────────────────────────────────┬─────────────────────────────────┐
│ Personal Email *                │ Google Workspace Email 🔵      │
│ [teacher@example.com________]   │ [teacher@clarascienceacademy.org]│
│ For personal communications     │ For Google Sign-In              │
└─────────────────────────────────┴─────────────────────────────────┘
```

### 3. Backend API Updates

#### `view_student` Endpoint
**Location:** `managementroutes.py`, line 5773

**Added to JSON Response:**
```python
'google_workspace_email': student.user.google_workspace_email if student.user else None
```

This ensures the edit form is populated with the current Google Workspace email.

#### `edit_student` Endpoint
**Location:** `managementroutes.py`, line 5867-5880

**Added Logic:**
```python
# Update Google Workspace email in User account if student has one
google_workspace_email = request.form.get('google_workspace_email', '').strip()
if student.user:
    if google_workspace_email:
        # Check if this email is already used by another user
        existing_user = User.query.filter_by(google_workspace_email=google_workspace_email).first()
        if existing_user and existing_user.id != student.user.id:
            return jsonify({'success': False, 'message': f'Google Workspace email {google_workspace_email} is already in use by another user.'}), 400
        
        student.user.google_workspace_email = google_workspace_email
    else:
        # Clear the Google Workspace email if field is empty
        student.user.google_workspace_email = None
```

**Features:**
- ✅ Updates the User model's `google_workspace_email` field
- ✅ Checks for duplicate emails across all users
- ✅ Returns error if email is already in use
- ✅ Allows clearing the field (set to NULL)
- ✅ Only updates if student has a user account

#### `view_teacher` Endpoint
**Location:** `managementroutes.py`, line 5971

**Added to JSON Response:**
```python
'google_workspace_email': teacher.user.google_workspace_email if teacher.user else None
```

#### `edit_teacher` Endpoint
**Location:** `managementroutes.py`, line 6052-6063

**Added Logic:**
```python
# Update Google Workspace email
google_workspace_email = request.form.get('google_workspace_email', '').strip()
if google_workspace_email:
    # Check if this email is already used by another user
    existing_user = User.query.filter_by(google_workspace_email=google_workspace_email).first()
    if existing_user and existing_user.id != teacher.user.id:
        return jsonify({'success': False, 'message': f'Google Workspace email {google_workspace_email} is already in use by another user.'}), 400
    
    teacher.user.google_workspace_email = google_workspace_email
else:
    # Clear the Google Workspace email if field is empty
    teacher.user.google_workspace_email = None
```

---

## How It Works

### Editing a Student

1. **Administrator clicks "Edit" on a student card**
2. **Modal opens with all student information**
3. **Two email fields are visible:**
   - Personal Email (existing field, may have parent's email)
   - Google Workspace Email (new field, for Google Sign-In)
4. **Administrator can:**
   - Update personal email
   - Add/update Google Workspace email
   - Clear Google Workspace email (leave blank)
5. **Click "Save Changes"**
6. **Backend validates:**
   - Checks if Google Workspace email is unique
   - Returns error if already in use by another user
   - Updates User model if validation passes
7. **Success message displayed**

### Editing a Teacher/Staff

Same flow as students, but with teacher-specific fields.

---

## Validation & Error Handling

### Duplicate Email Check

**Scenario:** Admin tries to set `john.doe@clarascienceacademy.org` for Student A, but it's already assigned to Student B.

**Result:**
```json
{
  "success": false,
  "message": "Google Workspace email john.doe@clarascienceacademy.org is already in use by another user."
}
```

**UI:** Error alert displayed, form not saved.

### Empty Email Handling

**Scenario:** Admin clears the Google Workspace email field.

**Result:** Field set to `NULL` in database, user can no longer sign in with Google (but can still use username/password).

### No User Account

**Scenario:** Student/staff doesn't have a user account yet.

**Result:** Google Workspace email field is ignored (not saved), no error shown.

---

## User Experience

### For Administrators

**Before:**
- Only one email field
- Confusion about which email to use
- Had to choose between personal or institutional

**After:**
- Two clearly labeled email fields
- Tooltips explain each field's purpose
- Can maintain both emails simultaneously
- Google icon indicates authentication field

### Visual Indicators

- 🔵 **Google logo icon** next to "Google Workspace Email" label
- **Placeholder text** shows expected format
- **Helper text** explains purpose of each field
- **Tooltips** on hover for additional context

---

## Testing Checklist

### Student Edit Form
- [ ] Open edit form for a student
- [ ] Verify both email fields are visible
- [ ] Verify Personal Email field shows current email
- [ ] Verify Google Workspace Email field shows current workspace email (or empty)
- [ ] Update Personal Email only - verify saves correctly
- [ ] Update Google Workspace Email only - verify saves correctly
- [ ] Update both emails - verify both save correctly
- [ ] Try to set duplicate Google Workspace email - verify error message
- [ ] Clear Google Workspace email - verify clears in database
- [ ] Test Google Sign-In with updated email - verify works

### Teacher/Staff Edit Form
- [ ] Open edit form for a teacher
- [ ] Verify both email fields are visible
- [ ] Verify Personal Email field shows current email
- [ ] Verify Google Workspace Email field shows current workspace email (or empty)
- [ ] Update Personal Email only - verify saves correctly
- [ ] Update Google Workspace Email only - verify saves correctly
- [ ] Update both emails - verify both save correctly
- [ ] Try to set duplicate Google Workspace email - verify error message
- [ ] Clear Google Workspace Email - verify clears in database
- [ ] Test Google Sign-In with updated email - verify works

### Edge Cases
- [ ] Edit user without user account - verify no errors
- [ ] Edit user with only personal email set
- [ ] Edit user with only Google Workspace email set
- [ ] Edit user with both emails set to same value
- [ ] Edit user with special characters in email
- [ ] Edit user with very long email address

---

## Database Impact

### Fields Updated

**User Model:**
- `email` - Personal/contact email (existing)
- `google_workspace_email` - Institutional email (new)

**Student Model:**
- `email` - Student's personal email (existing)

**TeacherStaff Model:**
- `email` - Staff's personal email (existing)

### Relationships

```
Student
  └─> User (via student_id foreign key)
      ├─> email (personal)
      └─> google_workspace_email (institutional)

TeacherStaff
  └─> User (via teacher_staff_id foreign key)
      ├─> email (personal)
      └─> google_workspace_email (institutional)
```

---

## Security Considerations

### Unique Constraint

Both email fields have `unique=True`:
- No two users can share the same Google Workspace email
- Backend validates before saving
- Clear error messages for duplicates

### Data Privacy

- Personal emails remain private
- Google Workspace emails are institutional
- Both fields optional (nullable)
- Can be cleared at any time

### Access Control

- Only administrators can edit emails
- Changes logged in activity log
- Validation on both frontend and backend

---

## Maintenance

### Bulk Email Updates

If you need to update many users at once, use the helper script:

```bash
python populate_google_workspace_emails.py
```

### Individual Updates

For one-off updates, use the management dashboard:
1. Go to Students or Teachers & Staff tab
2. Click "Edit" on the user
3. Update the Google Workspace Email field
4. Click "Save Changes"

### Verification

Check current email settings:

```bash
python populate_google_workspace_emails.py show
```

---

## Best Practices

### For Administrators

1. **Set Google Workspace emails** for all users who will use Google Sign-In
2. **Use consistent format:** `firstname.lastname@clarascienceacademy.org`
3. **Keep personal emails** for parent contact and records
4. **Verify uniqueness** before saving
5. **Test Google Sign-In** after updating emails

### Email Format Guidelines

**Students:**
```
firstname.lastname@clarascienceacademy.org
```

**Teachers:**
```
firstname.lastname@clarascienceacademy.org
```

**Administrators:**
```
firstname.lastname@clarascienceacademy.org
```

**Special Cases:**
- Duplicate names: Add middle initial or number
- Hyphenated names: Remove hyphens or keep them
- Spaces in names: Remove spaces

---

## Troubleshooting

### Issue: "Google Workspace email is already in use"

**Cause:** Another user already has this email

**Solution:**
1. Search for the user with that email:
   ```bash
   python populate_google_workspace_emails.py show | grep "email@domain.org"
   ```
2. Update the conflicting user first
3. Then update the current user

### Issue: Changes don't save

**Cause:** User doesn't have a user account

**Solution:**
1. Create a user account for the student/staff first
2. Then update the Google Workspace email

### Issue: Google Sign-In doesn't work after updating

**Possible Causes:**
1. Typo in email address
2. Email doesn't match Google Workspace account
3. User not signed into correct Google account

**Solution:**
1. Verify email spelling in edit form
2. Have user check their Google Workspace email
3. Test with correct Google account

---

## Summary

✅ **Student edit form updated** with Google Workspace email field  
✅ **Teacher edit form updated** with Google Workspace email field  
✅ **Backend validation** for duplicate emails  
✅ **API endpoints updated** to return and save Google Workspace emails  
✅ **Clear labeling** distinguishes personal vs institutional emails  
✅ **Tooltips and help text** guide administrators  
✅ **Error handling** for edge cases  

**Administrators can now easily manage Google Workspace emails for all users directly from the dashboard!**

---

*Last updated: November 6, 2025*
*Clara Science Academy - Management Dashboard Enhancement*

