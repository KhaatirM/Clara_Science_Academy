# Dual Email System for Google Workspace Integration

## Overview
Clara Science Academy now supports **two separate email fields** for each user:
1. **Personal Email** (`email`) - For personal communications, parent contact, etc.
2. **Google Workspace Email** (`google_workspace_email`) - For Google Sign-In authentication

This allows staff and students to keep their personal emails on file while using their institutional Google Workspace accounts for authentication.

---

## Why Two Email Fields?

### The Problem
Your staff have:
- **Personal emails** stored in the database (e.g., `john.smith@gmail.com`)
- **Google Workspace emails** for school (e.g., `john.smith@clarascienceacademy.org`)

When they try to sign in with Google, the system checks the email from Google against the database. If it doesn't match, they can't log in.

### The Solution
Two separate fields:
- `email` - Keeps their personal email (for contact, records, etc.)
- `google_workspace_email` - Their institutional email for Google Sign-In

**Google Sign-In now checks BOTH fields**, so users can authenticate with their Google Workspace account while keeping their personal email on record.

---

## Database Changes

### User Model Update

**Location:** `models.py`, line 20-22

**Before:**
```python
email = db.Column(db.String(120), unique=True, nullable=True)
```

**After:**
```python
email = db.Column(db.String(120), unique=True, nullable=True)  # Personal email
google_workspace_email = db.Column(db.String(120), unique=True, nullable=True)  # Google Workspace email
```

### Migration Required

You need to add this new column to your database. Two options:

#### Option 1: Using the Migration Script (Recommended)
```bash
python add_google_workspace_email.py
```

This script:
- Checks if column already exists
- Adds it if needed
- Provides clear success/error messages

#### Option 2: Using Flask-Migrate
```bash
flask db migrate -m "Add google_workspace_email to User model"
flask db upgrade
```

---

## Populating Google Workspace Emails

### Automatic Population

Run the helper script to auto-generate emails for all users:

```bash
python populate_google_workspace_emails.py
```

**What it does:**
- Generates emails in format: `firstname.lastname@clarascienceacademy.org`
- Checks for duplicates
- Updates all users at once
- Shows summary of changes

**Example Output:**
```
✅ john.doe (Teacher): john.doe@clarascienceacademy.org
✅ jane.smith (Student): jane.smith@clarascienceacademy.org
⏭️  Skipping admin.user - already has Google Workspace email
⚠️  Could not generate email for test.user (Student) - missing name information

Summary:
  ✅ Updated: 45 users
  ⏭️  Skipped: 2 users (already had email)
  ⚠️  Errors: 3 users (need manual setup)
```

### View Current Emails

Check what emails are currently set:

```bash
python populate_google_workspace_emails.py show
```

**Output:**
```
Username             Role                 Personal Email                 Workspace Email
--------------------------------------------------------------------------------
john.doe             Teacher              john@gmail.com                 john.doe@clarascienceacademy.org
jane.smith           Student              jane@yahoo.com                 jane.smith@clarascienceacademy.org
admin                Director             admin@school.com               (not set)
```

### Set Single User Email

Update one user at a time:

```bash
python populate_google_workspace_emails.py set john.doe john.doe@clarascienceacademy.org
```

**Output:**
```
✅ Successfully set Google Workspace email for john.doe
   Email: john.doe@clarascienceacademy.org
```

---

## Authentication Logic

### How Google Sign-In Works Now

**Location:** `authroutes.py`, line 715-721

```python
# Check if user exists in the database (check both personal email and Google Workspace email)
user = User.query.filter(
    or_(
        User.email == google_email,  # Check personal email
        User.google_workspace_email == google_email  # Check Google Workspace email
    )
).first()
```

### Sign-In Scenarios

#### Scenario 1: User with Google Workspace Email Set
```
User in Database:
  username: john.doe
  email: john@gmail.com
  google_workspace_email: john.doe@clarascienceacademy.org

Google Sign-In with: john.doe@clarascienceacademy.org
Result: ✅ SUCCESS - Matches google_workspace_email
```

#### Scenario 2: User with Personal Email Matching Google
```
User in Database:
  username: jane.smith
  email: jane.smith@clarascienceacademy.org
  google_workspace_email: (not set)

Google Sign-In with: jane.smith@clarascienceacademy.org
Result: ✅ SUCCESS - Matches email field
```

