# Google Forms Integration - Live Server Setup Guide

**Quick setup guide for deploying Google Forms quiz features to production.**

---

## 🎯 What You Need to Do

### **On Google Cloud Console** (5-10 minutes)
1. Enable Google Forms API
2. Enable Google Drive API  
3. Add new OAuth scopes to consent screen
4. Verify redirect URIs

### **On Render** (5 minutes)
1. Add environment variables (if not already set)
2. Redeploy service

---

## 📘 Part 1: Google Cloud Console Configuration

### Step 1: Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (the same one you use for Google OAuth)
3. Navigate to **"APIs & Services" > "Library"**

4. **Enable Google Forms API:**
   - Search for: `Google Forms API`
   - Click on it
   - Click **"Enable"** button
   - Wait for it to enable (usually instant)

5. **Enable Google Drive API:**
   - Search for: `Google Drive API`
   - Click on it
   - Click **"Enable"** button
   - Wait for it to enable

### Step 2: Add New OAuth Scopes

1. Go to **"APIs & Services" > "OAuth consent screen"**
2. Click **"Edit App"** (or configure if not done)
3. Scroll down to **"Scopes"** section
4. Click **"Add or Remove Scopes"**
5. In the filter/search box, search for and add these scopes:
   - `https://www.googleapis.com/auth/forms.body` - **Read/write form structure**
   - `https://www.googleapis.com/auth/forms.responses.readonly` - **Read form responses**
   - `https://www.googleapis.com/auth/drive` - **Create forms in Drive**
6. Click **"Update"** at the bottom
7. Click **"Save and Continue"** through any remaining screens
8. If you see a "Testing" or "Publish" option, you can leave it in Testing mode for now

### Step 3: Verify Redirect URIs

1. Go to **"APIs & Services" > "Credentials"**
2. Click on your **OAuth 2.0 Client ID** (the one you use for the app)
3. Under **"Authorized redirect URIs"**, make sure you have:
   ```
   https://www.clarascienceacademy.org/teacher/settings/google-account/callback
   https://www.clarascienceacademy.org/management/settings/google-account/callback
   https://www.clarascienceacademy.org/auth/google/callback
   ```
   *(Replace `clarascienceacademy.org` with your actual domain if different)*

4. If any are missing, click **"Add URI"** and add them
5. Click **"Save"**

---

## 🌐 Part 2: Render Environment Variables

### Option A: Using GOOGLE_CLIENT_SECRET_JSON (Recommended)

This is the easiest method - just paste your entire `client_secret.json` file.

1. **Get your client_secret.json:**
   - In Google Cloud Console, go to **"APIs & Services" > "Credentials"**
   - Click on your OAuth 2.0 Client ID
   - Click **"Download JSON"** button
   - Open the downloaded file in a text editor
   - Copy the **entire contents**

2. **Add to Render:**
   - Go to your Render dashboard
   - Select your web service
   - Click **"Environment"** in the left sidebar
   - Click **"Add Environment Variable"**
   - **Key:** `GOOGLE_CLIENT_SECRET_JSON`
   - **Value:** Paste the entire JSON content (all of it, including the `{` and `}`)
   - Click **"Save Changes"**

### Option B: Using Separate Variables (Alternative)

If you prefer separate variables:

1. **Add GOOGLE_CLIENT_ID:**
   - **Key:** `GOOGLE_CLIENT_ID`
   - **Value:** Your Client ID (from `client_secret.json` or Credentials page)
   - Format: `xxxxx.apps.googleusercontent.com`

2. **Add GOOGLE_CLIENT_SECRET:**
   - **Key:** `GOOGLE_CLIENT_SECRET`
   - **Value:** Your Client Secret (from `client_secret.json` or Credentials page)
   - Format: `GOCSPX-xxxxx`

3. **Add ENCRYPTION_KEY** (if not already set):
   - **Key:** `ENCRYPTION_KEY`
   - **Value:** Generate using:
     ```bash
     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     ```
   - Copy the output and paste as the value

