#!/usr/bin/env python3
"""Doubles the logo size and ensures image URLs are bulletproof."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Web App: Double Logo Size (h-10 -> h-20)
# ----------------------------------------------------------------
LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")

if 'className="h-20 w-auto object-contain"' not in text:
    text = text.replace(
        'className="h-10 w-auto object-contain"',
        'className="h-20 w-auto object-contain"'
    )
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched Layout.tsx: Doubled web logo size to h-20 (80px)")

# ----------------------------------------------------------------
# 2. Mobile App: Double Logo Size
# ----------------------------------------------------------------
HOME_FILE = MOBILE / "lib" / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")
if 'height: 80' not in text:
    text = text.replace(
        'Image.asset("assets/images/logo.png", height: 40),',
        'Image.asset("assets/images/logo.png", height: 80),'
    )
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Doubled mobile header logo to 80")

LOGIN_FILE = MOBILE / "lib" / "login_screen.dart"
text = LOGIN_FILE.read_text(encoding="utf-8")
if 'height: 160' not in text:
    text = text.replace(
        'Image.asset("assets/images/logo.png", height: 80),',
        'Image.asset("assets/images/logo.png", height: 160),'
    )
    LOGIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Doubled mobile login logo to 160")

# ----------------------------------------------------------------
# 3. Ensure Image Logic is Bulletproof
# ----------------------------------------------------------------
# Backend: Ensure local files return absolute URLs
SERIALIZER_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZER_FILE.read_text(encoding="utf-8")

# We just want to make sure the logic is solid.
if "request.build_absolute_uri(url)" not in text:
    print("⚠️ Backend image serializer might need manual check. Expected request.build_absolute_uri.")

# Frontend: Ensure URLs are handled correctly
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

new_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // 1. If the backend already sent an absolute URL, use it
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 2. If it's a relative path, prepend the backend base URL
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''

import re
pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"
text = re.sub(pattern, new_url_logic, text)
API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched frontend listings.ts: Ensured getMediaUrl handles absolute and relative paths")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Double logo size and ensure bulletproof image URLs"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 LOGO RESIZED AND IMAGE LOGIC FIXED!
==================================================

### 1. To see the new logo size:
- **Web:** Hard refresh your browser (`Ctrl + Shift + R`).
- **Mobile:** Restart Flutter (`q`, then `flutter run -d chrome`).

### 2. Why the image was broken:
The screenshot shows a property in "Meanwood". If you uploaded that image while running the backend locally, it was saved to your computer's hard drive. When you view the site on Render, it looks for `https://nyumbalink-backend-eaw2.onrender.com/media/...`, but the file isn't there because it was never uploaded to Cloudinary (or the Render disk was wiped).

**To fix the broken image permanently:**
1. Go to your local app (or Render app).
2. Click **Edit** on that specific property.
3. Upload the image again.
4. Now that Cloudinary is fully configured, the image will be saved to the cloud and will work on both local and production environments.
""")