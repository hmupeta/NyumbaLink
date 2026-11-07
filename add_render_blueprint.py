#!/usr/bin/env python3
"""Generates render.yaml for one-click Blueprint deployment."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()

RENDER_YAML = '''databases:
  - name: nyumbalink-db
    databaseName: nyumbalink
    user: nyumbalink
    plan: free

services:
  # ------------------------------------------------------------
  # DJANGO BACKEND
  # ------------------------------------------------------------
  - type: web
    name: nyumbalink-backend
    runtime: python
    plan: free
    buildCommand: "./build.sh"
    startCommand: "gunicorn config.wsgi:application"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: nyumbalink-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: DJANGO_SETTINGS_MODULE
        value: config.settings.prod
      - key: PYTHON_VERSION
        value: 3.12.0
      - key: WEB_CONCURRENCY
        value: 2

  # ------------------------------------------------------------
  # REACT FRONTEND
  # ------------------------------------------------------------
  - type: web
    name: nyumbalink-frontend
    runtime: static
    plan: free
    rootDir: frontend
    buildCommand: "npm install && npm run build"
    staticPublishPath: dist
    envVars:
      - key: VITE_API_URL
        value: https://nyumbalink-backend.onrender.com/api/v1
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
'''

(ROOT / "render.yaml").write_text(RENDER_YAML, encoding="utf-8")
print("✅ Created render.yaml")

# Ensure build.sh exists (in case the previous script wasn't run)
build_file = ROOT / "build.sh"
if not build_file.exists():
    BUILD_SH = '''#!/usr/bin/env bash
set -o errexit
apt-get update && apt-get install -y gdal-bin libgdal-dev
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
'''
    build_file.write_text(BUILD_SH, encoding="utf-8")
    print("✅ Created build.sh")

# Git add, commit, and push
print("\n🚀 Pushing to GitHub...")
subprocess.run(["git", "add", "render.yaml", "build.sh"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Add Render Blueprint and build script"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 RENDER.YAML DEPLOYED TO GITHUB!
==================================================

Now go back to your Render Dashboard (the screen in your screenshot) 
and follow these steps:

1. Click the "Retry" button at the bottom.
2. Render will now detect your render.yaml file.
3. It will ask you to confirm the creation of:
   - 1 PostgreSQL Database (Free)
   - 1 Python Web Service (Backend)
   - 1 Static Site (Frontend)
4. Click "Apply" or "Deploy Blueprint".

Render will now automatically:
  • Install GDAL for your Django backend.
  • Run migrations.
  • Build your React app.
  • Set up the routing so React doesn't 404 on refresh.

The first build will take about 5-10 minutes because it has to compile
GDAL and install all your dependencies from scratch.

--------------------------------------------------
⚠️ IMPORTANT: DATABASE EXTENSION
--------------------------------------------------
Once the database is deployed, you MUST enable PostGIS. 
Go to your `nyumbalink-db` dashboard in Render -> "Connect" tab, 
copy the PSQL command, run it in your terminal, and execute:

    CREATE EXTENSION postgis;
""")