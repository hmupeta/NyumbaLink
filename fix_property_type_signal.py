#!/usr/bin/env python3
"""Fixes the AttributeError in search/signals.py."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "apps" / "search" / "signals.py"

if not FILE.exists():
    print("signals.py not found.")
    exit()

text = FILE.read_text(encoding="utf-8")

# Fix the typo: instance.property.type -> instance.property.property_type
if "instance.property.type)" in text:
    text = text.replace("instance.property.type)", "instance.property.property_type)")
    FILE.write_text(text, encoding="utf-8")
    print("Patched apps/search/signals.py: fixed property_type attribute.")
else:
    print("Typo not found. The file may already be fixed.")

print("""
Done! 
  1. The backend will auto-reload (Django runserver).
  2. Go back to Moderation and click "Approve" on the listing.
  3. It should now successfully publish!
""")