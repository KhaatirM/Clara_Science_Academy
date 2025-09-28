# Password Management Scripts

These scripts allow you to see user passwords by resetting them to known values. Since original passwords are stored as hashes and cannot be recovered, these scripts set new passwords that you can see.

## 🚀 Quick Start

### Option 1: Same Password for All Users (Fastest)
```bash
python reset_and_show_passwords.py
```
**Result**: All users get password `password123`

### Option 2: Individual Passwords (Recommended)
```bash
python quick_individual_passwords.py
```
**Result**: Each user gets password `username123` (e.g., `admin123`, `teacher123`)

## 📋 Available Scripts

### 1. `reset_and_show_passwords.py` - Same Password for All
**Purpose**: Reset all users to the same password
**Usage**: `python reset_and_show_passwords.py`
**Result**: All users get password `password123`

### 2. `quick_individual_passwords.py` - Individual Passwords (Recommended)
**Purpose**: Give each user a unique password
**Usage**: `python quick_individual_passwords.py`
**Result**: Each user gets password `username123`

### 3. `show_passwords.py` - Custom Password for All
**Purpose**: Set all users to a custom password
**Usage**: 
```bash
python show_passwords.py
python show_passwords.py mypassword123
```

### 4. `individual_passwords.py` - Individual Passwords with Confirmation
**Purpose**: Set individual passwords with confirmation prompt
**Usage**: `python individual_passwords.py`
**Result**: Each user gets password `username123` (with confirmation)

### 5. `password_manager.py` - Advanced Management
**Purpose**: Complete password management tool
**Usage**:
```bash
python password_manager.py list                    # List all users
python password_manager.py reset user pass        # Reset specific user
python password_manager.py reset-all pass         # Reset all users
python password_manager.py create user pass role  # Create new user
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

### Step 3: Run Password Script
```bash
# Quick individual passwords (recommended)
python quick_individual_passwords.py

# Or same password for all
python reset_and_show_passwords.py
```

## 📊 Output Examples

### Individual Passwords Output:
```
================================================================================
USER CREDENTIALS WITH INDIVIDUAL PASSWORDS
================================================================================
Password format: username + '123'
================================================================================
ID: 1 | Username: admin | Password: admin123 | Role: Director
ID: 2 | Username: teacher1 | Password: teacher1123 | Role: Teacher
ID: 3 | Username: student1 | Password: student1123 | Role: Student

Total: 3 users - All passwords reset to username + '123'
```

### Same Password Output:
```
================================================================================
USER CREDENTIALS WITH VISIBLE PASSWORDS
================================================================================
All users now have password: password123
================================================================================
ID: 1 | Username: admin | Password: password123 | Role: Director
ID: 2 | Username: teacher1 | Password: password123 | Role: Teacher
ID: 3 | Username: student1 | Password: password123 | Role: Student

Total: 3 users - All passwords reset to: password123
```

## 🔒 Security Notes

### Important Security Considerations:
1. **Password Reset**: These scripts reset ALL user passwords
2. **Known Passwords**: After running, you'll know all user passwords
3. **Temporary Access**: Use these passwords to access accounts, then change them
4. **Secure Handling**: Treat the output as sensitive information

### Recommended Workflow:
1. **Run Script**: Use `quick_individual_passwords.py` to set known passwords
2. **Access Accounts**: Use the displayed passwords to log in
3. **Change Passwords**: Change passwords to secure values through the web interface
4. **Clean Up**: Delete any temporary files created

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
   **Solution**: The script doesn't need to create files for basic password reset

### Getting Help:
```bash
python password_manager.py help
```

## 📁 File Descriptions

- `reset_and_show_passwords.py` - Same password for all users (fastest)
- `quick_individual_passwords.py` - Individual passwords (recommended)
- `show_passwords.py` - Custom password for all users
- `individual_passwords.py` - Individual passwords with confirmation
- `password_manager.py` - Advanced password management
- `PASSWORD_SCRIPTS_README.md` - This documentation

## 🎯 Recommended Workflow

1. **Quick Access**: Use `quick_individual_passwords.py` to set known passwords
2. **Login**: Use the displayed passwords to access user accounts
3. **Change Passwords**: Change passwords to secure values through the web interface
4. **Clean Up**: Delete any temporary files after use

## ⚠️ Important Notes

- **Original passwords cannot be recovered** - they are stored as hashes
- **These scripts reset passwords** - all users will need to use the new passwords
- **Use responsibly** - ensure you have proper authorization
- **Change passwords after use** - don't leave accounts with known passwords

---

**Note**: These scripts are designed for administrative purposes only. Use responsibly and ensure you have proper authorization before resetting user passwords.
