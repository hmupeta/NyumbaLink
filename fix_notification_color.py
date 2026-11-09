#!/usr/bin/env python3
"""Fixes the Colors.emerald error in notifications_screen.dart."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "notifications_screen.dart"

text = FILE.read_text(encoding="utf-8")

# Replace the invalid Colors.emerald with a valid Flutter green
if "Colors.emerald[50]" in text:
    text = text.replace(
        "Colors.emerald[50]",
        "Colors.green[50]"
    )
    FILE.write_text(text, encoding="utf-8")
    print("✅ Patched notifications_screen.dart: Replaced Colors.emerald with Colors.green")
else:
    print("ℹ️ Colors.emerald not found or already fixed.")

print("""
==================================================
🎉 COLOR FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload (or 'R' to hot restart).
The app should compile successfully now.
""")