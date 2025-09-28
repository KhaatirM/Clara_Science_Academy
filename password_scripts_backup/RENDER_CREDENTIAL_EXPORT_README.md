# Render Credential Export Scripts

This directory contains scripts to export user credentials from your Flask application running on Render.

## 🚀 Quick Start

### Option 1: Quick Export (Recommended)
```bash
python quick_export.py
```

### Option 2: Detailed Export
```bash
python get_user_credentials.py
```

### Option 3: Full Management Suite
```bash
python admin_user_manager.py export
```

## 📋 Available Scripts

### 1. `quick_export.py`
**Purpose**: Fastest way to get all user credentials
**Usage**: `python quick_export.py`
**Output**: Simple list with ID, username, role, and password hash

### 2. `get_user_credentials.py`
**Purpose**: Detailed credential export with full user information
**Usage**: `python get_user_credentials.py`
**Output**: Comprehensive user details including email, names, activity status

### 3. `export_user_credentials.py`
**Purpose**: Advanced export with multiple output formats
**Usage**: 
```bash
python export_user_credentials.py console
python export_user_credentials.py csv
python export_user_credentials.py json
python export_user_credentials.py all
```

### 4. `admin_user_manager.py`
**Purpose**: Complete user management tool
**Usage**:
```bash
python admin_user_manager.py export          # Export credentials
python admin_user_manager.py list            # List all users
python admin_user_manager.py reset-password <user> <pass>  # Reset password
python admin_user_manager.py create <user> <pass> <role>   # Create user
```

## 🔧 How to Use on Render

### Step 1: Access Render Shell
1. Go to your Render dashboard
2. Select your web service
3. Click on "Shell" tab
4. Wait for the shell to load

### Step 2: Navigate to Project Directory
```bash
cd /opt/render/project/src
```

### Step 3: Run Export Script
```bash
# Quick export (recommended)
python quick_export.py

# Or detailed export
python get_user_credentials.py
```

### Step 4: Copy Results
- Copy the output from the terminal
- Save it to a secure file on your local machine
- Delete any temporary files created

## 📊 Output Examples

### Quick Export Output:
```
================================================================================
USER CREDENTIALS
================================================================================
1. ID: 1 | Username: admin | Role: Director | Hash: pbkdf2:sha256:260000$...
2. ID: 2 | Username: teacher1 | Role: Teacher | Hash: pbkdf2:sha256:260000$...
3. ID: 3 | Username: student1 | Role: Student | Hash: pbkdf2:sha256:260000$...

Total: 3 users
```

### Detailed Export Output:
```
================================================================================
USER CREDENTIALS EXPORT
================================================================================
Export Date: 2025-01-10 12:30:45
Total Users: 3
================================================================================

1. USER ID: 1
   Username: admin
   Email: admin@school.com
   Role: Director
   First Name: John
   Last Name: Doe
   Active: True
   Created: 2025-01-01 10:00:00
   Last Login: 2025-01-10 12:00:00
   Password Hash: pbkdf2:sha256:260000$...
------------------------------------------------------------
```

## 🔒 Security Notes

### Important Security Considerations:
1. **Password Hashes Only**: These scripts export password hashes, not plaintext passwords
2. **Secure Handling**: Treat the output as sensitive information
3. **Temporary Files**: Delete any CSV/JSON files created after use
4. **Access Control**: Only run these scripts if you have proper authorization

### Password Reset:
If you need to reset a user's password:
```bash
python admin_user_manager.py reset-password username newpassword123
```

### Create New User:
```bash
python admin_user_manager.py create newuser password123 Teacher
```

## 🛠️ Troubleshooting

### Common Issues:

1. **Import Error**: 
   ```
   Error importing modules: No module named 'app'
   ```
   **Solution**: Make sure you're in the project root directory (`/opt/render/project/src`)

2. **Database Connection Error**:
   ```
   Error: Database connection failed
   ```
   **Solution**: Check that your database is running and accessible

3. **Permission Denied**:
   ```
   Permission denied: cannot open file
   ```
   **Solution**: The script doesn't need to create files for basic export

### Getting Help:
```bash
python admin_user_manager.py help
```

## 📁 File Descriptions

- `quick_export.py` - Fastest credential export
- `get_user_credentials.py` - Detailed credential export  
- `export_user_credentials.py` - Advanced export with multiple formats
- `admin_user_manager.py` - Complete user management suite
- `RENDER_CREDENTIAL_EXPORT_README.md` - This documentation

## 🎯 Recommended Workflow

1. **Quick Check**: Use `quick_export.py` for a fast overview
2. **Detailed Export**: Use `get_user_credentials.py` for full details
3. **Management**: Use `admin_user_manager.py` for user management tasks
4. **Cleanup**: Delete any temporary files after use

---

**Note**: These scripts are designed for administrative purposes only. Use responsibly and ensure you have proper authorization before accessing user credentials.
