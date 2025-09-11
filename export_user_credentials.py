#!/usr/bin/env python3
"""
User Credentials Export Script
=============================

This script exports all user credentials (username, password, ID) from the database.
It's designed to be run on the Render shell under the webservice.

Usage:
    python export_user_credentials.py

Output:
    - Console output with all user credentials
    - Optional CSV file export
    - Optional JSON file export

Security Note:
    This script should only be run by authorized administrators.
    The output contains sensitive information and should be handled securely.
"""

import os
import sys
import csv
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from models import db, User
    from werkzeug.security import check_password_hash
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def export_user_credentials(output_format='console', filename=None):
    """
    Export all user credentials from the database.
    
    Args:
        output_format (str): Output format - 'console', 'csv', 'json', or 'all'
        filename (str): Optional filename for file exports
    """
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Query all users
            users = User.query.all()
            
            if not users:
                print("No users found in the database.")
                return
            
            # Prepare data
            user_data = []
            for user in users:
                user_info = {
                    'id': user.id,
                    'username': user.username,
                    'email': getattr(user, 'email', 'N/A'),
                    'role': getattr(user, 'role', 'N/A'),
                    'first_name': getattr(user, 'first_name', 'N/A'),
                    'last_name': getattr(user, 'last_name', 'N/A'),
                    'is_active': getattr(user, 'is_active', True),
                    'created_at': getattr(user, 'created_at', 'N/A'),
                    'last_login': getattr(user, 'last_login', 'N/A'),
                    'password_hash': user.password_hash,
                    'password_plaintext': 'ENCRYPTED'  # Passwords are hashed, not stored in plaintext
                }
                user_data.append(user_info)
            
            # Console output
            if output_format in ['console', 'all']:
                print("=" * 80)
                print("USER CREDENTIALS EXPORT")
                print("=" * 80)
                print(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Total Users: {len(user_data)}")
                print("=" * 80)
                
                for i, user in enumerate(user_data, 1):
                    print(f"\n{i}. USER ID: {user['id']}")
                    print(f"   Username: {user['username']}")
                    print(f"   Email: {user['email']}")
                    print(f"   Role: {user['role']}")
                    print(f"   Name: {user['first_name']} {user['last_name']}")
                    print(f"   Active: {user['is_active']}")
                    print(f"   Created: {user['created_at']}")
                    print(f"   Last Login: {user['last_login']}")
                    print(f"   Password Hash: {user['password_hash'][:50]}...")
                    print(f"   Password (Plaintext): {user['password_plaintext']}")
                    print("-" * 60)
            
            # CSV export
            if output_format in ['csv', 'all']:
                csv_filename = filename or f"user_credentials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['id', 'username', 'email', 'role', 'first_name', 'last_name', 
                                'is_active', 'created_at', 'last_login', 'password_hash', 'password_plaintext']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(user_data)
                print(f"\nCSV file exported: {csv_filename}")
            
            # JSON export
            if output_format in ['json', 'all']:
                json_filename = filename or f"user_credentials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(json_filename, 'w', encoding='utf-8') as jsonfile:
                    json.dump({
                        'export_info': {
                            'export_date': datetime.now().isoformat(),
                            'total_users': len(user_data),
                            'exported_by': 'admin_script'
                        },
                        'users': user_data
                    }, jsonfile, indent=2, default=str)
                print(f"JSON file exported: {json_filename}")
            
            print(f"\nExport completed successfully!")
            print(f"Total users exported: {len(user_data)}")
            
        except Exception as e:
            print(f"Error exporting user credentials: {e}")
            import traceback
            traceback.print_exc()

def show_help():
    """Show help information."""
    print("""
User Credentials Export Script
=============================

Usage:
    python export_user_credentials.py [format] [filename]

Arguments:
    format      Output format: console, csv, json, or all (default: console)
    filename    Optional filename for file exports (default: auto-generated)

Examples:
    python export_user_credentials.py
    python export_user_credentials.py console
    python export_user_credentials.py csv
    python export_user_credentials.py json
    python export_user_credentials.py all
    python export_user_credentials.py csv my_users.csv
    python export_user_credentials.py json users_backup.json

Formats:
    console     - Display results in console (default)
    csv         - Export to CSV file
    json        - Export to JSON file
    all         - Display in console AND export to both CSV and JSON

Security Note:
    This script exports sensitive information including password hashes.
    Handle the output files securely and delete them after use.
""")

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        return
    
    # Parse command line arguments
    output_format = 'console'
    filename = None
    
    if len(sys.argv) > 1:
        output_format = sys.argv[1]
    
    if len(sys.argv) > 2:
        filename = sys.argv[2]
    
    # Validate format
    valid_formats = ['console', 'csv', 'json', 'all']
    if output_format not in valid_formats:
        print(f"Error: Invalid format '{output_format}'. Valid formats: {', '.join(valid_formats)}")
        show_help()
        return
    
    # Run export
    export_user_credentials(output_format, filename)

if __name__ == '__main__':
    main()
