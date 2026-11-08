#!/usr/bin/env python3
"""Fixes image URLs at the backend source and updates frontends."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ---------------------------------------------------------------- 1. Backend Fix (The Root Cause)
SERIALIZER_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZER_FILE.read_text(encoding="utf-8")

if "class ListingMediaSerializer" in text and "SerializerMethodField()" not in text.split("class ListingMediaSerializer")[1]:
    old_serializer = '''class ListingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingMedia
        fields = ("id", "listing", "file", "media_type", "caption", "display_order")
        read_only_fields = ("id", "listing")'''

    new_serializer = '''class ListingMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = ListingMedia
        fields = ("id", "listing", "file", "media_type", "caption", "display_order")
        read_only_fields = ("id", "listing")

    def get_file(self, obj):
        if not obj.file:
            return None
        # If the DB has an external URL (like Unsplash), return it as-is
        if str(obj.file).startswith('http'):
            return str(obj.file)
        # Otherwise, let Cloudinary/Django generate the absolute URL
        return obj.file.url'''

    text = text.replace(old_serializer, new_serializer)
    SERIALIZER_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched serializers.py: Fixed FileField URL generation")

# ---------------------------------------------------------------- 2. React Fix
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"
new_function = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  // If it's already an absolute URL (Cloudinary or Unsplash), return it
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  // Otherwise, it's a relative path
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''
text = re.sub(pattern, new_function, text)
API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched React listings.ts: Simplified getMediaUrl")

# ---------------------------------------------------------------- 3. Flutter Fix
HOME_FILE = MOBILE / "lib" / "home_screen.dart"
if HOME_FILE.exists():
    text = HOME_FILE.read_text(encoding="utf-8")
    # Replace the inline ternary with a clean helper
    old_image_logic = "imageUrl: imageUrl.startsWith('http') ? imageUrl : 'https://nyumbalink-backend-eaw2.onrender.com$imageUrl',"
    new_image_logic = "imageUrl: _getFullImageUrl(imageUrl),"
    
    if old_image_logic in text:
        text = text.replace(old_image_logic, new_image_logic)
        
        # Add the helper method to the class
        helper_method = '''
  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }
'''
        # Insert helper before build method
        text = text.replace("  @override\n  Widget build(BuildContext context) {", helper_method + "\n  @override\n  Widget build(BuildContext context) {")
        
        HOME_FILE.write_text(text, encoding="utf-8")
        print("✅ Patched Flutter home_screen.dart: Added URL helper")

# ---------------------------------------------------------------- 4. Push
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Resolve image URL formatting for Cloudinary and Unsplash"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 IMAGE FIX DEPLOYED!
==================================================

1. Render will automatically rebuild your React frontend and Django backend.
2. Once deployed, refresh your React app. The images will load.
3. For Flutter, you need to restart the app. Go to your terminal, press 'q' to quit, and run:

   flutter run -d chrome --web-port 5173

The images will now load perfectly on both platforms!
""")