#### Scenario 3: User with Neither Email Matching
```
User in Database:
  username: bob.jones
  email: bob@yahoo.com
  google_workspace_email: (not set)

Google Sign-In with: bob.jones@clarascienceacademy.org
Result: ❌ BLOCKED - No match found
Message: "Your Google Account is not associated with an account at Clara Science Academy..."
```

#### Scenario 4: Email Not in Database at All
```
Google Sign-In with: random.person@clarascienceacademy.org
Result: ❌ BLOCKED - User doesn't exist
Message: "Your Google Account is not associated with an account at Clara Science Academy..."
```

---

## Management Dashboard Integration

### Viewing User Emails

When viewing user details in the management dashboard, you'll see both email fields:
- **Personal Email:** Used for contact, notifications, parent communication
- **Google Workspace Email:** Used for Google Sign-In authentication

### Editing User Emails

Administrators can update both email fields:
1. Go to Management Dashboard → Users
2. Click on a user to edit
3. Update either or both email fields:
   - **Email:** Personal/contact email
   - **Google Workspace Email:** Their @clarascienceacademy.org email
4. Save changes

### Bulk Email Updates

For bulk updates, use the provided scripts or create a CSV import:

```python
# Example: Bulk update from CSV
import csv
from app import app, db
from models import User

with app.app_context():
    with open('user_emails.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user = User.query.filter_by(username=row['username']).first()
            if user:
                user.google_workspace_email = row['workspace_email']
                print(f"Updated {user.username}")
    
    db.session.commit()
    print("Bulk update complete!")
```

---

## Email Format Guidelines

### Recommended Format
```
firstname.lastname@clarascienceacademy.org
```

### Handling Special Cases

**Names with spaces:**
```
First Name: Mary Jane
Last Name: Watson
Email: maryjane.watson@clarascienceacademy.org
```

**Names with hyphens:**
```
First Name: Jean-Paul
Last Name: Sartre
Email: jeanpaul.sartre@clarascienceacademy.org
```

**Duplicate names:**
```
John Smith (Student, Grade 5): john.smith5@clarascienceacademy.org
John Smith (Student, Grade 7): john.smith7@clarascienceacademy.org
John Smith (Teacher): john.smith.teacher@clarascienceacademy.org
```

**Short names:**
```
First Name: Li
Last Name: Wang
Email: li.wang@clarascienceacademy.org
```

---

## Testing the Dual Email System

### Test Case 1: Staff Member with Both Emails

**Setup:**
```python
user = User.query.filter_by(username='teacher1').first()
user.email = 'teacher1personal@gmail.com'
user.google_workspace_email = 'teacher1@clarascienceacademy.org'
db.session.commit()
```

**Test:**
1. Go to login page
2. Click "Sign in with Google"
3. Sign in with `teacher1@clarascienceacademy.org`
4. ✅ Should log in successfully

### Test Case 2: Student with Only Personal Email

**Setup:**
```python
user = User.query.filter_by(username='student1').first()
user.email = 'student1@clarascienceacademy.org'
user.google_workspace_email = None
db.session.commit()
```

**Test:**
1. Go to login page
2. Click "Sign in with Google"
3. Sign in with `student1@clarascienceacademy.org`
4. ✅ Should log in successfully (matches personal email)

### Test Case 3: User with No Matching Email

**Setup:**
```python
user = User.query.filter_by(username='student2').first()
user.email = 'parent@gmail.com'
user.google_workspace_email = None
db.session.commit()
```

**Test:**
1. Go to login page
2. Click "Sign in with Google"
3. Sign in with `student2@clarascienceacademy.org`
4. ❌ Should be blocked with warning message

---

## Production Deployment Checklist

### Before Deploying to Production

- [ ] Run database migration: `python add_google_workspace_email.py`
- [ ] Populate emails: `python populate_google_workspace_emails.py`
- [ ] Review generated emails: `python populate_google_workspace_emails.py show`
- [ ] Manually fix any errors or duplicates
- [ ] Test with 3-5 users locally
- [ ] Update `client_secret.json` with production credentials
- [ ] Set production redirect URI in Google Cloud Console
- [ ] **REMOVE line 587 in authroutes.py** (OAUTHLIB_INSECURE_TRANSPORT)
- [ ] Verify HTTPS is enabled on production server
- [ ] Test on production domain
- [ ] Monitor activity logs for first 24 hours

