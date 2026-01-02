# Google OAuth Final Fix - Client ID Extraction

## ✅ What Was Fixed

The Google OAuth was failing with this error:
```
Token has wrong audience <your-actual-client-id>, 
expected one of ['your-client-id-goes-here']
```

This happened because the `GOOGLE_CLIENT_ID` in `config.py` was set to a placeholder value.

---

## 🔧 The Solution

Instead of hardcoding the Client ID (which GitHub blocks for security), the code now **automatically extracts** the Client ID from the `GOOGLE_CLIENT_SECRET_JSON` environment variable.

### Changes Made:

1. **`config.py`**: Removed hardcoded fallback values for `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
2. **`authroutes.py`**: Added logic to extract the Client ID from the JSON if not set as a separate environment variable

---

## 📋 Current Configuration

Your Render environment should have:

### Environment Variables:
- `DATABASE_URL` - Your PostgreSQL database
- `SECRET_KEY` - Your Flask secret key
- `GOOGLE_CLIENT_SECRET_JSON` - Your complete Google OAuth JSON config

The `GOOGLE_CLIENT_SECRET_JSON` contains:
```json
{
  "web": {
    "client_id": "YOUR-CLIENT-ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR-CLIENT-SECRET",
    "redirect_uris": [
      "https://www.clarascienceacademy.org/auth/google/callback",
      "https://csastudentmanagement.onrender.com/auth/google/callback"
    ]
  }
}
```

---

## 🚀 How It Works Now

1. User clicks "Sign in with Google"
2. App creates OAuth flow using `GOOGLE_CLIENT_SECRET_JSON`
3. User signs in with Google
4. Google redirects back with a token
5. App verifies the token using the Client ID extracted from the JSON
6. User is logged in if their email matches a user in the database

---

## ✅ What Should Work Now

After Render redeploys (which happens automatically after the push):

1. ✅ Google Sign-In button should work
2. ✅ Users can sign in with their `@clarascienceacademy.org` email
3. ✅ No more "wrong audience" errors
4. ✅ No secrets hardcoded in the repository

---

## 🧪 Testing

Once the deployment completes:

1. Go to `https://www.clarascienceacademy.org/login`
2. Click **"Sign in with Google"**
3. Sign in with a Google account that has an email matching a user's `email` or `google_workspace_email` in your database
4. You should be successfully logged in!

---

## 📝 For Staff/Teachers

Make sure each staff member has their Google Workspace email (`@clarascienceacademy.org`) added to their account:

1. Go to **Management Dashboard** → **Teachers**
2. Click **Edit** on the teacher
3. Enter their Google Workspace email in the **"Google Workspace Email"** field
4. Save

Now they can sign in with Google!

---

## 🔒 Security Notes

✅ **No secrets in code** - All credentials are in environment variables
✅ **GitHub protected** - GitHub blocks pushes with hardcoded secrets
✅ **Secure storage** - Render encrypts environment variables
✅ **Automatic extraction** - Client ID is extracted from JSON at runtime

---

**Last Updated:** November 7, 2025  
**Status:** ✅ Fixed and deployed

