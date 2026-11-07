#!/usr/bin/env python3
"""Upgrades the Render database to the Basic-256MB ($6/mo) plan."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()

RENDER_YAML = '''databases:
  - name: nyumbalink-db
    databaseName: nyumbalink
    user: nyumbalink
    plan: basic-256mb  # Upgraded to $6/mo plan

services:
  # ------------------------------------------------------------
  # DJANGO BACKEND (Web Service)
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
        value: "3.12.0"
      - key: WEB_CONCURRENCY
        value: "2"

  # ------------------------------------------------------------
  # REACT FRONTEND (Static Site)
  # ------------------------------------------------------------
  - type: web
    name: nyumbalink-frontend
    runtime: static
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

(ROOT / "render.yaml").write_text(RENDER_YAML.strip() + "\n", encoding="utf-8")
print("✅ Updated render.yaml: Database plan set to 'basic-256mb' ($6/mo)")

# Commit and push
print("\n🚀 Pushing upgrade to GitHub...")
subprocess.run(["git", "add", "render.yaml"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Upgrade database to basic-256mb plan"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 DATABASE UPGRADE DEPLOYED TO GITHUB!
==================================================

Next steps in your Render Dashboard:

1. Go back to the Blueprint sync page.
2. Click "Retry" (or "Sync").
3. Render will now provision a Paid Database (no free-tier limit!) 
   and your Backend/Frontend will proceed with their builds.

--------------------------------------------------
⚠️ FINAL STEP: ENABLE POSTGIS
--------------------------------------------------
Once the database is created (look for the green "Available" status):

1. Click on the 'nyumbalink-db' in Render.
2. Go to the 'Connect' tab.
3. Copy the 'PSQL Command' (it looks like: PGPASSWORD=... psql -h ...).
4. Paste it into your local terminal and hit Enter.
5. Run this exact SQL command:

    CREATE EXTENSION postgis;

6. Type '\q' to exit.
7. Once PostGIS is installed, you can manually trigger a redeploy of 
   the backend so it can successfully run its database migrations.
==================================================
""")