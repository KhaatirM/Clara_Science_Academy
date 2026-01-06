# Google OAuth Quick Start - TL;DR

## ⚡ Quick Setup (5 Minutes)

### 1. Google Cloud Console (3 minutes)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **Create OAuth Client ID:**
   - APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
   - Type: Web application
   - Name: Clara Science Website
   - **Redirect URIs (IMPORTANT!):**
     ```
     http://127.0.0.1:5000/auth/google/callback
     https://your-domain.com/auth/google/callback
     ```
3. **Download `client_secret.json`**
4. **Set OAuth consent screen to "Internal"** (APIs & Services → OAuth consent screen)

### 2. Put client_secret.json in Project Root (30 seconds)
```
Clara_science_app/
├── client_secret.json  ← Place here
├── app.py
└── ...
```

### 3. Update User Emails (2 minutes)
Make sure user emails in your database match their Google Workspace emails:

```python
# Quick script to update one user
from app import db
from models import User

user = User.query.filter_by(username='john.doe').first()
user.email = 'john.doe@yourdomain.org'  # Their Google Workspace email
db.session.commit()
```

### 4. Test It!
1. Start app: `python app.py`
2. Go to `http://127.0.0.1:5000/login`
3. Click "Sign in with Google"
4. ✅ Done!

---

## 🔒 Security Reminder

✅ **ALREADY DONE:**
- ✅ `client_secret.json` in `.gitignore`
- ✅ OAuth routes implemented
- ✅ Email verification active
- ✅ Activity logging enabled
- ✅ CSRF protection included

⚠️ **BEFORE PRODUCTION:**
- [ ] Change OAuth consent screen to "Internal"
- [ ] Update all user emails to match Google Workspace
- [ ] Set production redirect URI in Google Cloud
- [ ] Remove or comment out line 587 in `authroutes.py`:
  ```python
  # REMOVE THIS LINE IN PRODUCTION:
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
  ```
- [ ] Verify HTTPS is enabled

---

## 🚨 Common Issues

**"Your Google Account is not associated..."**  
→ This is CORRECT! Update user's email in database to match their Google account.

**"Invalid redirect URI"**  
→ Check Google Cloud Console redirect URIs match EXACTLY (no typos, trailing slashes, or wrong protocols).

**Button doesn't show**  
→ Hard refresh (Ctrl+F5) or clear cache.

**"Access blocked"**  
→ Set OAuth consent screen to "Internal" in Google Cloud Console.

---

## 📚 Full Documentation

See `GOOGLE_OAUTH_SETUP_GUIDE.md` for complete details, troubleshooting, and FAQ.

---

**Ready to go!** Your Clara Science Academy now supports Google Workspace authentication. 🎉

