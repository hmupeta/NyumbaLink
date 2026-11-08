#!/usr/bin/env python3
"""Removes broken local images from the production database."""
import os
import sys
import re
import django
from getpass import getpass

print("=" * 60)
print("Clean Broken Local Uploads")
print("=" * 60)

RENDER_DB_URL = getpass("Paste your Render External Database URL: ").strip()
match = re.search(r"(postgres(?:ql)?://[^\s]+)", RENDER_DB_URL)
if not match:
    sys.exit(1)

os.environ["DATABASE_URL"] = match.group(1)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
django.setup()

from apps.properties.models import ListingMedia

def clean():
    print("\n🔍 Scanning for broken local image records...")
    deleted = 0
    
    for media in ListingMedia.objects.all():
        name = str(media.file.name)
        
        # If it's a local path (doesn't start with http) and doesn't contain cloudinary
        if not name.startswith('http') and 'cloudinary' not in name:
            print(f"🗑️  Deleting broken local file record: {name}")
            media.delete()
            deleted += 1
            
    print(f"\n✅ Deleted {deleted} broken image records.")

if __name__ == "__main__":
    clean()