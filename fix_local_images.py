#!/usr/bin/env python3
"""Fixes the serializer to allow local media files in development."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
SERIALIZER_FILE = ROOT / "apps" / "properties" / "serializers.py"

text = SERIALIZER_FILE.read_text(encoding="utf-8")

# We need to replace the overly aggressive placeholder logic
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
        
        # 1. If it's a Cloudinary or external URL, return it directly
        if name.startswith('http://') or name.startswith('https://'):
            return name
            
        # 2. If it's a local file, build the absolute URL (e.g., http://localhost:8000/media/...)
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
print("✅ Patched serializers.py: Restored local image URL handling")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Allow local media URLs in serializer for development"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 LOCAL IMAGE FIX APPLIED!
==================================================

1. Restart your local Django backend (`runserver`).
2. Refresh your local React app (`localhost:5173`).

The backend will now correctly return `http://localhost:8000/media/...` 
for your locally uploaded images, and the frontend will display them!
""")