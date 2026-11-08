#!/usr/bin/env python3
"""Fixes Flutter Colors.emerald error."""
from pathlib import Path

ROOT = Path.cwd()
MOBILE_DIR = ROOT / "mobile" / "lib"

files_to_fix = [
    "login_screen.dart",
    "home_screen.dart",
    "main.dart"
]

for filename in files_to_fix:
    filepath = MOBILE_DIR / filename
    if filepath.exists():
        text = filepath.read_text(encoding="utf-8")
        # Replace Colors.emerald with the exact hex code for NyumbaLink green
        text = text.replace("Colors.emerald", "Color(0xFF059669)")
        # For the main theme, primarySwatch expects a MaterialColor, so we'll just use Colors.green
        if filename == "main.dart":
            text = text.replace("primarySwatch: Color(0xFF059669)", "primarySwatch: Colors.green")
            
        filepath.write_text(text, encoding="utf-8")
        print(f"✅ Patched {filename}")

print("""
==================================================
🎉 COLORS FIXED!
==================================================

Go back to your terminal in the mobile folder and run:

  flutter run -d chrome --web-port 5173

It should compile successfully now!
""")