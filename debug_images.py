#!/usr/bin/env python3
"""Diagnostic script to inspect image URLs in production."""
import os
import sys
import re
import django
import json
from getpass import getpass

print("=" * 60)
print("NyumbaLink Image Diagnostic Tool")
print("=" * 60)

RENDER_DB_URL = getpass("Paste your Render External Database URL: ").strip()
match = re.search(r"(postgres(?:ql)?://[^\s]+)", RENDER_DB_URL)
if not match:
    print("❌ Invalid URL")
    sys.exit(1)

os.environ["DATABASE_URL"] = match.group(1)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
django.setup()

from apps.properties.models import ListingMedia

def run_diagnostic():
    print("\n🔍 Fetching the 5 most recently uploaded images...")
    # Order by created_at descending to get the newest ones
    recent_media = ListingMedia.objects.all().order_by('-created_at')[:5]

    if not recent_media:
        print("❌ No media records found in the database at all.")
        return

    for index, media in enumerate(recent_media, 1):
        print(f"\n--- Image {index} (ID: {media.id}) ---")
        
        # 1. What is stored in the database?
        raw_name = str(media.file.name)
        print(f"Raw Database String: {raw_name}")

        # 2. What does Django's storage backend say the URL is?
        try:
            final_url = media.file.url
            print(f"Django Generated URL: {final_url}")
        except Exception as e:
            print(f"Django Generated URL: ❌ ERROR ({e})")
            continue

        # 3. Diagnosis
        if raw_name.startswith('http'):
            print("✅ DIAGNOSIS: This is a valid external/Cloudinary URL.")
            print("   If the frontend isn't showing it, check the frontend `getMediaUrl` function.")
        elif final_url.startswith('/media/'):
            print("❌ DIAGNOSIS: This is a LOCAL path. Cloudinary is NOT working.")
            print("   Django is trying to save to Render's local disk, which gets wiped.")
            print("   -> Check your Render Environment Variables (CLOUDINARY_CLOUD_NAME, etc).")
        else:
            print("⚠️ DIAGNOSIS: Unknown format. Check the storage backend configuration.")

if __name__ == "__main__":
    run_diagnostic()