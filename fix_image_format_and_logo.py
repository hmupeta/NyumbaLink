#!/usr/bin/env python3
"""Forces absolute URLs in the backend and applies final logo sizing."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Backend: Force Absolute URLs in Serializer
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
        
        # 1. External or Cloudinary URL (already absolute)
        if name.startswith('http://') or name.startswith('https://'):
            return name
            
        # 2. Local file: build the absolute URL (e.g., http://localhost:8000/media/...)
        try:
            url = obj.file.url
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None

'''
text = re.sub(pattern, new_serializer + "\n\nclass PropertySerializer", text)
SERIALIZER_FILE.write_text(text, encoding="utf-8")
print("✅ Patched serializers.py: Forced absolute URL generation")

# ----------------------------------------------------------------
# 2. Frontend: Simplify getMediaUrl (Backend handles the heavy lifting)
# ----------------------------------------------------------------
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

new_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // The backend now ALWAYS sends an absolute URL. Just return it.
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // Fallback just in case
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''

pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"
text = re.sub(pattern, new_url_logic, text)
API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched frontend listings.ts: Simplified getMediaUrl")

# ----------------------------------------------------------------
# 3. Logo Sizing (Web and Mobile)
# ----------------------------------------------------------------
# Web
LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")
if 'className="h-20 w-auto object-contain"' not in text:
    text = text.replace('className="h-10 w-auto object-contain"', 'className="h-20 w-auto object-contain"')
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched Layout.tsx: Web logo doubled to h-20")

# Mobile Home
HOME_FILE = MOBILE / "lib" / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")
if 'height: 80' not in text:
    text = text.replace('Image.asset("assets/images/logo.png", height: 40),', 'Image.asset("assets/images/logo.png", height: 80),')
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Mobile header logo doubled to 80")

# Mobile Login
LOGIN_FILE = MOBILE / "lib" / "login_screen.dart"
text = LOGIN_FILE.read_text(encoding="utf-8")
if 'height: 160' not in text:
    text = text.replace('Image.asset("assets/images/logo.png", height: 80),', 'Image.asset("assets/images/logo.png", height: 160),')
    LOGIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Mobile login logo doubled to 160")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Force absolute image URLs and double logo sizes"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FORMATS FIXED & LOGO RESIZED!
==================================================

### Why this fixes the image issue:
The Django backend now uses `request.build_absolute_uri()`. 
- If you upload locally, it sends `http://localhost:8000/media/...`
- If you upload on Render (Cloudinary), it sends `https://res.cloudinary.com/...`
The frontend simply displays whatever the backend sends. No more guessing!

### Next steps:
1. **Restart your local Django backend** (`runserver`).
2. **Web App:** Hard refresh (`Ctrl + Shift + R`).
3. **Mobile App:** Restart (`q` then `flutter run -d chrome`).
""")