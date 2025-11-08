# Google Classroom Integration - Implementation Summary

## Overview
This document summarizes the complete Google Classroom integration implemented in the Clara Science Academy Student Management System. The integration allows teachers to connect their Google accounts and automatically creates Google Classrooms when administrators add new classes to the system.

## What Was Implemented

### 1. Database Models (models.py)
- **User Model**: Added `_google_refresh_token` field (encrypted) to store teacher's Google OAuth refresh token
  - Property getter/setter automatically encrypts/decrypts the token using Fernet encryption
- **Class Model**: Added `google_classroom_id` field to link internal classes with Google Classroom courses

### 2. Configuration (config.py)
- Added `ENCRYPTION_KEY` for secure storage of refresh tokens
- Added `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from your existing Google Cloud project
- Updated `GOOGLE_CLIENT_SECRETS_FILE` path to point to your actual client secret file

### 3. Dependencies (requirements.txt)
- Added `cryptography` for secure token encryption
- Added `requests` for OAuth token refresh calls
- Existing packages (`google-auth-oauthlib`, `google-api-python-client`) are already in place

### 4. Database Migration (migrations_scripts/add_google_classroom_fields.py)
- Created and executed migration script to add new columns to the database
- Migration is SQLite-compatible and has been successfully run

### 5. Google Classroom Service Helper (google_classroom_service.py)
A new utility module providing:
- `get_google_service(user)`: Builds authenticated Google Classroom API service
- `create_google_classroom(service, class_name, ...)`: Creates a new Google Classroom
- `get_classroom_info(service, classroom_id)`: Retrieves classroom information
- `add_student_to_classroom(service, classroom_id, student_email)`: Adds students to classrooms
- `list_user_classrooms(service)`: Lists all classrooms for a user

### 6. Teacher Settings Routes (teacher_routes/settings.py)
Three new routes for Google account management:
- **`/teacher/settings/google-account/connect`**: Initiates OAuth flow to connect Google account
- **`/teacher/settings/google-account/callback`**: Handles OAuth callback and stores refresh token
- **`/teacher/settings/google-account/disconnect`**: Removes Google account connection

### 7. Automatic Classroom Creation (managementroutes.py)
Enhanced the `add_class` route to automatically:
1. Check if the assigned teacher has connected their Google account
2. Build an authenticated Google Classroom API service using their refresh token
3. Create a new Google Classroom with the class name, subject, and description
4. Store the Google Classroom ID in the database
5. Provide appropriate feedback to the administrator

## How It Works

### Teacher Setup (One-Time)
1. Teacher logs into the system
2. Navigates to their Settings page
3. Clicks "Connect Google Account" button
4. Grants permission to the app (requires consent for Classroom API access)
5. System securely stores encrypted refresh token

### Automatic Classroom Creation
When an administrator creates a new class:
1. System checks if the assigned teacher has connected their Google account
2. If yes:
   - Uses teacher's refresh token to get a fresh access token
   - Creates Google Classroom with class details
   - Stores the Google Classroom ID
   - Shows success message: "Class created and linked to Google Classroom!"
3. If no:
   - Creates the class in the internal system only
   - Shows info message: "Class created. Teacher needs to connect Google account for Classroom integration."

## Security Features

1. **Encrypted Token Storage**: Refresh tokens are encrypted using Fernet (symmetric encryption) before being stored in the database
2. **OAuth 2.0 Flow**: Standard OAuth 2.0 authorization code flow with PKCE
3. **Offline Access**: `access_type='offline'` ensures we get refresh tokens
4. **Forced Consent**: `prompt='consent'` ensures users always see what permissions they're granting
5. **State Validation**: OAuth state parameter prevents CSRF attacks

## Important Configuration Notes

### Google Cloud Console Setup Required
Your Google Cloud Project needs the following OAuth redirect URIs configured:

**Development:**
```
http://localhost:5000/teacher/settings/google-account/callback
http://127.0.0.1:5000/teacher/settings/google-account/callback
```

**Production:**
```
https://csastudentmanagement.onrender.com/teacher/settings/google-account/callback
https://www.clarascienceacademy.org/teacher/settings/google-account/callback
```

### Required Google API Scopes
The following scopes are requested during OAuth:
- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/userinfo.profile`
- `openid`
- `https://www.googleapis.com/auth/classroom.courses` (Create/manage courses)
- `https://www.googleapis.com/auth/classroom.rosters` (Manage student rosters)

