#!/usr/bin/env python3
"""Fixes missing http import in chat_screen.dart."""
from pathlib import Path

ROOT = Path.cwd()
CHAT_FILE = ROOT / "mobile" / "lib" / "chat_screen.dart"

text = CHAT_FILE.read_text(encoding="utf-8")

# Check if the import is already there
if "import 'package:http/http.dart' as http;" not in text:
    # Insert it at the top of the file (along with other imports)
    text = text.replace(
        "import 'dart:async';",
        "import 'dart:async';\nimport 'package:http/http.dart' as http;"
    )
    CHAT_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched chat_screen.dart: Added http import")
else:
    print("ℹ️ Import already exists.")

print("""
==================================================
🎉 IMPORT FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.
The app should compile successfully now.
""")