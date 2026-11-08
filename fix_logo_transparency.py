#!/usr/bin/env python3
"""Removes the white background from the logo and updates both apps."""
from __future__ import annotations
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path.cwd()
LOGO_PATH = ROOT / "logo.png"

if not LOGO_PATH.exists():
    print("❌ ERROR: logo.png not found in project root.")
    exit(1)

# ----------------------------------------------------------------
# 1. Make the white background transparent
# ----------------------------------------------------------------
print("🎨 Removing white background from logo...")
img = Image.open(LOGO_PATH).convert("RGBA")
datas = img.getdata()

new_data = []
for item in datas:
    # If the pixel is white (or very close to it), make it transparent
    if item[0] > 240 and item[1] > 240 and item[2] > 240:
        new_data.append((255, 255, 255, 0))
    else:
        new_data.append(item)

img.putdata(new_data)
img.save(LOGO_PATH) # Overwrite the original
print("✅ Logo is now transparent.")

# ----------------------------------------------------------------
# 2. Update Web App (React)
# ----------------------------------------------------------------
print("\n🌐 Updating Web App...")
FRONTEND = ROOT / "frontend"
shutil_path = FRONTEND / "public" / "logo.png"

import shutil
shutil.copy(LOGO_PATH, shutil_path)

LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")

# Add mix-blend-multiply as a CSS fallback to ensure it blends if the browser caches the old image
if "mix-blend-multiply" not in text:
    text = text.replace(
        'className="h-8 w-8 object-contain"',
        'className="h-8 w-8 object-contain mix-blend-multiply"'
    )
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("  ✅ Patched Layout.tsx with CSS blend mode")

# ----------------------------------------------------------------
# 3. Update Mobile App (Flutter)
# ----------------------------------------------------------------
print("\n📱 Updating Mobile App...")
MOBILE = ROOT / "mobile"
FLUTTER_LOGO = MOBILE / "assets" / "images" / "logo.png"
shutil.copy(LOGO_PATH, FLUTTER_LOGO)

print("  ✅ Replaced Flutter logo asset")
print("\n⏳ Regenerating Flutter launcher icons...")
subprocess.run(["dart", "run", "flutter_launcher_icons"], cwd=MOBILE, shell=True)

print("""
==================================================
🎉 LOGO FIXED!
==================================================

1. WEB APP:
   - Stop the Vite server (Ctrl+C) and restart: `npm run dev`
   - The logo will now be fully visible in the header and on the login page.

2. MOBILE APP:
   - Stop the Flutter app (press 'q') and restart: `flutter run -d chrome`
   - The logo on the green AppBar will now be transparent and look professional.
""")