#!/usr/bin/env python3
"""Replaces broken local media records with a placeholder image."""
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
    fixed = 0
    
    # We look for records that do NOT start with 'http' (meaning they are local paths)
    # But we exclude the ones that are already properly formatted Cloudinary URLs
    for media in ListingMedia.objects.all():
        name = str(media.file.name)
        
        # If it's a local path (does not start with http) and does not contain cloudinary
        if not name.startswith('http') and 'cloudinary' not in name:
            print(f"🗑️  Found broken local file: {name}")
            # Replace with a generic placeholder
            media.file.name = "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800"
            media.save(update_fields=['file'])
            fixed += 1
            
    print(f"\n✅ Replaced {fixed} broken image records with placeholders.")

if __name__ == "__main__":
    clean()