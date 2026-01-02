# Environment Variables Setup Guide

## 🔐 Security First!

The application now uses **environment variables** for all sensitive credentials. This is more secure than hardcoding values.

---

## 📋 Required Environment Variables

### 1. ENCRYPTION_KEY

Used to encrypt Google OAuth refresh tokens in the database.

**Generate a new key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output: `ATGS8V3TekRuS_GYRx2A0vQi7dxuairOg1H6yQ7yZw0=`

### 2. GOOGLE_CLIENT_ID

Your Google OAuth Client ID.

**Find in your `client_secret.json` file:**
```json
{
  "web": {
    "client_id": "123456789-abc123xyz.apps.googleusercontent.com",
    ...
  }
}
```

### 3. GOOGLE_CLIENT_SECRET

Your Google OAuth Client Secret.

**Find in your `client_secret.json` file:**
```json
{
  "web": {
    ...
    "client_secret": "GOCSPX-abc123xyz",
    ...
  }
}
```

---

## 🖥️ Local Development Setup

### Option 1: Using .env file (Recommended)

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your actual values:
   ```bash
   ENCRYPTION_KEY=<paste-your-generated-key>
   GOOGLE_CLIENT_ID=<paste-from-client_secret.json>
   GOOGLE_CLIENT_SECRET=<paste-from-client_secret.json>
   ```

3. The app will automatically load these when it runs

### Option 2: Export in terminal

```bash
export ENCRYPTION_KEY="your-key-here"
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

**Note**: These only last for the current terminal session.

---

## ☁️ Production Setup (Render)

### Via Render Dashboard

1. Go to your Render service dashboard
2. Click **"Environment"** in the left sidebar
3. Add each variable:
   - **Key**: `ENCRYPTION_KEY`
   - **Value**: Your generated encryption key
   - Click **"Add Environment Variable"**

4. Repeat for:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

5. Click **"Save Changes"**
6. Your service will automatically redeploy

### Via Render CLI

```bash
render env set ENCRYPTION_KEY="your-key"
render env set GOOGLE_CLIENT_ID="your-client-id"
render env set GOOGLE_CLIENT_SECRET="your-client-secret"
```

---

## 🧪 Verify Setup

### Check if variables are loaded:

```python
python -c "import os; print('ENCRYPTION_KEY:', 'SET' if os.getenv('ENCRYPTION_KEY') else 'NOT SET')"
```

### Test in Python shell:

```python
from config import Config

print("ENCRYPTION_KEY:", "SET" if Config.ENCRYPTION_KEY else "NOT SET")
print("GOOGLE_CLIENT_ID:", "SET" if Config.GOOGLE_CLIENT_ID else "NOT SET")
print("GOOGLE_CLIENT_SECRET:", "SET" if Config.GOOGLE_CLIENT_SECRET else "NOT SET")
```

---

## ⚠️ Important Security Notes

1. **NEVER** commit `.env` file to git
2. **NEVER** commit `client_secret.json` to git
3. **NEVER** hardcode secrets in code
4. **ALWAYS** use environment variables for production
5. **ROTATE** keys periodically for security

---

## 🔄 Rotating Keys

If you need to change your encryption key:

1. **WARNING**: Changing `ENCRYPTION_KEY` will invalidate all stored refresh tokens
2. Teachers will need to reconnect their Google accounts
3. To rotate safely:
   - Generate new key
   - Update environment variable
   - Notify teachers to reconnect their accounts
   - Old tokens will fail gracefully with clear error messages

---

## 📝 Quick Reference

| Variable | Purpose | Where to Get |
|----------|---------|--------------|
| `ENCRYPTION_KEY` | Encrypt OAuth tokens | Generate with Fernet |
| `GOOGLE_CLIENT_ID` | Google OAuth | client_secret.json |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | client_secret.json |

---

## 🆘 Troubleshooting

### Error: "ENCRYPTION_KEY is None"
**Solution**: Set the `ENCRYPTION_KEY` environment variable

### Error: "GOOGLE_CLIENT_ID is None"
**Solution**: Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables

### OAuth redirect fails
**Solution**: Verify redirect URIs in Google Cloud Console match your deployment URL

### Teachers can't connect Google accounts
**Solution**: 
1. Check environment variables are set
2. Verify `client_secret.json` file exists
3. Check application logs for specific errors

---

## 📞 Support

If you're still having issues:
1. Check Render logs for specific error messages
2. Verify all three environment variables are set
3. Ensure values don't have extra spaces or quotes
4. Try regenerating the encryption key

**The app will fail gracefully if environment variables are missing with clear error messages.**

