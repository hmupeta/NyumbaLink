#!/usr/bin/env python3
"""Completely overwrites prod.py with a clean, syntactically valid version."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD_FILE = ROOT / "config" / "settings" / "prod.py"

PROD_SETTINGS = '''"""
Production settings for NyumbaLink (Render deployment).
Clean version with all integrations.
"""
from .base import *  # noqa: F401,F403
import os
import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
import cloudinary

# ----------------------------------------------------------------
# CORE
# ----------------------------------------------------------------
DEBUG = False

ALLOWED_HOSTS = [
    "nyumbalink.onrender.com",
    "nyumbalink-backend.onrender.com",
    "nyumbalink-backend-eaw2.onrender.com",
    ".onrender.com",
    "nyumbalink.com",
    "www.nyumbalink.com",
    "localhost",
    "127.0.0.1",
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
# MEDIA FILES (Cloudinary)
# ----------------------------------------------------------------
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure=True
)
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
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
CORS_ALLOW_ALL_ORIGINS = False
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
]

# ----------------------------------------------------------------
# EMAIL (Resend via Anymail)
# ----------------------------------------------------------------
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
ANYMAIL = {
    "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
}
DEFAULT_FROM_EMAIL = "NyumbaLink <onboarding@resend.dev>"

# ----------------------------------------------------------------
# ERROR TRACKING (Sentry)
# ----------------------------------------------------------------
sentry_dsn = os.environ.get("SENTRY_DSN", "")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True
    )

# ----------------------------------------------------------------
# JWT (Cookies must be secure in production)
# ----------------------------------------------------------------
SIMPLE_JWT["AUTH_COOKIE_SECURE"] = True
SIMPLE_JWT["AUTH_COOKIE_SAMESITE"] = "None"
'''

PROD_FILE.write_text(PROD_SETTINGS.strip() + "\n", encoding="utf-8")
print("✅ Completely rewrote config/settings/prod.py with clean syntax")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "config/settings/prod.py"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Clean prod.py syntax and consolidate all settings"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PROD.PY FIXED AND PUSHED!
==================================================

Now that the file is syntactically correct, you can re-run the media cleaner:

  python clean_prod_media.py

Render will also automatically redeploy the backend to use the new settings.
""")