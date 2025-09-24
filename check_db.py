#!/usr/bin/env python3
"""
Simple script to check database contents
"""

import sqlite3

def check_database():
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check users
        cursor.execute("SELECT username, role FROM user")
        users = cursor.fetchall()
        print(f"\nUsers in database ({len(users)} total):")
        for user in users:
            print(f"  - Username: {user[0]}, Role: {user[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database()
