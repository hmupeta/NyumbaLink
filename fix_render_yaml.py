#!/usr/bin/env python3
"""Fixes render.yaml by removing the invalid 'plan' field from the static site."""
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
    # plan: free  <-- REMOVED: Static sites do not use compute plans
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
print("✅ Updated render.yaml (removed invalid plan field from frontend)")

# Commit and push
print("\n🚀 Pushing fix to GitHub...")
subprocess.run(["git", "add", "render.yaml"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Remove invalid plan field from static site"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX DEPLOYED TO GITHUB!
==================================================

Go back to your Render Dashboard, click 'Retry', and 
the Blueprint should now validate successfully.

Render will provision:
  - 1 PostgreSQL Database (Free)
  - 1 Python Web Service (Free)
  - 1 Static Site (Free)

The build will take 5-10 minutes because it compiles GDAL.
""")