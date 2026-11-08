#!/usr/bin/env python3
"""Fixes missing Uint8List import in create_listing_screen.dart."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "create_listing_screen.dart"

text = FILE.read_text(encoding="utf-8")

# Add the typed_data import at the top
if "import 'dart:typed_data';" not in text:
    text = text.replace(
        "import 'package:flutter/material.dart';",
        "import 'dart:typed_data';\nimport 'package:flutter/material.dart';"
    )
    FILE.write_text(text, encoding="utf-8")
    print("✅ Patched create_listing_screen.dart: Added dart:typed_data import")
else:
    print("ℹ️ Import already exists.")

print("""
==================================================
🎉 IMPORT FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.
The app should compile successfully now.
""")