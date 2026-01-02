# Google OAuth Environment Variable Setup

## ✅ What You've Done

You've successfully configured Google OAuth to read credentials from an environment variable instead of a file. This is the **recommended approach for production deployments**.

---

## 🔧 Next Steps on Render

### 1. Go to Your Render Dashboard

1. Navigate to your web service
2. Click on **"Environment"** in the left sidebar

### 2. Add the Environment Variable

1. Click **"Add Environment Variable"**
2. Fill in the following:
   - **Key:** `GOOGLE_CLIENT_SECRET_JSON`
   - **Value:** Paste the **entire contents** of your `client_secret.json` file

**Example of what the value should look like:**

```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": [
      "https://www.clarascienceacademy.org/auth/google/callback"
    ]
  }
}
```

3. Click **"Save Changes"**

### 3. Redeploy Your Service

After saving the environment variable:

1. Render will automatically trigger a redeploy
2. Wait for the deployment to complete (1-2 minutes)
3. Your Google Sign-In should now work!

---

## 🧪 Testing

After deployment:

1. Go to your login page: `https://www.clarascienceacademy.org/login`
2. Click the **"Sign in with Google"** button
3. You should be redirected to Google's sign-in page
4. After signing in with a Google account that matches a user's email in your system, you should be logged in successfully

---

## 📝 How It Works

The updated `authroutes.py` now:

1. **First checks** for the `GOOGLE_CLIENT_SECRET_JSON` environment variable
2. **If found:** Uses the JSON configuration from the environment variable
3. **If not found:** Falls back to looking for `client_secret.json` file (for local development)

This means:
- ✅ **Production (Render):** Uses environment variable (secure, no file needed)
- ✅ **Local Development:** Uses `client_secret.json` file (convenient for testing)

---

## 🔒 Security Notes

- ✅ **Environment variables are secure** - they're encrypted and not visible in your code
- ✅ **Never commit** `client_secret.json` to your Git repository
- ✅ Make sure `client_secret.json` is in your `.gitignore` file

---

## ❓ Troubleshooting

### Error: "Google Sign-In is not configured"

**Cause:** The environment variable is not set or is invalid JSON.

**Solution:**
1. Check that `GOOGLE_CLIENT_SECRET_JSON` exists in Render Environment settings
2. Verify the JSON is valid (no extra quotes, proper formatting)
3. Redeploy after making changes

### Error: "Invalid login session"

**Cause:** OAuth state mismatch (usually from browser cache).

**Solution:**
1. Clear browser cookies/cache
2. Try again in an incognito/private window

### Error: "Your Google Account is not associated with an account"

**Cause:** The Google email doesn't match any user's `email` or `google_workspace_email` in your database.

**Solution:**
1. Go to Management Dashboard → Students or Teachers
2. Edit the user and add their Google email to the "Google Workspace Email" field
3. Save and try logging in with Google again

---

## 📚 Related Documentation

- `GOOGLE_OAUTH_SETUP_GUIDE.md` - Full Google Cloud Console setup
- `DUAL_EMAIL_SYSTEM_GUIDE.md` - Understanding the dual email system
- `AUTO_GENERATED_GOOGLE_WORKSPACE_EMAILS.md` - Auto-generation of workspace emails

---

**Last Updated:** November 6, 2025

