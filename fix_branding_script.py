#!/usr/bin/env python3
"""Fixes the FRONTEND variable bug in setup_branding.py."""
from pathlib import Path

ROOT = Path.cwd()
SCRIPT = ROOT / "setup_branding.py"

text = SCRIPT.read_text(encoding="utf-8")

old = '''# ----------------------------------------------------------------
# 1. WEB APP (React) Branding
# ----------------------------------------------------------------
print("🌐 Updating Web App Branding...")
FRONTEND_PUBLIC = ROOT / "frontend" / "public"
FRONTEND_SRC = ROOT / "frontend" / "src"'''

new = '''# ----------------------------------------------------------------
# 1. WEB APP (React) Branding
# ----------------------------------------------------------------
print("🌐 Updating Web App Branding...")
FRONTEND = ROOT / "frontend"
FRONTEND_PUBLIC = FRONTEND / "public"
FRONTEND_SRC = FRONTEND / "src"'''

if "FRONTEND = ROOT" not in text:
    text = text.replace(old, new)
    SCRIPT.write_text(text, encoding="utf-8")
    print("✅ Fixed setup_branding.py")
else:
    print("ℹ️ Already fixed.")

print("""
Now run:
    python setup_branding.py
""")