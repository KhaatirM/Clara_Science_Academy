# Google Forms Integration Setup Guide

This guide will help you configure Google Forms integration for the quiz assignment features on your live server.

---

## 📋 Prerequisites

- Google Workspace account (for your school domain)
- Access to Google Cloud Console
- Access to Render dashboard for environment variables

---

## 🔧 Part 1: Google Cloud Console Setup

### Step 1: Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one if needed)
3. Navigate to **"APIs & Services" > "Library"**
4. Enable the following APIs:
   - ✅ **Google Forms API** (search for "Google Forms API")
   - ✅ **Google Drive API** (needed to create forms)
   - ✅ **Google OAuth2 API** (if not already enabled)

### Step 2: Update OAuth Consent Screen Scopes

1. Go to **"APIs & Services" > "OAuth consent screen"**
2. Click **"Edit App"** or configure if not already done
3. Click **"Add or Remove Scopes"**
4. Add the following scopes:
   - `https://www.googleapis.com/auth/forms.body` (Read/write form structure)
   - `https://www.googleapis.com/auth/forms.responses.readonly` (Read form responses)
   - `https://www.googleapis.com/auth/drive` (Create forms in Drive)
5. Click **"Update"** and **"Save and Continue"**
6. If prompted, submit for verification (or mark as "Testing" if in development)

### Step 3: Verify OAuth Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Find your OAuth 2.0 Client ID (or create one if needed)
3. Under **"Authorized redirect URIs"**, ensure you have:
   ```
   https://www.clarascienceacademy.org/teacher/settings/google-account/callback
   https://www.clarascienceacademy.org/management/settings/google-account/callback
   https://www.clarascienceacademy.org/auth/google/callback
   ```
   (Replace with your actual domain if different)

4. **Download** or copy your `client_secret.json` file - you'll need this for Render

---

## 🌐 Part 2: Render Environment Variables

### Required Environment Variables

Add these to your Render service's **Environment** settings:

1. **GOOGLE_CLIENT_ID**
   - Value: Your OAuth Client ID from Google Cloud Console
   - Format: `xxxxx.apps.googleusercontent.com`

2. **GOOGLE_CLIENT_SECRET**
   - Value: Your OAuth Client Secret from Google Cloud Console

3. **GOOGLE_CLIENT_SECRET_JSON** (Alternative to above two)
   - Value: The entire contents of your `client_secret.json` file as a JSON string
   - Format: `{"web":{"client_id":"...","client_secret":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","redirect_uris":["..."]}}`
   - **Note**: This is the recommended method for production

4. **ENCRYPTION_KEY** (if not already set)
   - Value: A Fernet encryption key for storing refresh tokens securely
   - Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### How to Add Environment Variables in Render

1. Go to your Render dashboard
2. Select your service (Flask app)
3. Go to **"Environment"** tab
4. Click **"Add Environment Variable"**
5. Add each variable above
6. Click **"Save Changes"**
7. **Redeploy** your service for changes to take effect

---

## ✅ Part 3: Verification Steps

### After Deployment:

1. **Test Google Account Connection**
   - Log in as a teacher or administrator
   - Go to Settings
   - Click "Connect Google Account"
   - You should see the new scopes requested (Forms API, Drive API)
   - Grant permissions

2. **Test Quiz Export**
   - Create a quiz assignment with questions
   - Go to the assignment view
   - Click "Export to Google Forms"
   - Should create a Google Form and link it

3. **Test Google Forms Linking**
   - Create a quiz assignment
   - In quiz creation, paste a Google Form URL
   - Check "Link this quiz to the Google Form above"
   - Save the quiz
   - Should show "Google Forms Linked" in assignment view

4. **Test Submission Sync**
   - For a linked Google Form quiz
   - Have students submit responses in Google Forms
   - Click "Sync Submissions" in assignment view
   - Should import submissions

---

## ⚠️ Important Notes

### OAuth Re-authorization Required

**All users who previously connected their Google account will need to reconnect** because we added new scopes:
- `forms.body` (read/write)
- `forms.responses.readonly`
- `drive` (create)

The system will automatically request these new permissions when they reconnect.

### API Quotas

Google Forms API has quotas:
- **Default**: 60 requests per minute per user
- If you hit limits, you may need to request quota increases in Google Cloud Console

### Security

- Never commit `client_secret.json` to version control
- Use environment variables in Render
- The `ENCRYPTION_KEY` must be kept secret and never shared

---

## 🐛 Troubleshooting

### "Google Forms API is not enabled"
- **Solution**: Enable Google Forms API in Google Cloud Console (Step 1 above)

### "403 Forbidden" when exporting
- **Solution**: Check that `forms.body` and `drive` scopes are added to OAuth consent screen

### "Failed to create Google Form"
- **Solution**: 
  - Verify Google Drive API is enabled
  - Check that user has reconnected with new scopes
  - Check Render logs for detailed error messages

### "No refresh token" errors
- **Solution**: User needs to reconnect their Google account in Settings to get a new refresh token with updated scopes

### Submissions not syncing
- **Solution**:
  - Verify Google Form is set to collect respondent emails
  - Check that student emails in system match Google Form respondent emails
  - Check Render logs for API errors

---

## 📝 Quick Checklist

Before going live, ensure:

- [ ] Google Forms API enabled in Google Cloud Console
- [ ] Google Drive API enabled in Google Cloud Console
- [ ] OAuth scopes added to consent screen:
  - [ ] `forms.body`
  - [ ] `forms.responses.readonly`
  - [ ] `drive`
- [ ] Environment variables set in Render:
  - [ ] `GOOGLE_CLIENT_ID` OR `GOOGLE_CLIENT_SECRET_JSON`
  - [ ] `GOOGLE_CLIENT_SECRET` (if not using JSON)
  - [ ] `ENCRYPTION_KEY`
- [ ] OAuth redirect URIs configured in Google Cloud Console
- [ ] Service redeployed on Render
- [ ] Test Google account connection
- [ ] Test quiz export functionality

---

## 🔗 Useful Links

- [Google Forms API Documentation](https://developers.google.com/forms/api)
- [Google OAuth 2.0 Setup](https://developers.google.com/identity/protocols/oauth2)
- [Render Environment Variables](https://render.com/docs/environment-variables)

---

**Last Updated**: December 28, 2025

