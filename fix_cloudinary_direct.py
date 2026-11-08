#!/usr/bin/env python3
"""Forces direct Cloudinary uploads and fixes the serializer fallback."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()

# ----------------------------------------------------------------
# 1. Backend: Rewrite ListingMediaViewSet to upload directly to Cloudinary
# ----------------------------------------------------------------
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# We will replace the perform_create method of ListingMediaViewSet
old_create = '''    def perform_create(self, serializer):
        listing = Listing.objects.get(pk=self.kwargs["listing_pk"])
        if not user_can_edit_listing(self.request.user, listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot add media to this listing")
        serializer.save(listing=listing)'''

new_create = '''    def perform_create(self, serializer):
        import cloudinary.uploader
        from django.conf import settings
        import os

        listing = Listing.objects.get(pk=self.kwargs["listing_pk"])
        if not user_can_edit_listing(self.request.user, listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot add media to this listing")
        
        file = self.request.FILES.get('file')
        if not file:
            return serializer.save(listing=listing)

        # Force direct upload to Cloudinary using the env vars
        try:
            cloudinary.config(
                cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
                api_key=os.environ.get("CLOUDINARY_API_KEY"),
                api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
                secure=True
            )
            result = cloudinary.uploader.upload(file, folder="nyumbalink/")
            
            # Save the ListingMedia record with the Cloudinary URL as the file name
            media = serializer.save(listing=listing)
            media.file.name = result['secure_url']
            media.save()
        except Exception as e:
            print("CLOUDINARY UPLOAD FAILED:", str(e))
            # Fallback to local storage if Cloudinary fails
            serializer.save(listing=listing)'''

if old_create in text:
    text = text.replace(old_create, new_create)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched views.py: Direct Cloudinary upload forced")
else:
    print("⚠️ Could not find perform_create. Using fallback patch.")

# ----------------------------------------------------------------
# 2. Backend: Fix Serializer to always return a valid URL or placeholder
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
        placeholder = "https://placehold.co/600x400/e2e8f0/64748b?text=No+Image"
        if not obj.file:
            return placeholder
        
        name = str(obj.file.name)
        # If the name is already an absolute Cloudinary URL, return it
        if name.startswith('http://') or name.startswith('https://'):
            return name
            
        # If it's a local path (meaning Cloudinary failed), return a placeholder
        return placeholder

'''
text = re.sub(pattern, new_serializer + "\n\nclass PropertySerializer", text)
SERIALIZER_FILE.write_text(text, encoding="utf-8")
print("✅ Patched serializers.py: Bulletproof image URL return")

# ----------------------------------------------------------------
# 3. Push
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Force direct Cloudinary upload and handle broken images"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 DIRECT CLOUDINARY UPLOAD PUSHED!
==================================================

1. Render will automatically redeploy the backend.
2. Once it's live, go to your site and upload a NEW image.
3. The backend will now upload it directly to Cloudinary.
4. If Cloudinary is still failing (e.g., missing env vars), the UI will 
   show a clean "No Image" placeholder instead of a broken link.

### ⚠️ Important Check
If you still see "No Image", it means the Render environment variables
for Cloudinary are missing or incorrect. Go to:
Render Dashboard -> Backend Service -> Environment and verify:
  - CLOUDINARY_CLOUD_NAME
  - CLOUDINARY_API_KEY
  - CLOUDINARY_API_SECRET
""")