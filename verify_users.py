#!/usr/bin/env python3
"""
Simple verification that users exist in database
"""
import sqlite3
import os

def verify_users():
    """Verify users exist in database"""
    db_path = 'instance/app.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("SELECT id, username, role FROM user")
        users = cursor.fetchall()
        
        print(f"📊 Total users in database: {len(users)}")
        print("\n👥 Users found:")
        
        expected_users = ['director', 'admin', 'teacher', 'student', 'tech']
        found_users = []
        
        for user_id, username, role in users:
            print(f"   - ID: {user_id}, Username: {username}, Role: {role}")
            found_users.append(username)
        
        # Check if all expected users exist
        missing_users = set(expected_users) - set(found_users)
        if missing_users:
            print(f"\n❌ Missing users: {', '.join(missing_users)}")
            return False
        
        print(f"\n✅ All expected users found!")
        print("\n🔐 Login Credentials:")
        print("   All users have password: password123")
        print("\n🌐 Test the login at: http://localhost:5000")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    verify_users()
