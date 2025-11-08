#!/usr/bin/env python3
"""
Interactive script to create .env file for Clara Science Academy
Run this script to automatically generate your .env file with the correct values
"""

import os
import json
from pathlib import Path
from cryptography.fernet import Fernet

def main():
    print("=" * 60)
    print("Clara Science Academy - Environment Setup")
    print("=" * 60)
    print()
    
    # Check if .env already exists
    env_file = Path(".env")
    if env_file.exists():
        response = input(".env file already exists. Overwrite? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Setup cancelled.")
            return
        print()
    
    # Generate encryption key
    print("Step 1: Generating encryption key...")
    encryption_key = Fernet.generate_key().decode()
    print(f"✓ Generated: {encryption_key}")
    print()
    
    # Find client_secret.json file
    print("Step 2: Looking for client_secret.json file...")
    client_secret_files = list(Path(".").glob("client_secret*.json"))
    
    if not client_secret_files:
        print("✗ No client_secret.json file found!")
        print("Please ensure your client_secret.json file is in the project directory.")
        return
    
    # Use the first client_secret file found
    client_secret_file = client_secret_files[0]
    print(f"✓ Found: {client_secret_file}")
    print()
    
    # Parse client_secret.json
    print("Step 3: Reading Google OAuth credentials...")
    try:
        with open(client_secret_file, 'r') as f:
            client_data = json.load(f)
        
        if 'web' in client_data:
            client_id = client_data['web']['client_id']
            client_secret = client_data['web']['client_secret']
        elif 'installed' in client_data:
            client_id = client_data['installed']['client_id']
            client_secret = client_data['installed']['client_secret']
        else:
            print("✗ Could not find 'web' or 'installed' section in client_secret.json")
            return
        
        print(f"✓ Client ID: {client_id[:50]}...")
        print(f"✓ Client Secret: {client_secret[:20]}...")
        print()
        
    except Exception as e:
        print(f"✗ Error reading client_secret.json: {e}")
        return
    
    # Create .env file
    print("Step 4: Creating .env file...")
    env_content = f"""# Clara Science Academy - Environment Variables
# Generated automatically by setup_env.py
# DO NOT commit this file to git!

# Encryption key for storing OAuth refresh tokens
ENCRYPTION_KEY={encryption_key}

# Google OAuth Configuration
GOOGLE_CLIENT_ID={client_id}
GOOGLE_CLIENT_SECRET={client_secret}

# Optional: Flask configuration
# SECRET_KEY=your-secret-key-here
# FLASK_DEBUG=True
"""
    
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        print("✓ .env file created successfully!")
        print()
        
    except Exception as e:
        print(f"✗ Error creating .env file: {e}")
        return
    
    # Verify
    print("Step 5: Verifying setup...")
    if Path(".env").exists():
        print("✓ .env file exists")
        
        # Try to load it
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            if os.getenv('ENCRYPTION_KEY'):
                print("✓ ENCRYPTION_KEY is set")
            else:
                print("✗ ENCRYPTION_KEY not found")
            
            if os.getenv('GOOGLE_CLIENT_ID'):
                print("✓ GOOGLE_CLIENT_ID is set")
            else:
                print("✗ GOOGLE_CLIENT_ID not found")
            
            if os.getenv('GOOGLE_CLIENT_SECRET'):
                print("✓ GOOGLE_CLIENT_SECRET is set")
            else:
                print("✗ GOOGLE_CLIENT_SECRET not found")
                
        except ImportError:
            print("⚠ python-dotenv not installed, but .env file is created")
            print("  The app will still work if you have python-dotenv in requirements.txt")
    
    print()
    print("=" * 60)
    print("Setup Complete! 🎉")
    print("=" * 60)
    print()
    print("Your .env file has been created with the following variables:")
    print("  • ENCRYPTION_KEY")
    print("  • GOOGLE_CLIENT_ID")
    print("  • GOOGLE_CLIENT_SECRET")
    print()
    print("You can now run your application:")
    print("  python app.py")
    print()
    print("Note: The .env file is automatically ignored by git for security.")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        print("Please check the error and try again.")

