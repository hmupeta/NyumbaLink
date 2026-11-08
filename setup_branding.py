#!/usr/bin/env python3
"""Applies the NyumbaLink logo to React and Flutter apps."""
from __future__ import annotations
import subprocess
import shutil
from pathlib import Path

ROOT = Path.cwd()
LOGO_PATH = ROOT / "logo.png"

if not LOGO_PATH.exists():
    print("❌ ERROR: Please save the logo image as 'logo.png' in the project root first.")
    exit(1)

# ----------------------------------------------------------------
# 1. WEB APP (React) Branding
# ----------------------------------------------------------------
print("🌐 Updating Web App Branding...")
FRONTEND = ROOT / "frontend"
FRONTEND_PUBLIC = FRONTEND / "public"
FRONTEND_SRC = FRONTEND / "src"

# Copy logo to public folder
shutil.copy(LOGO_PATH, FRONTEND_PUBLIC / "logo.png")

# Update index.html (Favicon and Title)
INDEX_HTML = FRONTEND / "index.html"
text = INDEX_HTML.read_text(encoding="utf-8")
if '<link rel="icon" type="image/png" href="/logo.png" />' not in text:
    # Remove default vite favicon if it exists
    text = text.replace('<link rel="icon" type="image/svg+xml" href="/vite.svg" />', '')
    # Add new favicon
    text = text.replace('<head>', '<head>\n    <link rel="icon" type="image/png" href="/logo.png" />')
    INDEX_HTML.write_text(text, encoding="utf-8")
    print("  ✅ Updated index.html favicon")

# Update Layout.tsx (Header Logo)
LAYOUT_FILE = FRONTEND_SRC / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")
if 'src="/logo.png"' not in text:
    old_logo = '''<Link to="/" className="text-xl font-bold text-emerald-700 tracking-tight">NyumbaLink</Link>'''
    new_logo = '''<Link to="/" className="flex items-center gap-2">
  <img src="/logo.png" alt="NyumbaLink" className="h-8 w-8 object-contain" />
  <span className="text-xl font-bold text-emerald-700 tracking-tight">NyumbaLink</span>
</Link>'''
    text = text.replace(old_logo, new_logo)
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("  ✅ Updated Layout.tsx header logo")

# Update LoginPage.tsx (Auth Screen Logo)
LOGIN_FILE = FRONTEND_SRC / "pages" / "LoginPage.tsx"
text = LOGIN_FILE.read_text(encoding="utf-8")
if 'src="/logo.png"' not in text:
    old_login = '''<h1 className="text-2xl font-bold mb-6">Log in to NyumbaLink</h1>'''
    new_login = '''<div className="flex flex-col items-center mb-6">
  <img src="/logo.png" alt="NyumbaLink" className="h-16 w-16 object-contain mb-2" />
  <h1 className="text-2xl font-bold">Log in to NyumbaLink</h1>
</div>'''
    text = text.replace(old_login, new_login)
    LOGIN_FILE.write_text(text, encoding="utf-8")
    print("  ✅ Updated LoginPage logo")

# ----------------------------------------------------------------
# 2. MOBILE APP (Flutter) Branding
# ----------------------------------------------------------------
print("\n📱 Updating Mobile App Branding...")
MOBILE = ROOT / "mobile"
FLUTTER_ASSETS = MOBILE / "assets" / "images"
FLUTTER_ASSETS.mkdir(parents=True, exist_ok=True)

# Copy logo to Flutter assets
shutil.copy(LOGO_PATH, FLUTTER_ASSETS / "logo.png")

# Update pubspec.yaml (Assets & Launcher Icons)
PUBSPEC = MOBILE / "pubspec.yaml"
text = PUBSPEC.read_text(encoding="utf-8")

if "assets/images/" not in text:
    text = text.replace(
        "  flutter:\n    sdk: flutter\n",
        "  flutter:\n    sdk: flutter\n    assets:\n      - assets/images/\n"
    )
    
if "flutter_launcher_icons:" not in text:
    # Add dev dependency for launcher icons
    text = text.replace(
        "dev_dependencies:\n  flutter_test:\n    sdk: flutter",
        "dev_dependencies:\n  flutter_test:\n    sdk: flutter\n  flutter_launcher_icons: ^0.13.1\n\nflutter_launcher_icons:\n  android: true\n  ios: true\n  image_path: \"assets/images/logo.png\""
    )
    
PUBSPEC.write_text(text, encoding="utf-8")
print("  ✅ Updated pubspec.yaml for assets and launcher icons")

# Update LoginScreen.dart
FLUTTER_LOGIN = MOBILE / "lib" / "login_screen.dart"
text = FLUTTER_LOGIN.read_text(encoding="utf-8")
if "assets/images/logo.png" not in text:
    old_flutter_login = '''Text("NyumbaLink", style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Color(0xFF059669))),'''
    new_flutter_login = '''Column(
  children: [
    Image.asset("assets/images/logo.png", height: 80),
    SizedBox(height: 16),
    Text("NyumbaLink", style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
  ],
),'''
    text = text.replace(old_flutter_login, new_flutter_login)
    FLUTTER_LOGIN.write_text(text, encoding="utf-8")
    print("  ✅ Updated Flutter LoginScreen logo")

# Update HomeScreen AppBar
FLUTTER_HOME = MOBILE / "lib" / "home_screen.dart"
text = FLUTTER_HOME.read_text(encoding="utf-8")
if "assets/images/logo.png" not in text:
    old_flutter_home = '''title: Text("NyumbaLink"),'''
    new_flutter_home = '''title: Row(
          children: [
            Image.asset("assets/images/logo.png", height: 32),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),'''
    text = text.replace(old_flutter_home, new_flutter_home)
    FLUTTER_HOME.write_text(text, encoding="utf-8")
    print("  ✅ Updated Flutter HomeScreen AppBar")

print("\n🚀 Generating Flutter App Launcher Icons (this takes a minute)...")
subprocess.run(["flutter", "pub", "get"], cwd=MOBILE, shell=True)
subprocess.run(["dart", "run", "flutter_launcher_icons"], cwd=MOBILE, shell=True)

print("""
==================================================
🎉 BRANDING COMPLETE!
==================================================

1. WEB APP:
   - Restart the Vite dev server.
   - The favicon in the browser tab will be updated.
   - The Header and Login screens will show the new logo.

2. MOBILE APP:
   - Restart the Flutter app (press 'q', then 'flutter run -d chrome').
   - The Login and Home screens will show the logo.
   - The actual App Icon on Android and iOS devices has been generated!
""")