### After Adding Variables:

1. **Redeploy your service:**
   - Render may auto-redeploy, or
   - Go to **"Manual Deploy"** > **"Deploy latest commit"**
   - Wait for deployment to complete (2-5 minutes)

---

## ✅ Part 3: Testing After Deployment

### Test 1: Google Account Connection

1. Log in as a teacher or administrator
2. Go to **Settings**
3. Click **"Connect Google Account"**
4. You should see a Google consent screen asking for permissions
5. **Important:** You should see the new scopes listed:
   - "See, edit, create, and delete all of your Google Forms"
   - "See all your Google Forms responses"
   - "See, edit, create, and delete all of your Google Drive files"
6. Click **"Allow"**
7. You should be redirected back with a success message

### Test 2: Export Quiz to Google Forms

1. Create a quiz assignment with at least one question
2. Go to the assignment view
3. Look for **"Google Forms Integration"** section
4. Click **"Export to Google Forms"**
5. Should create a Google Form and show a success message with a link
6. Click the link to verify the form was created correctly

### Test 3: Link Existing Google Form

1. Create a quiz assignment
2. In the quiz creation form, scroll to **"Google Forms Integration"**
3. Paste a Google Form URL
4. Check **"Link this quiz to the Google Form above"**
5. Save the quiz
6. In assignment view, should show **"Google Forms Linked"** section

---

## ⚠️ Important Notes

### Users Must Reconnect Google Accounts

**All teachers/administrators who previously connected their Google account MUST reconnect** because we added new API scopes. The system will automatically request the new permissions when they reconnect.

**Tell your users:**
- Go to Settings
- Click "Connect Google Account" (even if already connected)
- Grant the new permissions
- Done!

### API Quotas

Google Forms API has default quotas:
- **60 requests per minute per user**
- If you have many teachers exporting quizzes simultaneously, you may hit limits
- If needed, request quota increases in Google Cloud Console under "APIs & Services" > "Quotas"

### Troubleshooting

**"Google Forms API is not enabled"**
- Go back to Google Cloud Console
- Enable Google Forms API (Step 1 above)

**"403 Forbidden" when exporting**
- Check that all 3 scopes are added to OAuth consent screen
- User needs to reconnect Google account with new scopes

**"Failed to create Google Form"**
- Verify Google Drive API is enabled
- Check Render logs for detailed error messages
- Ensure user has reconnected with new scopes

**Submissions not syncing**
- Google Form must be configured to collect respondent emails
- Student emails in your system must match Google Form respondent emails exactly
- Check Render logs for API errors

---

## 📋 Quick Checklist

Before going live:

- [ ] Google Forms API enabled in Google Cloud Console
- [ ] Google Drive API enabled in Google Cloud Console
- [ ] OAuth scopes added:
  - [ ] `forms.body`
  - [ ] `forms.responses.readonly`
  - [ ] `drive`
- [ ] Redirect URIs verified in OAuth credentials
- [ ] Environment variables set in Render:
  - [ ] `GOOGLE_CLIENT_SECRET_JSON` (recommended) OR
  - [ ] `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` + `ENCRYPTION_KEY`
- [ ] Service redeployed on Render
- [ ] Tested Google account connection
- [ ] Tested quiz export functionality

---

## 🆘 Need Help?

If something doesn't work:

1. **Check Render logs:**
   - Go to Render dashboard > Your service > "Logs"
   - Look for error messages related to Google Forms API

2. **Check Google Cloud Console:**
   - Verify APIs are enabled
   - Check OAuth consent screen has all scopes
   - Verify redirect URIs are correct

3. **Common Issues:**
   - Forgot to enable an API → Enable it in Google Cloud Console
   - Missing scope → Add it to OAuth consent screen
   - User hasn't reconnected → They need to reconnect in Settings
   - Wrong redirect URI → Add correct URI in OAuth credentials

---

**Ready to deploy!** Follow the steps above and your Google Forms integration will be ready for testers. 🚀


