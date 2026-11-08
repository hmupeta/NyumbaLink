#!/usr/bin/env python3
"""Fixes serializers and frontend to handle Cloudinary and external URLs."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Backend: Make Serializer bulletproof
# ----------------------------------------------------------------
SERIALIZER_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZER_FILE.read_text(encoding="utf-8")

new_serializer = '''class ListingMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = ListingMedia
        fields = ("id", "listing", "file", "media_type", "caption", "display_order")
        read_only_fields = ("id", "listing")

    def get_file(self, obj):
        if not obj.file:
            return None
        # Check the raw name in the database
        name = str(obj.file.name)
        if name.startswith('http'):
            return name
        # If it's a local file or Cloudinary path, let Django/Cloudinary build the URL
        return obj.file.url'''

pattern = r"class ListingMediaSerializer\(serializers\.ModelSerializer\):([\s\S]*?)class PropertySerializer"
text = re.sub(pattern, new_serializer + "\n\n\nclass PropertySerializer", text)
SERIALIZER_FILE.write_text(text, encoding="utf-8")
print("✅ Patched serializers.py")

# ----------------------------------------------------------------
# 2. Frontend: Make getMediaUrl bulletproof
# ----------------------------------------------------------------
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"
new_function = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // 1. If it starts with /media/http, strip the /media/ prefix
  if (url.startsWith('/media/http')) {
    return url.replace('/media/', '')
  }
  
  // 2. Standard absolute URLs (Cloudinary or Unsplash)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 3. Local paths (Django backend)
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''
text = re.sub(pattern, new_function, text)
API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched frontend getMediaUrl")

print("\n🚀 Pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Bulletproof image URLs for Cloudinary"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)