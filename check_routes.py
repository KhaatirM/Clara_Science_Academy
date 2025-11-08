#!/usr/bin/env python3
"""
Script to list all registered Flask routes
Helps debug missing endpoint errors
"""

from app import create_app

app = create_app()

print("=" * 80)
print("REGISTERED FLASK ROUTES")
print("=" * 80)
print()

# Get all routes
routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'methods': ', '.join(rule.methods - {'HEAD', 'OPTIONS'}),
        'path': str(rule)
    })

# Sort by endpoint
routes.sort(key=lambda x: x['endpoint'])

# Filter for teacher routes
print("TEACHER ROUTES:")
print("-" * 80)
teacher_routes = [r for r in routes if r['endpoint'].startswith('teacher.')]
if teacher_routes:
    for route in teacher_routes:
        print(f"{route['endpoint']:<50} {route['methods']:<15} {route['path']}")
else:
    print("NO TEACHER ROUTES FOUND!")

print()
print("=" * 80)
print(f"Total routes: {len(routes)}")
print(f"Teacher routes: {len(teacher_routes)}")
print("=" * 80)
print()

# Specifically check for Google Classroom routes
print("CHECKING FOR GOOGLE CLASSROOM ROUTES:")
print("-" * 80)
google_routes = [r for r in routes if 'google' in r['endpoint'].lower()]
if google_routes:
    for route in google_routes:
        print(f"✓ {route['endpoint']}")
else:
    print("✗ NO GOOGLE CLASSROOM ROUTES FOUND!")
    print()
    print("This means the routes in teacher_routes/settings.py aren't loading.")
    print("Possible causes:")
    print("  1. Import error in settings.py")
    print("  2. Missing dependencies (google-auth-oauthlib)")
    print("  3. Old code still deployed on Render")

print()

