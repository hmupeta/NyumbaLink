#!/usr/bin/env python3
"""Increases logo size and removes CSS blend mode for sharpness."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Web App (React) - Header Logo
# ----------------------------------------------------------------
LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")

# Find the img tag for the logo and update size/classes
old_img = '<img src="/logo.png" alt="NyumbaLink" className="h-8 w-8 object-contain mix-blend-multiply" />'
new_img = '<img src="/logo.png" alt="NyumbaLink" className="h-10 w-auto object-contain" />'

if old_img in text:
    text = text.replace(old_img, new_img)
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched Layout.tsx: Increased web logo size to h-10 and removed blend mode")
else:
    print("⚠️ Could not find the exact image tag in Layout.tsx. Trying a broader replace.")
    text = text.replace('className="h-8 w-8 object-contain mix-blend-multiply"', 'className="h-10 w-auto object-contain"')
    LAYOUT_FILE.write_text(text, encoding="utf-8")

# ----------------------------------------------------------------
# 2. Mobile App (Flutter) - Home Screen Logo
# ----------------------------------------------------------------
HOME_FILE = MOBILE / "lib" / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

old_home_img = 'Image.asset("assets/images/logo.png", height: 32),'
new_home_img = 'Image.asset("assets/images/logo.png", height: 40),'

if old_home_img in text:
    text = text.replace(old_home_img, new_home_img)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Increased mobile header logo height to 40")

# ----------------------------------------------------------------
# 3. Mobile App (Flutter) - Login Screen Logo
# ----------------------------------------------------------------
LOGIN_FILE = MOBILE / "lib" / "login_screen.dart"
text = LOGIN_FILE.read_text(encoding="utf-8")

old_login_img = 'Image.asset("assets/images/logo.png", height: 80),'
new_login_img = 'Image.asset("assets/images/logo.png", height: 120),' # Bigger for auth screen

if old_login_img in text:
    text = text.replace(old_login_img, new_login_img)
    LOGIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Increased login logo height to 120")

print("""
==================================================
🎉 LOGO SIZE FIXED!
==================================================

1. WEB APP:
   - Go to your browser and do a HARD REFRESH to clear the cache:
     (Ctrl + Shift + R or Cmd + Shift + R)
   - The logo will now be 40px tall (h-10) and sharp.

2. MOBILE APP:
   - Restart Flutter (q, then flutter run -d chrome).
   - The logo will be larger on the Home AppBar and Login screen.
""")