### Environment Variables (Recommended for Production)
**REQUIRED** environment variables for production:

```bash
ENCRYPTION_KEY=<your-generated-key>
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
```

**To obtain these values:**
1. Generate ENCRYPTION_KEY: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Get CLIENT_ID and SECRET from your `client_secret.json` file

## Usage Instructions

### For Teachers
1. Log in to the system
2. Go to Settings (typically a gear icon or Settings link)
3. Look for "Google Account Connection" section
4. Click "Connect Google Account"
5. Sign in with your Google Workspace account (@clarascienceacademy.org)
6. Grant all requested permissions
7. You'll be redirected back to Settings with a success message

### For Administrators
1. Before creating classes, ensure teachers have connected their Google accounts
2. Create classes as usual through Management > Classes > Add New Class
3. System will automatically create Google Classrooms for classes where the teacher is connected
4. Success messages will indicate whether Google Classroom was created

## Future Enhancements (Optional)

Consider implementing these features in the future:

1. **Student Enrollment Sync**: Automatically add students to Google Classroom when they enroll in a class
2. **Assignment Sync**: Create Google Classroom assignments when creating assignments in the system
3. **Grade Sync**: Optionally sync grades back to Google Classroom
4. **Batch Operations**: Sync existing classes to Google Classroom
5. **Teacher Dashboard**: Show Google Classroom status for each class
6. **Reconnection Reminders**: Notify teachers if their token expires or becomes invalid

## Troubleshooting

### Teacher Can't Connect Google Account
- Verify OAuth redirect URIs are configured in Google Cloud Console
- Check that the client secret file exists and is accessible
- Ensure teacher is using their @clarascienceacademy.org account

### Google Classroom Not Created
- Verify teacher has connected their Google account (check Settings page)
- Check application logs for specific error messages
- Ensure teacher has permission to create courses in Google Classroom
- Verify Google Classroom API is enabled in Google Cloud Console

### Token Refresh Failures
- Teachers may need to reconnect their account if tokens become invalid
- Check that ENCRYPTION_KEY hasn't changed (would invalidate all stored tokens)
- Verify client ID and secret are correct

## Testing Recommendations

1. **Connect a Teacher Account**: Test the OAuth flow with a real teacher account
2. **Create a Test Class**: Create a class assigned to the connected teacher
3. **Verify Google Classroom**: Check that the classroom appears in Google Classroom
4. **Test Disconnection**: Test the disconnect feature and verify token is removed
5. **Test Without Connection**: Create a class for a teacher without Google connection

## Files Modified

1. `requirements.txt` - Added cryptography and requests
2. `config.py` - Added Google credentials and encryption key
3. `models.py` - Added google_refresh_token to User, google_classroom_id to Class
4. `migrations_scripts/add_google_classroom_fields.py` - New migration script (executed)
5. `google_classroom_service.py` - New helper module
6. `teacher_routes/settings.py` - Added OAuth routes
7. `managementroutes.py` - Enhanced add_class route with automation

## Security Recommendations

1. **Move Secrets to Environment Variables**: In production, use environment variables instead of hardcoded secrets
2. **Use HTTPS**: Ensure all OAuth flows use HTTPS in production
3. **Token Rotation**: Consider implementing periodic token refresh or reconnection prompts
4. **Audit Logging**: Add logging for all Google Classroom operations for security auditing
5. **Rate Limiting**: Implement rate limiting on OAuth endpoints to prevent abuse

## Notes

- The implementation uses SQLite in development and PostgreSQL in production
- The migration script is database-agnostic and works with both
- Google Classroom API has rate limits - be mindful when creating many classes
- Teachers must be Google Workspace users to use this feature
- The system gracefully handles cases where Google Classroom creation fails

## Support

If you encounter any issues or need modifications, refer to:
- Google Classroom API Documentation: https://developers.google.com/classroom
- Google OAuth 2.0 Documentation: https://developers.google.com/identity/protocols/oauth2
- Python Google API Client: https://github.com/googleapis/google-api-python-client

