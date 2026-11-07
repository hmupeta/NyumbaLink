#!/usr/bin/env python3
"""
Cleans up the production database:
1. Fixes mangled Unsplash URLs.
2. Deletes orphaned media records (files lost in redeploys).
3. Reseeds demo media with proper URLs.
"""
import os
import sys
import re
import django
from getpass import getpass

print("=" * 60)
print("NyumbaLink Production Media Cleaner")
print("=" * 60)

RENDER_DB_URL = getpass("Paste your Render External Database URL: ").strip()

# Extract valid URL from pasted string
match = re.search(r"(postgres(?:ql)?://[^\s]+)", RENDER_DB_URL)
if not match:
    print("❌ No valid PostgreSQL URL found.")
    sys.exit(1)

RENDER_DB_URL = match.group(1)

# Configure Django
os.environ["DATABASE_URL"] = RENDER_DB_URL
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"

try:
    django.setup()
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

from apps.properties.models import ListingMedia, Listing
from apps.properties.enums import MediaType

def clean():
    print("\n🔍 Scanning ListingMedia records...")
    all_media = ListingMedia.objects.all()
    print(f"Found {all_media.count()} media records total.\n")

    fixed = 0
    deleted = 0
    kept = 0

    for media in all_media:
        file_str = str(media.file)  # This is what's stored in the DB
        
        # CASE 1: Mangled Unsplash URL (e.g. https%3A/images.unsplash.com/...)
        if 'https%3A' in file_str or 'http%3A' in file_str or '/media/http' in file_str:
            print(f"🔧 Fixing mangled URL: {file_str[:80]}...")
            # Extract the real URL
            url_match = re.search(r'https?%3A[^\s]+|https?://[^\s]+', file_str)
            if url_match:
                new_url = url_match.group(0).replace('%3A', ':').replace('%2F', '/')
                media.file = new_url
                media.save(update_fields=['file'])
                fixed += 1
            else:
                media.delete()
                deleted += 1
        
        # CASE 2: Local file path (e.g. listings/xxx/yyy.jpg) - these files were lost
        # Note: If it starts with "http", it's already Cloudinary or external
        elif not file_str.startswith('http'):
            print(f"🗑️  Deleting orphaned local file: {file_str}")
            media.delete()
            deleted += 1
        
        # CASE 3: Already a proper URL - leave it alone
        else:
            kept += 1

    print(f"\n📊 Results:")
    print(f"   ✅ Fixed mangled URLs: {fixed}")
    print(f"   🗑️  Deleted orphaned records: {deleted}")
    print(f"   ✔️  Kept valid URLs: {kept}")

    # Re-seed demo images that were deleted
    print("\n🌱 Re-seeding demo media with proper URLs...")
    demo_listings = Listing.objects.filter(created_by__email="landlord@nyumbalink.com")
    
    for listing in demo_listings:
        if not listing.media.exists():
            if "Kabulonga" in listing.title:
                ListingMedia.objects.create(
                    listing=listing,
                    file="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
                    media_type=MediaType.IMAGE,
                    display_order=1
                )
                print(f"   ✅ Re-seeded Kabulonga image")
            elif "Woodlands" in listing.title and "Apartment" in listing.title:
                ListingMedia.objects.create(
                    listing=listing,
                    file="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
                    media_type=MediaType.IMAGE,
                    display_order=1
                )
                print(f"   ✅ Re-seeded Woodlands Apartment image")
            elif "Townhouse" in listing.title:
                ListingMedia.objects.create(
                    listing=listing,
                    file="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800",
                    media_type=MediaType.IMAGE,
                    display_order=1
                )
                print(f"   ✅ Re-seeded Townhouse image")

    print("\n🎉 CLEANUP COMPLETE!")

if __name__ == "__main__":
    clean()