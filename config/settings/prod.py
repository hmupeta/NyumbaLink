"""
Production settings for NyumbaLink (Render deployment).
"""
from .base import *  # noqa: F401,F403
import os
import dj_database_url

# ----------------------------------------------------------------
# CORE
# ----------------------------------------------------------------
DEBUG = False

# Allow Render's auto-generated hostnames and your custom domain
ALLOWED_HOSTS = [
    "nyumbalink.onrender.com",
    "nyumbalink-backend.onrender.com",
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
