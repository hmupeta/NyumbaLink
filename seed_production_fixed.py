#!/usr/bin/env python3
"""
Connects to the Render production database and seeds demo data.
This script sanitizes the pasted URL to prevent parsing errors.
"""
import os
import sys
import re
import django
from getpass import getpass

print("=" * 60)
print("NyumbaLink Production Seeder (Fixed)")
print("=" * 60)
raw_input = getpass("Paste your Render External Database URL (input will be hidden): ").strip()

# Use regex to find the first valid PostgreSQL URL in the string
# This handles cases where the URL is pasted multiple times or has extra text
match = re.search(r"(postgres(?:ql)?://[^\s]+)", raw_input)

if not match:
    print("\n❌ ERROR: Could not find a valid 'postgres://' or 'postgresql://' URL in what you pasted.")
    print("Please copy the 'External Database URL' exactly from your Render dashboard.")
    sys.exit(1)

RENDER_DB_URL = match.group(1)
print(f"\n✅ Parsed Database Host: {RENDER_DB_URL.split('@')[1].split('/')[0]}")

# Set up environment for production settings
os.environ["DATABASE_URL"] = RENDER_DB_URL
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"

# Initialize Django
try:
    django.setup()
except Exception as e:
    print(f"\n❌ ERROR initializing Django: {e}")
    sys.exit(1)

from apps.accounts.models import User
from apps.locations.models import Province, District, Locality, Neighbourhood
from apps.properties.models import Property, Listing, ListingMedia, PropertyFeature
from apps.properties.enums import PropertyType, TransactionType, PricePeriod, ListingStatus, MediaType

def run():
    print("\n🚀 Connecting to Render Production Database...")
    
    # 1. CREATE USERS
    print("👤 Creating Users...")
    
    admin, created = User.objects.get_or_create(
        email="admin@nyumbalink.com",
        defaults={"is_staff": True, "is_superuser": True, "first_name": "Platform", "last_name": "Admin"}
    )
    if created:
        admin.set_password("AdminPassword123!")
        admin.save()
        print("  ✅ Admin created: admin@nyumbalink.com / AdminPassword123!")

    landlord, created = User.objects.get_or_create(
        email="landlord@nyumbalink.com",
        defaults={"first_name": "Demo", "last_name": "Landlord"}
    )
    if created:
        landlord.set_password("LandlordPassword123!")
        landlord.save()
        print("  ✅ Landlord created: landlord@nyumbalink.com / LandlordPassword123!")

    seeker, created = User.objects.get_or_create(
        email="seeker@nyumbalink.com",
        defaults={"first_name": "Demo", "last_name": "Seeker"}
    )
    if created:
        seeker.set_password("SeekerPassword123!")
        seeker.save()
        print("  ✅ Seeker created: seeker@nyumbalink.com / SeekerPassword123!")

    # 2. CREATE LOCATIONS
    print("📍 Creating Locations...")
    lusaka, _ = Province.objects.get_or_create(slug="lusaka", defaults={"name": "Lusaka", "code": "LS"})
    lusaka_dist, _ = District.objects.get_or_create(province=lusaka, slug="lusaka", defaults={"name": "Lusaka"})
    lusaka_loc, _ = Locality.objects.get_or_create(district=lusaka_dist, slug="lusaka", defaults={"name": "Lusaka"})
    kabulonga, _ = Neighbourhood.objects.get_or_create(locality=lusaka_loc, slug="kabulonga", defaults={"name": "Kabulonga"})
    woodlands, _ = Neighbourhood.objects.get_or_create(locality=lusaka_loc, slug="woodlands", defaults={"name": "Woodlands"})

    # 3. CREATE FEATURES
    print("✨ Creating Features...")
    pool, _ = PropertyFeature.objects.get_or_create(slug="swimming-pool", defaults={"name": "Swimming Pool"})
    parking, _ = PropertyFeature.objects.get_or_create(slug="parking", defaults={"name": "Parking"})
    borehole, _ = PropertyFeature.objects.get_or_create(slug="borehole", defaults={"name": "Borehole"})

    # 4. CREATE PROPERTIES & LISTINGS
    print("🏠 Creating Properties...")
    
    # Property 1: Kabulonga
    prop1, _ = Property.objects.get_or_create(
        neighbourhood=kabulonga, submitted_by=landlord,
        defaults={"property_type": PropertyType.HOUSE, "bedrooms": 4, "bathrooms": 3, "floor_area": 350.00, "latitude": -15.423456, "longitude": 28.321234}
    )
    prop1.features.add(pool, parking)
    
    listing1, _ = Listing.objects.get_or_create(
        property=prop1, created_by=landlord,
        defaults={"transaction_type": TransactionType.RENT, "price": 15000.00, "currency": "ZMW", "price_period": PricePeriod.MONTH, "title": "Luxurious 4-Bed House in Kabulonga", "status": ListingStatus.PUBLISHED}
    )
    ListingMedia.objects.get_or_create(listing=listing1, file="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800", media_type=MediaType.IMAGE, display_order=1)

    # Property 2: Woodlands
    prop2, _ = Property.objects.get_or_create(
        neighbourhood=woodlands, submitted_by=landlord,
        defaults={"property_type": PropertyType.APARTMENT, "bedrooms": 2, "bathrooms": 1, "floor_area": 85.00, "latitude": -15.415678, "longitude": 28.305123}
    )
    prop2.features.add(parking, borehole)
    
    listing2, _ = Listing.objects.get_or_create(
        property=prop2, created_by=landlord,
        defaults={"transaction_type": TransactionType.RENT, "price": 6500.00, "currency": "ZMW", "price_period": PricePeriod.MONTH, "title": "Modern 2-Bed Apartment in Woodlands", "status": ListingStatus.PUBLISHED}
    )
    ListingMedia.objects.get_or_create(listing=listing2, file="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800", media_type=MediaType.IMAGE, display_order=1)

    # Property 3: Woodlands (For Sale)
    prop3, _ = Property.objects.get_or_create(
        neighbourhood=woodlands, submitted_by=landlord,
        defaults={"property_type": PropertyType.TOWNHOUSE, "bedrooms": 3, "bathrooms": 2, "floor_area": 180.00, "latitude": -15.416789, "longitude": 28.306543}
    )
    listing3, _ = Listing.objects.get_or_create(
        property=prop3, created_by=landlord,
        defaults={"transaction_type": TransactionType.SALE, "price": 1450000.00, "currency": "ZMW", "price_period": PricePeriod.ONCE, "title": "Executive 3-Bed Townhouse for Sale", "status": ListingStatus.PUBLISHED}
    )
    ListingMedia.objects.get_or_create(listing=listing3, file="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800", media_type=MediaType.IMAGE, display_order=1)

    print("\n🎉 PRODUCTION SEEDING COMPLETE!")
    print("You can now log in to your live site with:")
    print("Admin: admin@nyumbalink.com / AdminPassword123!")
    print("Landlord: landlord@nyumbalink.com / LandlordPassword123!")
    print("Seeker: seeker@nyumbalink.com / SeekerPassword123!")

if __name__ == "__main__":
    run()