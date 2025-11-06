# Google Workspace for Education OAuth Setup Guide

## Overview
This guide will help you integrate Google Workspace for Education authentication into Clara Science Academy. Users with Google Workspace accounts (registered in your system) will be able to sign in using their Google credentials.

## 🔐 Security Note
**IMPORTANT:** Only users whose email addresses are already registered in the Clara Science Academy database will be able to sign in. This ensures that random Google account holders cannot access your system.

---

## Part 1: Google Cloud Console Setup

### Step 1: Create or Access Your Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google Workspace for Education admin account
3. If you already have a project (e.g., "iboss Setup"), select it. Otherwise:
   - Click "Select a Project" at the top
   - Click "New Project"
   - Name it (e.g., "Clara Science Auth")
   - Click "Create"

### Step 2: Enable Google OAuth API

1. In your project, go to **"APIs & Services" > "Library"**
2. Search for **"Google+ API"** or **"Google Identity"**
3. Click on it and press **"Enable"**

### Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services" > "OAuth consent screen"**
2. Select **"Internal"** (this restricts sign-in to your Google Workspace domain)
3. Click **"Create"**
4. Fill in the required information:
   - **App name:** Clara Science Academy
   - **User support email:** Your admin email
   - **App logo:** (Optional) Upload your school logo
   - **App domain:** Your website domain (e.g., `clarascienceacademy.org`)
   - **Authorized domains:** Add your domain (e.g., `clarascienceacademy.org`)
   - **Developer contact email:** Your admin email
5. Click **"Save and Continue"**
6. **Scopes:** Click "Add or Remove Scopes" and add:
   - `userinfo.email`
   - `userinfo.profile`
   - `openid`
7. Click **"Save and Continue"**
8. Review and click **"Back to Dashboard"**

### Step 4: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"Create Credentials"** at the top
3. Select **"OAuth 2.0 Client ID"**
4. For **"Application type"**, select **"Web application"**
5. **Name:** "Clara Science Website"
6. **Authorized redirect URIs** - Click "ADD URI" and add BOTH:
   ```
   http://127.0.0.1:5000/auth/google/callback
   https://clarascienceacademy.org/auth/google/callback
   ```
   
   ⚠️ **Important Notes:**
   - Replace `clarascienceacademy.org` with your actual production domain
   - The first URI is for local development
   - The second URI is for production
   - Make sure there are NO typos - the callback must match exactly
   - Use `https://` for production (not `http://`)
   - No trailing slash at the end

