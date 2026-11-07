#!/usr/bin/env python3
"""Fixes cross-site cookie and CORS issues for Render production."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()

# ---------------------------------------------------------------- 1. Fix Cookie SameSite
VIEWS_FILE = ROOT / "apps" / "accounts" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# Replace the hardcoded "Lax" with dynamic based on DEBUG
old_cookie = '''def _cookie_kwargs(max_age: int) -> dict:
    return {
        "max_age": max_age,
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
    }'''

new_cookie = '''def _cookie_kwargs(max_age: int) -> dict:
    return {
        "max_age": max_age,
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "None" if not settings.DEBUG else "Lax",
    }'''

if old_cookie in text:
    text = text.replace(old_cookie, new_cookie)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched apps/accounts/views.py: Fixed SameSite cookie policy for production")
else:
    print("⚠️ Could not find _cookie_kwargs in views.py. It may already be updated.")

# ---------------------------------------------------------------- 2. Fix CORS Settings
PROD_FILE = ROOT / "config" / "settings" / "prod.py"
text = PROD_FILE.read_text(encoding="utf-8")

old_cors = '''CORS_ALLOW_ALL_ORIGINS = True  # Restrict to your domain later
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "https://nyumbalink.onrender.com",
    "https://nyumbalink-backend.onrender.com",
    "https://nyumbalink.com",
    "https://www.nyumbalink.com",
]'''

new_cors = '''CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://nyumbalink-frontend-pbkm.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CSRF_TRUSTED_ORIGINS = [
    "https://nyumbalink-frontend-pbkm.onrender.com",
    "https://nyumbalink-backend-eaw2.onrender.com",
    "https://nyumbalink.com",
    "https://www.nyumbalink.com",
]'''

if old_cors in text:
    text = text.replace(old_cors, new_cors)
    PROD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched config/settings/prod.py: Fixed CORS allowed origins")
else:
    print("⚠️ Could not find the CORS settings block in prod.py. It may already be updated.")

# ---------------------------------------------------------------- 3. Push
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Cross-site cookies and CORS for Render"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render will automatically redeploy your Backend.

Once the backend says "Live":

1. Log out of the frontend (to clear the old Lax cookies).
2. Log back in.
3. Try creating a listing again. The authentication error should be gone!
""")