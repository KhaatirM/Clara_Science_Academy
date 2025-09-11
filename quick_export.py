#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    print("=" * 80)
    print("USER CREDENTIALS")
    print("=" * 80)
    for i, user in enumerate(users, 1):
        print(f"{i}. ID: {user.id} | Username: {user.username} | Role: {getattr(user, 'role', 'N/A')} | Hash: {user.password_hash}")
    print(f"\nTotal: {len(users)} users")
