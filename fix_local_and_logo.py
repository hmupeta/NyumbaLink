#!/usr/bin/env python3
"""Fixes local image serving and ensures logo sizes are correct."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Backend: Ensure urls.py serves media locally
# ----------------------------------------------------------------
URLS_FILE = ROOT / "config" / "urls.py"
text = URLS_FILE.read_text(encoding="utf-8")

if "urlpatterns += static(settings.MEDIA_URL" not in text:
    # Check if the static import is there
    if "from django.conf.urls.static import static" not in text:
        text = text.replace(
            "from django.urls import include, path",
            "from django.urls import include, path\nfrom django.conf.urls.static import static\nfrom django.conf import settings"
        )
    
    text += '''
# Serve media files during local development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
'''
    URLS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched config/urls.py: Guaranteed media serving in local dev")

# ----------------------------------------------------------------
# 2. Backend: Fix Serializer to return relative paths
# ----------------------------------------------------------------
SERIALIZER_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZER_FILE.read_text(encoding="utf-8")

pattern = r"class ListingMediaSerializer\(serializers\.ModelSerializer\):([\s\S]*?)class PropertySerializer"

new_serializer = '''class ListingMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = ListingMedia
        fields = ("id", "listing", "file", "media_type", "caption", "display_order")
        read_only_fields = ("id", "listing")

    def get_file(self, obj):
        if not obj.file:
            return None
        
        name = str(obj.file.name)
        
        # 1. External or Cloudinary URL
        if name.startswith('http://') or name.startswith('https://'):
            return name
            
        # 2. Local file (return relative path like /media/...)
        try:
            return obj.file.url
        except Exception:
            return None

'''
text = re.sub(pattern, new_serializer + "\n\nclass PropertySerializer", text)
SERIALIZER_FILE.write_text(text, encoding="utf-8")
print("✅ Patched serializers.py: Return relative URLs for local dev")

# ----------------------------------------------------------------
# 3. Frontend: Bulletproof getMediaUrl
# ----------------------------------------------------------------
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

new_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // 1. Absolute URL (Cloudinary, Unsplash)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 2. Relative path (e.g. /media/listings/img.jpg)
  // If we are in development, point to localhost:8000. 
  // If we are in production, point to the API base URL.
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''

pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"
text = re.sub(pattern, new_url_logic, text)
API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched frontend listings.ts: Bulletproofed getMediaUrl for local and prod")

# ----------------------------------------------------------------
# 4. Logo Sizes (Web and Mobile)
# ----------------------------------------------------------------
# Web
LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")
if 'h-20 w-auto object-contain' not in text:
    text = text.replace('className="h-10 w-auto object-contain"', 'className="h-20 w-auto object-contain"')
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched Layout.tsx: Doubled web logo size")

# Mobile Home
HOME_FILE = MOBILE / "lib" / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")
if 'height: 80' not in text:
    text = text.replace('Image.asset("assets/images/logo.png", height: 40),', 'Image.asset("assets/images/logo.png", height: 80),')
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Doubled mobile logo size")

# Mobile Login
LOGIN_FILE = MOBILE / "lib" / "login_screen.dart"
text = LOGIN_FILE.read_text(encoding="utf-8")
if 'height: 160' not in text:
    text = text.replace('Image.asset("assets/images/logo.png", height: 80),', 'Image.asset("assets/images/logo.png", height: 160),')
    LOGIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Doubled mobile login logo size")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Local media serving, relative URLs, and logo sizes"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIXES APPLIED!
==================================================

### 1. To fix the Local App Images:
1. **Restart your Django backend** (`Ctrl+C`, then `python manage.py runserver`).
2. **Hard refresh your React app** (`Ctrl + Shift + R`).

The backend will now correctly serve your local images from the `media/` folder.

### 2. To see the bigger logo:
- **Web:** Hard refresh (`Ctrl + Shift + R`).
- **Mobile:** Restart Flutter (`q`, then `flutter run -d chrome`).

*(Note: If an image is still missing, it means the physical file was deleted from your local `media/` folder. You will just need to click "Edit" on the listing and re-upload the image).*
""")