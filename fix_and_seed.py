import os
import re
import django
import subprocess
import sys
from pathlib import Path

# 1. Patch the Model
model_file = Path("apps/properties/models.py")
text = model_file.read_text(encoding="utf-8")
if "max_length=255" not in text:
    print("Patching models.py to allow longer file paths...")
    text = text.replace(
        "file = models.FileField(upload_to=listing_media_path)",
        "file = models.FileField(upload_to=listing_media_path, max_length=255)"
    )
    model_file.write_text(text, encoding="utf-8")
else:
    print("models.py already patched.")

# 2. Apply Migration
print("\nApplying migration...")
subprocess.run([sys.executable, "manage.py", "makemigrations", "properties"])
subprocess.run([sys.executable, "manage.py", "migrate"])

# 3. Seed Data
print("\nSeeding demo data...")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.accounts.models import User
from apps.locations.models import Province, District, Locality, Neighbourhood
from apps.properties.models import Property, Listing, ListingMedia, PropertyFeature
from apps.properties.enums import PropertyType, TransactionType, PricePeriod, ListingStatus, MediaType

# Clean up any failed demo data from the previous run
Listing.objects.filter(created_by__email="demo@nyumbalink.com").delete()
Property.objects.filter(submitted_by__email="demo@nyumbalink.com").delete()

landlord, _ = User.objects.get_or_create(
    email="demo@nyumbalink.com",
    defaults={"first_name": "Demo", "last_name": "Landlord"}
)
landlord.set_password("Password123!")
landlord.save()

lusaka = Province.objects.get(slug="lusaka")
lusaka_dist = District.objects.get(province=lusaka, slug="lusaka")
lusaka_loc = Locality.objects.get(district=lusaka_dist, slug="lusaka")
kabulonga, _ = Neighbourhood.objects.get_or_create(locality=lusaka_loc, slug="kabulonga", defaults={"name": "Kabulonga"})
woodlands, _ = Neighbourhood.objects.get_or_create(locality=lusaka_loc, slug="woodlands", defaults={"name": "Woodlands"})

pool = PropertyFeature.objects.filter(slug="swimming-pool").first()
parking = PropertyFeature.objects.filter(slug="parking").first()

# Property 1
prop1 = Property.objects.create(
    neighbourhood=kabulonga, submitted_by=landlord, property_type=PropertyType.HOUSE,
    bedrooms=4, bathrooms=3, floor_area=350.00, description="Beautiful 4-bedroom house."
)
if pool: prop1.features.add(pool)
if parking: prop1.features.add(parking)

listing1 = Listing.objects.create(
    property=prop1, created_by=landlord, transaction_type=TransactionType.RENT,
    price=15000.00, currency="ZMW", price_period=PricePeriod.MONTH,
    title="Luxurious 4-Bed House in Kabulonga", status=ListingStatus.PUBLISHED
)
ListingMedia.objects.create(
    listing=listing1,
    file="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
    media_type=MediaType.IMAGE, display_order=1
)

# Property 2
prop2 = Property.objects.create(
    neighbourhood=woodlands, submitted_by=landlord, property_type=PropertyType.APARTMENT,
    bedrooms=2, bathrooms=1, floor_area=85.00, description="Modern secure apartment."
)
if parking: prop2.features.add(parking)

listing2 = Listing.objects.create(
    property=prop2, created_by=landlord, transaction_type=TransactionType.RENT,
    price=6500.00, currency="ZMW", price_period=PricePeriod.MONTH,
    title="Modern 2-Bed Apartment in Woodlands", status=ListingStatus.PUBLISHED
)
ListingMedia.objects.create(
    listing=listing2,
    file="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
    media_type=MediaType.IMAGE, display_order=1
)

print("\nSuccessfully created 2 published listings!")