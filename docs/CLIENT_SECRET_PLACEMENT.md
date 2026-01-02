# Where to Place client_secret.json

## 📍 Exact Location

Place `client_secret.json` in the **root directory** of your project:

```
C:\Users\admin\Documents\Clara_science_app\client_secret.json
```

---

## 📂 Visual Directory Structure

```
C:\Users\admin\Documents\Clara_science_app\
│
├── 📄 client_secret.json  ← ⭐ PLACE IT HERE ⭐
│
├── 📄 app.py
├── 📄 config.py
├── 📄 authroutes.py
├── 📄 models.py
├── 📄 requirements.txt
├── 📄 .gitignore
│
├── 📄 add_google_workspace_email.py
├── 📄 populate_google_workspace_emails.py
│
├── 📁 templates/
│   ├── 📁 shared/
│   │   ├── login.html
│   │   └── ...
│   └── ...
│
├── 📁 static/
├── 📁 instance/
├── 📁 venv/
└── ...
```

---

## 🎯 How to Verify Correct Placement

### Method 1: Check in File Explorer

1. Open File Explorer
2. Navigate to: `C:\Users\admin\Documents\Clara_science_app\`
3. You should see `client_secret.json` in the **same folder** as:
   - `app.py`
   - `config.py`
   - `requirements.txt`

### Method 2: Check in VS Code / Cursor

In your file explorer sidebar, you should see:
```
CLARA_SCIENCE_APP
├── client_secret.json  ← Should be at root level
├── app.py
├── config.py
├── templates/
└── ...
```

### Method 3: Python Script

Run this to verify:

```python
import os

project_root = r"C:\Users\admin\Documents\Clara_science_app"
client_secret_path = os.path.join(project_root, "client_secret.json")

if os.path.exists(client_secret_path):
    print(f"✅ Found! File is at: {client_secret_path}")
    print(f"   File size: {os.path.getsize(client_secret_path)} bytes")
else:
    print(f"❌ Not found at: {client_secret_path}")
    print("   Please place client_secret.json in the project root directory.")
```

---

## 📥 How to Get client_secret.json

### Step 1: Go to Google Cloud Console
1. Visit: https://console.cloud.google.com/
2. Select your project
3. Go to: **APIs & Services → Credentials**

### Step 2: Find Your OAuth Client ID
Look for the one named "Clara Science Website" (or whatever you named it)

### Step 3: Download the JSON File
1. Click the **download icon** (⬇️) on the right side of your OAuth Client ID
2. This downloads a file like: `client_secret_123456789.apps.googleusercontent.com.json`
3. **Rename it to:** `client_secret.json`

### Step 4: Move to Project Root
1. Open File Explorer
2. Navigate to your downloads folder
3. Copy `client_secret.json`
4. Paste into: `C:\Users\admin\Documents\Clara_science_app\`

---

## ✅ What the File Contains

The `client_secret.json` file looks like this:

```json
{
  "web": {
    "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-your-secret-here",
    "redirect_uris": [
      "http://127.0.0.1:5000/auth/google/callback",
      "https://clarascienceacademy.org/auth/google/callback"
    ]
  }
}
```

**Important:**
- This file contains **sensitive credentials**
- Never commit it to Git (already in `.gitignore` ✅)
- Never share it publicly
- Keep it secure

---

## 🔐 Security Notes

### Already Protected ✅

The file is in `.gitignore`:
```gitignore
# Google OAuth Credentials
# IMPORTANT: Never commit client_secret.json to version control!
client_secret.json
google_credentials.json
*client_secret*.json
```

### What This Means

- ✅ Git will ignore this file
- ✅ Won't be committed to version control
- ✅ Won't be pushed to GitHub/GitLab
- ✅ Each environment needs its own copy

### For Production

On your production server (e.g., Render):
1. Upload `client_secret.json` manually
2. Or use environment variables instead:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

---

## 🚨 Common Mistakes

### ❌ Wrong: Placing in templates/ folder
```
Clara_science_app/
└── templates/
    └── client_secret.json  ← WRONG!
```

### ❌ Wrong: Placing in static/ folder
```
Clara_science_app/
└── static/
    └── client_secret.json  ← WRONG!
```

### ❌ Wrong: Placing in instance/ folder
```
Clara_science_app/
└── instance/
    └── client_secret.json  ← WRONG!
```

### ✅ Correct: Placing in root
```
Clara_science_app/
├── client_secret.json  ← CORRECT! ✅
├── app.py
└── config.py
```

---

## 🧪 Testing After Placement

### Quick Test

1. **Place the file**
2. **Run this Python script:**

```python
from config import Config
import os

# Check if file exists
file_path = Config.GOOGLE_CLIENT_SECRETS_FILE
print(f"Looking for file at: {file_path}")

if os.path.exists(file_path):
    print("✅ File found!")
    print(f"   Size: {os.path.getsize(file_path)} bytes")
    
    # Try to read it
    import json
    with open(file_path, 'r') as f:
        data = json.load(f)
        if 'web' in data:
            print("✅ File format is correct!")
            print(f"   Client ID: {data['web']['client_id'][:20]}...")
        else:
            print("❌ File format is incorrect!")
else:
    print("❌ File not found!")
    print("   Please place client_secret.json in the project root.")
```

3. **Expected output:**
```
Looking for file at: C:\Users\admin\Documents\Clara_science_app\client_secret.json
✅ File found!
   Size: 542 bytes
✅ File format is correct!
   Client ID: 123456789-abcdefgh...
```

---

## 📞 Still Need Help?

### If File Won't Download
1. Make sure you're signed in to Google Cloud Console
2. Make sure you created an OAuth 2.0 Client ID (not API Key)
3. Try a different browser
4. Check your downloads folder

### If File is in Wrong Format
- Should be JSON format
- Should start with `{"web":{`
- Should contain `client_id` and `client_secret`
- If it's XML or HTML, you downloaded the wrong thing

### If App Can't Find File
1. Check the exact path in File Explorer
2. Make sure it's named exactly `client_secret.json` (not `.json.txt`)
3. Check file permissions (should be readable)
4. Restart your Flask application after placing the file

---

## ✨ You're Almost Done!

Once you place `client_secret.json` in the root directory:

1. ✅ Run `python add_google_workspace_email.py`
2. ✅ Run `python populate_google_workspace_emails.py`
3. ✅ Start your app: `python app.py`
4. ✅ Go to: http://127.0.0.1:5000/login
5. ✅ Click "Sign in with Google"
6. ✅ Test it out!

**That's it!** 🎉

---

*Clara Science Academy - Google Workspace Setup*  
*File Placement Guide*

