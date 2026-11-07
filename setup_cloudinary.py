#!/usr/bin/env python3
"""Installs and configures Cloudinary for production media storage."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import re

ROOT = Path.cwd()

# ---------------------------------------------------------------- 1. Install Packages Locally
print("📦 Installing Cloudinary packages locally...")
subprocess.run([sys.executable, "-m", "pip", "install", "cloudinary", "django-cloudinary-storage"], check=True)

# ---------------------------------------------------------------- 2. Update requirements.txt
REQ_FILE = ROOT / "requirements.txt"
text = REQ_FILE.read_text(encoding="utf-8")
if "cloudinary" not in text:
    text += "\ncloudinary>=1.36\ndjango-cloudinary-storage>=0.3.0\n"
    REQ_FILE.write_text(text, encoding="utf-8")
    print("✅ Updated requirements.txt")

# ---------------------------------------------------------------- 3. Patch base.py (INSTALLED_APPS)
BASE_FILE = ROOT / "config" / "settings" / "base.py"
text = BASE_FILE.read_text(encoding="utf-8")
if "cloudinary_storage" not in text:
    # Cloudinary storage must be placed before django.contrib.staticfiles
    text = text.replace(
        'INSTALLED_APPS = [\n',
        'INSTALLED_APPS = [\n    "cloudinary_storage",\n    "cloudinary",\n'
    )
    BASE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched base.py: Added Cloudinary to INSTALLED_APPS")

# ---------------------------------------------------------------- 4. Patch prod.py (Storage Config)
PROD_FILE = ROOT / "config" / "settings" / "prod.py"
text = PROD_FILE.read_text(encoding="utf-8")

if "DEFAULT_FILE_STORAGE" not in text:
    cloudinary_config = '''
# ----------------------------------------------------------------
# CLOUDINARY MEDIA STORAGE (Production)
# ----------------------------------------------------------------
import cloudinary
import os

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure=True
)

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
'''
    text += cloudinary_config
    PROD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched prod.py: Configured Cloudinary as the default storage backend")

# ---------------------------------------------------------------- 5. Push to GitHub
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Configure Cloudinary for persistent media storage"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 CLOUDINARY CONFIGURED AND PUSHED!
==================================================

To finish the setup, you need to add your Cloudinary credentials to Render:

1. Go to https://cloudinary.com and sign up for a free account.
2. On your Cloudinary Dashboard, you will see:
   - Cloud Name
   - API Key
   - API Secret
3. Go to your Render Backend Service -> Environment.
4. Add these three Environment Variables:
   - CLOUDINARY_CLOUD_NAME = (your cloud name)
   - CLOUDINARY_API_KEY = (your api key)
   - CLOUDINARY_API_SECRET = (your api secret)

Render will automatically redeploy the backend. 
Once it's live, all new images you upload will be securely stored in the cloud 
and will NEVER disappear when you redeploy!
""")