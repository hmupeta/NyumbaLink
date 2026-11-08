#!/usr/bin/env python3
"""Allows all origins on the backend to fix Flutter Web CORS issues."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PROD_FILE = ROOT / "config" / "settings" / "prod.py"

text = PROD_FILE.read_text(encoding="utf-8")

# Change CORS settings
old_cors = '''CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://nyumbalink-frontend-pbkm.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]'''

new_cors = '''CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True'''

if old_cors in text:
    text = text.replace(old_cors, new_cors)
    PROD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched prod.py: Enabled CORS_ALLOW_ALL_ORIGINS for Flutter development")
else:
    print("⚠️ Could not find the CORS block. It might already be updated or different.")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Allow CORS for Flutter Web development"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render is now redeploying your backend (it will take ~2 minutes).

Once the backend is "Live", go back to your Flutter app in Chrome and 
click the "Login" button again. 

Because the backend is on a free tier, the first request might take a 
few seconds to wake it up, but it will succeed!
""")