#!/usr/bin/env python3
import re
import sys

import requests

BASE = "http://127.0.0.1:5000"
s = requests.Session()
r = s.get(f"{BASE}/login", timeout=10)
m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
if not m:
    print("no csrf", file=sys.stderr)
    sys.exit(1)
s.post(
    f"{BASE}/login",
    data={"username": "vmuhammad", "password": "ClaraDev2026!", "csrf_token": m.group(1)},
    allow_redirects=False,
    timeout=10,
)
for path in ["/api/spa/parents", "/api/spa/classes", "/api/spa/students"]:
    r = s.get(f"{BASE}{path}", timeout=10)
    print(path, r.status_code, r.text[:300])
