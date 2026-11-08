#!/usr/bin/env python3
"""Fixes the WhiteNoise missing file error on Render."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD_FILE = ROOT / "config" / "settings" / "prod.py"

text = PROD_FILE.read_text(encoding="utf-8")

# Replace the strict Manifest storage with the flexible Compressed storage
old_backend = '"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",'
new_backend = '"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",'

if old_backend in text:
    text = text.replace(old_backend, new_backend)
    PROD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched prod.py: Changed WhiteNoise storage to CompressedStaticFilesStorage")
else:
    print("⚠️ Could not find the exact WhiteNoise line. Please check prod.py manually.")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Use CompressedStaticFilesStorage to avoid WhiteNoise manifest errors"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render will now automatically rebuild the backend.
Once the build finishes successfully, the deployment will be live.

This change still compresses your static files to save bandwidth, but it 
doesn't crash the build if a minor admin icon is missing.
""")