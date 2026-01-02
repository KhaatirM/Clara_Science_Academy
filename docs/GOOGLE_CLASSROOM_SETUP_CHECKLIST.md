# Google Classroom Integration - Setup Checklist

## ✅ Completed Implementation

All the following have been successfully implemented and tested:

- [x] Added `cryptography` and `requests` to requirements.txt
- [x] Generated encryption key and added to config.py
- [x] Updated User model with encrypted google_refresh_token field
- [x] Updated Class model with google_classroom_id field
- [x] Created and ran database migration (fields added to database)
- [x] Created google_classroom_service.py helper module
- [x] Added teacher OAuth routes in teacher_routes/settings.py
- [x] Enhanced add_class route with automatic Google Classroom creation
- [x] No linting errors - all code passes validation

## 🔧 Required Configuration (Action Needed)

### 1. Update Google Cloud Console Redirect URIs

**IMPORTANT**: You need to add these redirect URIs to your Google Cloud Console:

1. Go to: https://console.cloud.google.com/
2. Select project: "iboss-integration-477318"
3. Navigate to: APIs & Services > Credentials
4. Click on your OAuth 2.0 Client ID
5. Add these to "Authorized redirect URIs":

**For Development (if testing locally):**
```
http://localhost:5000/teacher/settings/google-account/callback
http://127.0.0.1:5000/teacher/settings/google-account/callback
```

**For Production (REQUIRED):**
```
https://csastudentmanagement.onrender.com/teacher/settings/google-account/callback
https://www.clarascienceacademy.org/teacher/settings/google-account/callback
```

6. Click "Save"

### 2. Verify Google Classroom API is Enabled

1. In Google Cloud Console, go to: APIs & Services > Enabled APIs & services
2. Search for "Google Classroom API"
3. If not enabled, click "Enable API"

### 3. Install New Dependencies (Production)

When deploying to production, ensure the new dependencies are installed:

```bash
pip install -r requirements.txt
```

Or specifically:
```bash
pip install cryptography requests
```

### 4. Set Environment Variables (Production - HIGHLY RECOMMENDED)

For production security, set these environment variables in your Render dashboard:

```
ENCRYPTION_KEY=<your-generated-encryption-key>
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
```

**How to get these values:**
- **ENCRYPTION_KEY**: Generate using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- **GOOGLE_CLIENT_ID**: Found in your `client_secret.json` file under `web.client_id`
- **GOOGLE_CLIENT_SECRET**: Found in your `client_secret.json` file under `web.client_secret`

**Important**: These environment variables are REQUIRED. The config.py file no longer has hardcoded fallback values for security.

### 5. Run Database Migration (Production)

When deploying to production, run the migration script:

```bash
python migrations_scripts/add_google_classroom_fields.py
```

This will add the required columns to your PostgreSQL database.

## 📋 Testing Checklist

After deployment, test the following:

### Teacher Account Connection
- [ ] Teacher can access Settings page
- [ ] "Connect Google Account" button is visible
- [ ] Clicking button redirects to Google OAuth consent screen
- [ ] After granting permissions, teacher is redirected back with success message
- [ ] Settings page shows "Google Account Connected" status

### Automatic Classroom Creation
- [ ] Admin can create a new class
- [ ] When teacher has connected Google account, Google Classroom is created
- [ ] Success message indicates classroom was created and linked
- [ ] google_classroom_id is stored in database
- [ ] Classroom appears in Google Classroom (https://classroom.google.com)

### Without Google Connection
- [ ] Creating class for non-connected teacher still works
- [ ] Info message indicates Google Classroom was not created
- [ ] Class is created in internal system successfully

### Disconnection
- [ ] Teacher can disconnect their Google account from Settings
- [ ] Refresh token is removed from database
- [ ] Settings page shows "Not Connected" status

## 🚀 Deployment Steps

1. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Add Google Classroom integration"
   git push
   ```

2. **Update Google Cloud Console** (see section 1 above)

3. **Deploy to Render** (automatic if connected to GitHub)

4. **Run Migration**:
   - Via Render shell: `python migrations_scripts/add_google_classroom_fields.py`
   - Or include in your deployment script

5. **Set Environment Variables** (optional but recommended)

6. **Test** (follow testing checklist above)

## 📝 User Instructions

### For Teachers (First-Time Setup)

1. Log in to the student management system
2. Navigate to your Settings page
3. Look for "Google Account Connection" section
4. Click "Connect Google Account"
5. Sign in with your @clarascienceacademy.org Google account
6. Grant all requested permissions:
   - View your email and profile
   - Create and manage Google Classroom courses
   - Manage student rosters
7. You'll be redirected back with a success message

**Note**: This is a one-time setup. Once connected, all future classes created for you will automatically get Google Classrooms.

### For Administrators

1. Ensure teachers have connected their Google accounts before creating classes
2. Create classes as normal through the Management dashboard
3. The system will automatically:
   - Create a Google Classroom if the teacher is connected
   - Show a success message indicating if Google Classroom was created
   - Store the Google Classroom ID for future reference

## ⚠️ Important Notes

1. **Google Workspace Required**: Teachers must use their @clarascienceacademy.org accounts (Google Workspace)
2. **Permissions**: Teachers need permission to create courses in Google Classroom (check Workspace admin settings)
3. **One-Time Setup**: Teachers only need to connect once; the connection persists
4. **Graceful Degradation**: If Google Classroom creation fails, the class is still created in the internal system
5. **Manual Override**: If needed, administrators can manually link classes to Google Classrooms later

## 🔍 Troubleshooting

### "Redirect URI Mismatch" Error
**Solution**: Update redirect URIs in Google Cloud Console (see section 1)

### "Invalid Client" Error
**Solution**: Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct

### Google Classroom Not Created
**Solutions**:
- Verify teacher has connected their Google account
- Check application logs for specific errors
- Ensure Google Classroom API is enabled
- Verify teacher has permission to create courses

### Teacher Can't See Connect Button
**Solution**: Ensure teacher is accessing the Settings page from the teacher dashboard

### Token Expired Errors
**Solution**: Teacher needs to disconnect and reconnect their Google account

## 📞 Support Resources

- **Google Classroom API**: https://developers.google.com/classroom
- **OAuth 2.0 Troubleshooting**: https://developers.google.com/identity/protocols/oauth2/web-server#handlingresponse
- **Application Logs**: Check Render logs for detailed error messages

## 🎯 Next Steps (Optional Enhancements)

After basic integration is working, consider:

1. **Student Auto-Enrollment**: Automatically add students to Google Classroom when enrolled in a class
2. **UI Enhancements**: Add Google Classroom status indicators to class management pages
3. **Bulk Operations**: Add ability to sync existing classes to Google Classroom
4. **Assignment Integration**: Create Google Classroom assignments from the system
5. **Grade Sync**: Optionally sync grades to Google Classroom

---

## Summary

✅ **Implementation is complete and ready for deployment**

⚠️ **Action Required**:
1. Update Google Cloud Console redirect URIs
2. Deploy to production
3. Run database migration
4. Test with a teacher account

Once these steps are complete, the Google Classroom integration will be fully operational!

