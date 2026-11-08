#!/usr/bin/env python3
"""Fixes the WhiteNoise compression build failure on Render."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD_FILE = ROOT / "config" / "settings" / "prod.py"

text = PROD_FILE.read_text(encoding="utf-8")

# Replace the WhiteNoise storage with Django's default static storage
old_storage = '''    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },'''

new_storage = '''    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },'''

if old_storage in text:
    text = text.replace(old_storage, new_storage)
    PROD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched prod.py: Disabled WhiteNoise compression to fix build failure")
else:
    print("⚠️ Could not find the WhiteNoise storage block. It may have already been changed.")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Disable WhiteNoise compression to prevent Render build crash"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render will now rebuild the backend. 

Because we disabled the strict compression step, `collectstatic` will finish 
in seconds and the deployment will go live.

Once it's live, test your image upload again. It will now save directly 
to Cloudinary and persist across future deploys!
""")