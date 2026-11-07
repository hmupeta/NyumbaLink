#!/usr/bin/env python3
"""Prepares NyumbaLink for GitHub and Render deployment."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

# ---------------------------------------------------------------- 1. .gitignore
GITIGNORE = """# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.sqlite3

# Django
.env
media/
staticfiles/

# Node
node_modules/
frontend/node_modules/
frontend/dist/
frontend/.env.local

# Tools
tools/

# OS
.DS_Store
Thumbs.db
"""

(ROOT / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
print("✅ Created/updated .gitignore")

# ---------------------------------------------------------------- 2. requirements.txt
REQUIREMENTS = """Django>=5.1,<5.2
djangorestframework>=3.15,<4.0
django-filter>=24.2
django-cors-headers>=4.3
drf-spectacular>=0.27
psycopg[binary]>=3.1
python-dotenv>=1.0
drf-nested-routers>=0.94
djangorestframework-simplejwt>=5.4
cryptography>=42.0
stripe>=7.0
mtnmomoapi>=0.0.7
basicauth>=0.4.2
Pillow>=10.0

# Production / Render Requirements
gunicorn>=21.0
whitenoise>=6.6
dj-database-url>=2.1
psycopg2-binary>=2.9
"""

(ROOT / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
print("✅ Updated requirements.txt with production packages")

# ---------------------------------------------------------------- 3. config/settings/prod.py
PROD_SETTINGS = '''"""
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
'''

(ROOT / "config" / "settings" / "prod.py").write_text(PROD_SETTINGS.strip() + "\n", encoding="utf-8")
print("✅ Overwrote config/settings/prod.py with clean production config")

# ---------------------------------------------------------------- 4. build.sh
BUILD_SH = '''#!/usr/bin/env bash
# build.sh - Runs on Render during deployment

# Exit immediately if any command fails
set -o errexit

# Install system dependencies for GeoDjango (GDAL/GEOS)
echo "Installing system dependencies..."
apt-get update && apt-get install -y gdal-bin libgdal-dev

# Install Python dependencies
echo "Installing Python requirements..."
pip install -r requirements.txt

# Collect static files for WhiteNoise
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Run migrations
echo "Running database migrations..."
python manage.py migrate
'''

build_file = ROOT / "build.sh"
build_file.write_text(BUILD_SH.strip() + "\n", encoding="utf-8")

# Make it executable if on Unix (does nothing harmful on Windows)
try:
    import stat
    build_file.chmod(build_file.stat().st_mode | stat.S_IEXEC)
except Exception:
    pass
print("✅ Created build.sh script for Render")

# ---------------------------------------------------------------- 5. Git Operations
def run_cmd(cmd: list[str], desc: str):
    print(f"  ⏳ {desc}...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        # Some git commands 'fail' benignly (e.g. remote already exists)
        if "already exists" in result.stderr or "nothing to commit" in result.stdout:
            print(f"     ℹ️  {desc} skipped (already done)")
        else:
            print(f"     ⚠️  {desc} output: {result.stderr.strip()}")
    else:
        print(f"     ✅ {desc}")

print("\n--------------------------------------------------")
print("🐙 PREPARING GIT REPOSITORY")
print("--------------------------------------------------")

run_cmd(["git", "init"], "Initializing Git repository")
run_cmd(["git", "add", "."], "Adding files to staging area")
run_cmd(["git", "commit", "-m", "Production: Prepare for Render deployment"], "Committing changes")
run_cmd(["git", "branch", "-M", "main"], "Renaming branch to 'main'")

# ---------------------------------------------------------------- 6. Final Instructions
print("""
==================================================
🎉 PREPARATION COMPLETE!
==================================================

Your code is now ready to be pushed to GitHub and 
deployed to Render.

Follow these steps:

1️⃣ PUSH TO GITHUB
Run these commands in your terminal (replace YOUR_USERNAME):

    git remote add origin https://github.com/YOUR_USERNAME/NyumbaLink.git
    git push -u origin main

*(If it says "remote origin already exists", run:)*
    git remote set-url origin https://github.com/YOUR_USERNAME/NyumbaLink.git
    git push -u origin main

--------------------------------------------------

2️⃣ DEPLOY POSTGRES ON RENDER
  a. Go to Render Dashboard -> New -> PostgreSQL
  b. Name it 'nyumbalink-db', select 'Free' tier.
  c. Once created, copy the 'PSQL Command' from the Info tab.
  d. Run it in your local terminal to connect.
  e. Execute: CREATE EXTENSION postgis;
  f. Exit the database connection.

--------------------------------------------------

3️⃣ DEPLOY BACKEND ON RENDER
  a. Dashboard -> New -> Web Service -> Connect GitHub repo.
  b. Name: nyumbalink-backend
  c. Build Command: ./build.sh
  d. Start Command: gunicorn config.wsgi:application
  e. Add Environment Variables:
     - DATABASE_URL (paste Internal Database URL from step 2)
     - SECRET_KEY (generate a long random string)
     - DJANGO_SETTINGS_MODULE (set to: config.settings.prod)
     - PYTHON_VERSION (set to: 3.12.0)
  f. Click 'Create Web Service' and wait for the build to finish.

--------------------------------------------------

4️⃣ DEPLOY FRONTEND ON RENDER
  a. Dashboard -> New -> Static Site -> Connect repo.
  b. Name: nyumbalink-frontend
  c. Root Directory: frontend
  d. Build Command: npm install && npm run build
  e. Publish Directory: dist
  f. Click 'Create Static Site'.

  🔴 CRITICAL: After it deploys, go to Settings -> Redirects/Rewrites:
      Source: /*
      Destination: /index.html
      Action: Rewrite
  (This prevents 404 errors when users refresh pages like /dashboard).

--------------------------------------------------

5️⃣ CONNECT THEM
  a. Go to your Frontend Static Site -> Environment.
  b. Add Variable: VITE_API_URL
  c. Value: https://nyumbalink-backend.onrender.com/api/v1
  d. Click 'Manual Deploy' -> 'Clear build cache & deploy'.

==================================================
""")