7. Click **"Create"**
8. A popup will appear with your **Client ID** and **Client Secret**
   - **DO NOT CLOSE THIS YET!**
   - Copy both values somewhere safe (you'll need them in Part 2)
9. Click **"Download JSON"** - this downloads `client_secret.json`
10. **IMPORTANT:** Keep this file secure and never commit it to version control!

---

## Part 2: Flask Application Configuration

### Step 1: Place client_secret.json

1. Take the `client_secret.json` file you downloaded
2. Place it in the **root directory** of your Clara Science Academy project
   ```
   Clara_science_app/
   ├── client_secret.json  ← Place it here
   ├── app.py
   ├── config.py
   ├── requirements.txt
   └── ...
   ```
3. **Verify** it's in .gitignore (already done ✅)

### Step 2: Set Environment Variables (Production Only)

For **production** deployment, set these environment variables on your hosting platform (e.g., Render, Heroku):

```bash
GOOGLE_CLIENT_ID=your-client-id-from-google-cloud
GOOGLE_CLIENT_SECRET=your-client-secret-from-google-cloud
```

**Note:** For local development, the app will automatically use `client_secret.json`, so you don't need to set these environment variables locally.

### Step 3: Verify Requirements

The `google-auth-oauthlib` library is already in `requirements.txt`. If you're setting up a new environment:

```bash
pip install -r requirements.txt
```

---

## Part 3: Testing the Integration

### Local Testing

1. **Start your Flask application:**
   ```bash
   python app.py
   ```
   
2. **Navigate to the login page:**
   ```
   http://127.0.0.1:5000/login
   ```

3. **Look for the "Sign in with Google" button**
   - It should appear below the regular login form
   - It should have the Google logo (colorful icon)
   - Clicking it should redirect you to Google's sign-in page

4. **Test with a registered user:**
   - Sign in with a Google account whose **email is registered** in your User database
   - You should be redirected back and logged in successfully
   - Check that the user's dashboard loads correctly

5. **Test with an unregistered user:**
   - Sign in with a Google account whose email is NOT in your database
   - You should see a warning message: "Your Google Account is not associated with an account at Clara Science Academy..."
   - User should NOT be logged in

### Production Testing

1. **Deploy your application** to your production server
2. **Verify the production redirect URI** is set correctly in Google Cloud Console
3. **Test on your production domain:**
   ```
   https://clarascienceacademy.org/login
   ```
4. Follow the same testing steps as local testing above

---

## Part 4: User Management

### Linking Google Accounts to Existing Users

For users to sign in with Google, their **email address in the Google Workspace** must match the **email address in your User database**.

#### Option 1: Manual Update via Management Dashboard
1. As an administrator, go to your user management page
2. Edit each user's profile
3. Set their **email** field to match their Google Workspace email
4. Save changes

#### Option 2: Bulk Update via Database Script
Create a script to update user emails in bulk:

```python
# update_user_emails.py
from app import db
from models import User

# Example: Update email for a student
user = User.query.filter_by(username='john.doe').first()
if user:
    user.email = 'john.doe@clarascienceacademy.org'  # Google Workspace email
    db.session.commit()
    print(f"Updated email for {user.username}")
```

Run with:
```bash
python update_user_emails.py
```

#### Option 3: CSV Import
1. Export your Google Workspace users to CSV
2. Create a matching CSV with usernames and emails
3. Use a script to batch update the database

---

## Security Features

### ✅ What's Protected

1. **Email Verification:**
   - Only registered emails can sign in
   - Google account must match email in User database

2. **Internal Apps Only:**
   - OAuth consent screen set to "Internal"
   - Only users in your Google Workspace domain can see the app
   - External Google accounts cannot even attempt to sign in

3. **CSRF Protection:**
   - OAuth state parameter prevents CSRF attacks
   - Session state verification on callback

4. **Secure Token Handling:**
   - Tokens never exposed to client
   - Automatic token verification
   - Secure session management

5. **Activity Logging:**
   - All Google login attempts logged
   - Failed attempts tracked with reason
   - Success/failure monitoring

### ⚠️ Important Security Notes

1. **Never commit `client_secret.json` to version control**
   - Already in `.gitignore` ✅
   - Contains sensitive OAuth credentials

2. **HTTPS Required in Production**
   - OAuth requires HTTPS for production
   - Local development uses HTTP (line 587 in authroutes.py)
   - **Remove or comment out line 587 in production!**
   
   ```python
   # In authroutes.py, line 587:
   # REMOVE THIS LINE IN PRODUCTION:
   os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
   ```

3. **Keep Client Secret Safe**
   - Don't share screenshots containing it
   - Don't email it
   - Use environment variables in production

4. **Monitor Login Activity**
   - Check activity logs regularly
   - Review failed Google login attempts
   - Investigate suspicious patterns

---

## Troubleshooting

### Issue 1: "Google Sign-In is not configured" Error

**Solution:**
- Check that `client_secret.json` exists in project root
- Verify file is valid JSON (not corrupted)
- Check file permissions (should be readable)

### Issue 2: "Invalid redirect URI" Error

**Cause:** The callback URL doesn't match what's in Google Cloud Console

**Solution:**
1. Go to Google Cloud Console > Credentials
2. Click on your OAuth 2.0 Client ID
3. Check **"Authorized redirect URIs"**
4. Make sure it EXACTLY matches:
   - Local: `http://127.0.0.1:5000/auth/google/callback`
   - Production: `https://yourdomain.com/auth/google/callback`
5. No extra slashes, correct protocol (http vs https), correct port

### Issue 3: "Your Google Account is not associated..." Message

**This is EXPECTED behavior for security!**

**Solution:**
1. Verify the user's email is registered in your User database
2. Make sure it's an exact match (case-sensitive)
3. Update the user's email if necessary:
   ```python
   user = User.query.filter_by(username='student1').first()
   user.email = 'student1@yourdomain.org'
   db.session.commit()
   ```

### Issue 4: Button doesn't appear on login page

**Solution:**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Do a hard refresh (Ctrl+F5)
3. Check for JavaScript errors in browser console (F12)
4. Verify `login.html` was updated correctly

### Issue 5: "Access blocked: This app has not been verified"

**Cause:** Trying to use "External" OAuth consent screen

**Solution:**
1. Go to Google Cloud Console > OAuth consent screen
2. Change to **"Internal"** user type
3. This restricts to your Google Workspace domain only
4. Re-publish the app

### Issue 6: Error about missing scopes

**Solution:**
1. Go to OAuth consent screen in Google Cloud Console
2. Edit app registration
3. Go to "Scopes" section
4. Add these scopes:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
5. Save and re-test

---

## Maintenance and Updates

### Rotating Client Secret

If your `client_secret.json` is compromised:

1. Go to Google Cloud Console > Credentials
2. Click on your OAuth Client ID
3. Click "Add Secret" or "Delete" the old one
4. Download new `client_secret.json`
5. Replace the old file
6. Update environment variables if used
7. Restart your application

### Updating Redirect URIs

When moving to a new domain:

1. Go to Google Cloud Console > Credentials
2. Click your OAuth Client ID
3. Add new redirect URI
4. Keep old one active during transition
5. Test new domain
6. Remove old URI once confirmed working

### Monitoring Usage

1. Go to Google Cloud Console > Dashboard
2. View API usage metrics
3. Monitor for unusual patterns
4. Set up alerts for quota limits

---

## FAQ

### Q: Can students sign in with personal Gmail accounts?

**A:** No, if you set the OAuth consent screen to "Internal". Only users with accounts in your Google Workspace for Education domain can sign in.

### Q: Do I need to import all Google Workspace users into Clara Science?

**A:** No. Only users who are already registered in your Clara Science Academy database can sign in, regardless of whether they exist in Google Workspace.

### Q: What if a user's email changes?

**A:** Update their email in the Clara Science Academy User database to match their new Google Workspace email.

### Q: Can users still sign in with username/password?

**A:** Yes! Google Sign-In is an additional option. Users can always use their regular username and password.

### Q: Does this replace the password system?

**A:** No. It's a convenience feature. Both methods work independently.

### Q: What data does the app get from Google?

**A:** Only:
- Email address
- Full name
- Profile picture URL

We do NOT access calendars, drives, or any other Google services.

### Q: Is this secure?

**A:** Yes! The implementation follows Google's OAuth 2.0 best practices:
- State parameter for CSRF protection
- Token verification
- Internal-only access
- Email verification against database
- Activity logging

---

## Support

If you encounter issues not covered in this guide:

1. **Check the logs:** Look in your application logs for detailed error messages
2. **Google Cloud Logs:** Check the Google Cloud Console > Logging for API errors
3. **Activity Logs:** Review the activity log in Clara Science Academy
4. **Email:** Contact your system administrator

---

## Summary Checklist

Before going live with Google OAuth:

- [ ] Google Cloud project created
- [ ] OAuth consent screen configured as "Internal"
- [ ] OAuth 2.0 Client ID created
- [ ] Redirect URIs added (both local and production)
- [ ] `client_secret.json` downloaded and placed in project root
- [ ] Environment variables set (production only)
- [ ] User emails in database match Google Workspace emails
- [ ] Tested with registered user (success)
- [ ] Tested with unregistered user (blocked)
- [ ] Tested on production domain
- [ ] Removed `OAUTHLIB_INSECURE_TRANSPORT` line for production
- [ ] Verified HTTPS is enabled on production
- [ ] Activity logging verified
- [ ] Documentation shared with team

---

## Quick Reference

### Important URLs

- **Google Cloud Console:** https://console.cloud.google.com/
- **OAuth Consent Screen:** `APIs & Services` > `OAuth consent screen`
- **Credentials:** `APIs & Services` > `Credentials`
- **Logs:** `Logging` > `Logs Explorer`

### Important Files

- `config.py` - OAuth configuration
- `authroutes.py` - Login routes and Google OAuth logic
- `templates/shared/login.html` - Login page with Google button
- `client_secret.json` - OAuth credentials (NEVER commit!)
- `.gitignore` - Ensures `client_secret.json` is not committed

### Important Routes

- `/login` - Login page (now with Google button)
- `/google-login` - Initiates Google OAuth flow
- `/auth/google/callback` - Handles Google's response

---

*Last updated: [Current Date]*
*Clara Science Academy - Google Workspace Integration*

