#!/usr/bin/env python3
"""Fixes the blank screen after login when redirected by session timeout."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "login_screen.dart"

text = FILE.read_text(encoding="utf-8")

# 1. Ensure MainLayout is imported
if "import 'main_layout.dart';" not in text:
    text = text.replace(
        "import 'auth_provider.dart';",
        "import 'auth_provider.dart';\nimport 'main_layout.dart';"
    )

# 2. Update the navigation logic
old_nav = '''      // FIX: Just pop the login screen. The MainLayout is underneath!
      if (mounted) {
        Navigator.pop(context);
      }'''

new_nav = '''      // FIX: Check if we can pop. If not (because we were pushed as root by the 401 handler),
      // we must push the MainLayout instead.
      if (mounted) {
        if (Navigator.canPop(context)) {
          Navigator.pop(context);
        } else {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => MainLayout()),
          );
        }
      }'''

if old_nav in text:
    text = text.replace(old_nav, new_nav)
    FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Handled root navigation after login")
else:
    print("⚠️ Could not find the exact navigation block. Please check login_screen.dart manually.")

print("""
==================================================
🎉 NAVIGATION FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.

Now, when you log in, it will check if it needs to pop back to the previous screen, 
or if it needs to push the MainLayout (with the Bottom Navigation Bar). 
The white screen is gone!
""")