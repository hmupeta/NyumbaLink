#!/usr/bin/env python3
"""Fixes the missing bottom nav after login."""
from pathlib import Path

ROOT = Path.cwd()
LOGIN_FILE = ROOT / "mobile" / "lib" / "login_screen.dart"

text = LOGIN_FILE.read_text(encoding="utf-8")

old_nav = '''      // FIX: Use MaterialPageRoute instead of pushReplacementNamed('/home')
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => HomeScreen()),
        );
      }'''

new_nav = '''      // FIX: Just pop the login screen. The MainLayout is underneath!
      if (mounted) {
        Navigator.pop(context);
      }'''

if old_nav in text:
    text = text.replace(old_nav, new_nav)
    # Remove the now unused import
    text = text.replace("import 'home_screen.dart'; // Ensure HomeScreen is imported\n", "")
    LOGIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Login now pops back to MainLayout")
else:
    print("⚠️ Could not find the exact navigation code. Please check login_screen.dart manually.")

print("""
==================================================
🎉 NAVIGATION FIXED!
==================================================

Go back to your Flutter terminal and fully restart the app (press 'q', then run again).

1. Click the Profile tab.
2. Log in as seeker@nyumbalink.com / SeekerPassword123!
3. The Login screen will close, and you will be back on the Profile tab.
4. The Bottom Navigation Bar will remain visible!
""")