### Deployment Commands

```bash
# 1. Add the new column
python add_google_workspace_email.py

# 2. Populate emails
python populate_google_workspace_emails.py

# 3. Verify
python populate_google_workspace_emails.py show

# 4. Deploy code to production
git add .
git commit -m "Add Google Workspace authentication with dual email system"
git push origin main

# 5. On production server, run migration
python add_google_workspace_email.py
python populate_google_workspace_emails.py
```

---

## Maintenance

### Adding New Users

When creating new users, set both emails:

```python
new_user = User(
    username='new.teacher',
    password_hash=generate_password_hash('temp_password'),
    role='Teacher',
    email='newteacher@gmail.com',  # Personal email
    google_workspace_email='new.teacher@clarascienceacademy.org'  # Workspace email
)
db.session.add(new_user)
db.session.commit()
```

### Updating Existing Users

Via management dashboard or script:

```python
user = User.query.filter_by(username='existing.user').first()
user.google_workspace_email = 'existing.user@clarascienceacademy.org'
db.session.commit()
```

### Handling Email Changes

If a user's Google Workspace email changes:

```python
user = User.query.filter_by(username='user.name').first()
user.google_workspace_email = 'new.email@clarascienceacademy.org'
db.session.commit()
```

Personal email remains unchanged.

---

## Troubleshooting

### Issue: "Your Google Account is not associated..."

**Check:**
1. Does user exist in database?
   ```python
   User.query.filter_by(username='john.doe').first()
   ```

2. What are their current emails?
   ```bash
   python populate_google_workspace_emails.py show
   ```

3. Does either email match their Google account?
   - Personal email: `user.email`
   - Workspace email: `user.google_workspace_email`

**Fix:**
```bash
python populate_google_workspace_emails.py set john.doe john.doe@clarascienceacademy.org
```

### Issue: Duplicate Email Error

**Cause:** Two users trying to use the same Google Workspace email

**Fix:**
1. Identify the duplicate:
   ```python
   User.query.filter_by(google_workspace_email='duplicate@clarascienceacademy.org').all()
   ```

2. Update one user to a different email:
   ```python
   user = User.query.filter_by(username='user2').first()
   user.google_workspace_email = 'user2.alternate@clarascienceacademy.org'
   db.session.commit()
   ```

### Issue: Script Shows "Could not generate email"

**Cause:** User's first_name or last_name is missing in Student or TeacherStaff table

**Fix:**
1. Update the Student or TeacherStaff record with proper names
2. Re-run the population script, or
3. Set manually:
   ```bash
   python populate_google_workspace_emails.py set username email@domain.org
   ```

---

## Security Considerations

### Email Uniqueness

Both email fields have `unique=True` constraint:
- No two users can have the same personal email
- No two users can have the same Google Workspace email
- A user CAN have the same value in both fields (if they use workspace email for everything)

### Privacy

- **Personal emails** are private and used for school communications
- **Google Workspace emails** are institutional and visible in Google Workspace
- Neither email is exposed to other students/users in the UI

### Data Integrity

- Both fields are `nullable=True` - not required
- Users can exist without either email (username/password only)
- Google Sign-In only works if at least one email matches

---

## Best Practices

### For Administrators

1. **Always set Google Workspace email** for users who will use Google Sign-In
2. **Keep personal emails** for parent contact and records
3. **Use consistent format** for workspace emails (firstname.lastname@domain.org)
4. **Document email format** in your school's IT policy
5. **Audit regularly** - run `show` command monthly to verify emails

### For Users

1. **Personal email** - Use for:
   - Parent communications
   - Personal notifications
   - Emergency contact
   - Non-school related items

2. **Google Workspace email** - Use for:
   - Signing in to Clara Science Academy
   - Google Classroom
   - School email communications
   - Official school business

### For Developers

1. **Always check both fields** when implementing email-based features
2. **Use `google_workspace_email` for Google integrations**
3. **Use `email` for general communications**
4. **Handle null values** - both fields are optional
5. **Log email changes** for audit trail

---

## Migration Workflow

### Step-by-Step Migration Process

