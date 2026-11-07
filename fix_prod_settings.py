#!/usr/bin/env python3
"""Replaces prod.py with a clean, working production settings file."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
PROD_FILE = ROOT / "config" / "settings" / "prod.py"

# ---------------------------------------------------------------- First: Diagnose
print("=" * 60)
print("DIAGNOSTIC: Current contents of prod.py")
print("=" * 60)
if PROD_FILE.exists():
    content = PROD_FILE.read_text(encoding="utf-8")
    lines = content.split("\n")
    found = False
    for i, line in enumerate(lines, 1):
        if "reference" in line.lower():
            print(f"  Line {i}: {line}")
            found = True
    if not found:
        print("  No 'reference' word found in prod.py.")
        print("  The error might be coming from a file imported by prod.py (like base.py).")
        print("\n  Current prod.py content:")
        print("-" * 60)
        print(content[:2000])
        print("-" * 60)
else:
    print("  prod.py does not exist yet.")

# ---------------------------------------------------------------- Second: Fix
PROD_SETTINGS = '''"""
Production settings for NyumbaLink.
"""
from .base import *  # noqa: F401,F403
import os
import dj_database_url

# ----------------------------------------------------------------
# CORE
# ----------------------------------------------------------------
DEBUG = False

# Allow Render's auto-generated hostname and your custom domain
ALLOWED_HOSTS = [
    "nyumbalink.onrender.com",
    "nyumbalink-backend.onrender.com",
    ".onrender.com",           # Any Render subdomain
    "nyumbalink.com",
    "www.nyumbalink.com",
    "localhost",
]

# ----------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------
DATABASES["default"] = dj_database_url.config(
    conn_max_age=600,
    ssl_require=True,
)

# ----------------------------------------------------------------
# STATIC FILES (WhiteNoise)
# ----------------------------------------------------------------
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ----------------------------------------------------------------
# MEDIA FILES
# ----------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ----------------------------------------------------------------
# SECURITY
# ----------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ----------------------------------------------------------------
# CORS (Allow the frontend to talk to the backend)
# ----------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True  # Restrict to your domain later
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "https://nyumbalink.onrender.com",
    "https://nyumbalink-backend.onrender.com",
    "https://nyumbalink.com",
    "https://www.nyumbalink.com",
]

# ----------------------------------------------------------------
# EMAIL (Use console backend on free tier)
# ----------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "alerts@nyumbalink.com"

# ----------------------------------------------------------------
# JWT (Cookies must be secure in production)
# ----------------------------------------------------------------
SIMPLE_JWT["AUTH_COOKIE_SECURE"] = True
SIMPLE_JWT["AUTH_COOKIE_SAMESITE"] = "None"
'''

PROD_FILE.parent.mkdir(parents=True, exist_ok=True)
PROD_FILE.write_text(PROD_SETTINGS.strip() + "\n", encoding="utf-8")
print("\n" + "=" * 60)
print("FIX APPLIED")
print("=" * 60)
print(f"Replaced {PROD_FILE.relative_to(ROOT)} with clean production settings.")

# ---------------------------------------------------------------- Third: Verify
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

import subprocess
import sys

# Try to import the settings to check for errors
result = subprocess.run(
    [sys.executable, "-c",
     "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod'); "
     "import django; django.setup(); print('Settings loaded successfully!')"],
    capture_output=True,
    text=True,
    cwd=ROOT,
)

if result.returncode == 0:
    print("✅ Settings loaded successfully with no errors.")
else:
    print("❌ Settings failed to load. Error output:")
    print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

print("""
Next steps:
  1. If the verification said "Settings loaded successfully", you can commit and push to GitHub.
  2. If it failed, paste the error output above and I'll fix it.
""")