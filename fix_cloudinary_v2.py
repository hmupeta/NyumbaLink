#!/usr/bin/env python3
"""Fixes Cloudinary configuration for Django 5.1+ using STORAGES."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD_FILE = ROOT / "config" / "settings" / "prod.py"

text = PROD_FILE.read_text(encoding="utf-8")

# Remove old deprecated config
import re
text = re.sub(r"# -*\n# CLOUDINARY MEDIA STORAGE.*?MEDIA_ROOT = BASE_DIR / \"media\"\n", "", text, flags=re.DOTALL)

# Add the modern STORAGES config for Django 4.2+ / 5.1+
modern_config = '''
# ----------------------------------------------------------------
# CLOUDINARY MEDIA STORAGE (Django 5.1+)
# ----------------------------------------------------------------
import os

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    'API_KEY': os.environ.get("CLOUDINARY_API_KEY", ""),
    'API_SECRET': os.environ.get("CLOUDINARY_API_SECRET", ""),
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
'''

text = text.strip() + "\n\n" + modern_config
PROD_FILE.write_text(text, encoding="utf-8")
print("✅ Patched prod.py: Migrated to modern STORAGES dictionary")

print("\n🚀 Pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Use Django 5.1 STORAGES dictionary for Cloudinary"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)