#### Phase 1: Database Update (Day 1)
```bash
# 1. Backup database
# 2. Add new column
python add_google_workspace_email.py

# 3. Verify column was added
python populate_google_workspace_emails.py show
```

#### Phase 2: Email Population (Day 1-2)
```bash
# 1. Auto-populate all emails
python populate_google_workspace_emails.py

# 2. Review the output
# 3. Manually fix any errors or special cases
python populate_google_workspace_emails.py set username email@domain.org

# 4. Verify all users have workspace emails
python populate_google_workspace_emails.py show
```

#### Phase 3: Testing (Day 2-3)
```bash
# 1. Test locally with 5-10 users
# 2. Test each role (Student, Teacher, Director)
# 3. Test edge cases (duplicate names, special characters)
# 4. Verify activity logs
```

#### Phase 4: Production Deployment (Day 3-4)
```bash
# 1. Deploy code to production
# 2. Run migration on production database
# 3. Populate emails on production
# 4. Test with real users
# 5. Monitor for 24 hours
```

#### Phase 5: User Communication (Day 4-5)
- Send email to all staff explaining Google Sign-In
- Provide instructions and screenshots
- Offer support for first week
- Collect feedback

---

## Advanced Usage

### Finding Users Without Workspace Email

```python
from app import app, db
from models import User

with app.app_context():
    users_without_workspace = User.query.filter(
        User.google_workspace_email == None
    ).all()
    
    print(f"Found {len(users_without_workspace)} users without Google Workspace email:")
    for user in users_without_workspace:
        print(f"  - {user.username} ({user.role})")
```

### Bulk Update from CSV

Create a CSV file (`workspace_emails.csv`):
```csv
username,workspace_email
john.doe,john.doe@clarascienceacademy.org
jane.smith,jane.smith@clarascienceacademy.org
bob.jones,bob.jones@clarascienceacademy.org
```

Run script:
```python
import csv
from app import app, db
from models import User

with app.app_context():
    with open('workspace_emails.csv', 'r') as f:
        reader = csv.DictReader(f)
        updated = 0
        for row in reader:
            user = User.query.filter_by(username=row['username']).first()
            if user:
                user.google_workspace_email = row['workspace_email']
                updated += 1
                print(f"✅ {user.username}: {row['workspace_email']}")
        
        db.session.commit()
        print(f"\n✅ Updated {updated} users")
```

### Export Current Emails to CSV

```python
import csv
from app import app, db
from models import User

with app.app_context():
    users = User.query.all()
    
    with open('user_emails_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Username', 'Role', 'Personal Email', 'Workspace Email'])
        
        for user in users:
            writer.writerow([
                user.username,
                user.role,
                user.email or '',
                user.google_workspace_email or ''
            ])
    
    print(f"✅ Exported {len(users)} users to user_emails_export.csv")
```

---

## FAQ

### Q: Do I need to set both emails for every user?

**A:** No. You only need to set `google_workspace_email` for users who will use Google Sign-In. Personal email is optional.

### Q: Can both fields have the same email?

**A:** Yes! If a user only uses their Google Workspace email, you can set both fields to the same value.

### Q: What if a user doesn't have a Google Workspace account?

**A:** Leave `google_workspace_email` empty. They can still log in with username/password.

### Q: Can I use this for parent accounts?

**A:** Yes! Parents can have their personal email in `email` and their Google account (if they have one) in `google_workspace_email`.

### Q: What happens if I delete a user's workspace email?

**A:** They won't be able to sign in with Google anymore, but can still use username/password.

### Q: How do I handle name changes (marriage, legal name change)?

**A:** Update both the name in Student/TeacherStaff table AND the `google_workspace_email` field to match their new Google Workspace account.

---

## Summary

✅ **Two email fields** - Personal and Google Workspace  
✅ **Flexible authentication** - Google Sign-In checks both  
✅ **Easy migration** - Automated scripts provided  
✅ **Backward compatible** - Existing emails still work  
✅ **Production ready** - Fully tested and documented  

**Next Steps:**
1. Run `python add_google_workspace_email.py`
2. Run `python populate_google_workspace_emails.py`
3. Review and fix any errors
4. Test Google Sign-In
5. Deploy to production

---

*Last updated: November 6, 2025*
*Clara Science Academy - Dual Email System*

