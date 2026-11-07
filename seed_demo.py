import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.accounts.models import User
from apps.locations.models import Province, District, Locality, Neighbourhood
from apps.properties.models import Property, Listing, ListingMedia, PropertyFeature
from apps.properties.enums import PropertyType, TransactionType, PricePeriod, ListingStatus, MediaType

def run():
    print("Seeding demo data...")

    # 1. Create a demo landlord
    landlord, _ = User.objects.get_or_create(
        email="demo@nyumbalink.com",
        defaults={"first_name": "Demo", "last_name": "Landlord"}
    )
    landlord.set_password("Password123!")
    landlord.save()

    # 2. Get locations
    lusaka = Province.objects.get(slug="lusaka")
    lusaka_dist = District.objects.get(province=lusaka, slug="lusaka")
    lusaka_loc = Locality.objects.get(district=lusaka_dist, slug="lusaka")
    kabulonga, _ = Neighbourhood.objects.get_or_create(locality=lusaka_loc, slug="kabulonga", defaults={"name": "Kabulonga"})
    woodlands, _ = Neighbourhood.objects.get_or_create(locality=lusaka_loc, slug="woodlands", defaults={"name": "Woodlands"})

    # 3. Get features
    pool = PropertyFeature.objects.filter(slug="swimming-pool").first()
    parking = PropertyFeature.objects.filter(slug="parking").first()

    # 4. Create Property 1 (Kabulonga)
    prop1 = Property.objects.create(
        neighbourhood=kabulonga,
        submitted_by=landlord,
        property_type=PropertyType.HOUSE,
        bedrooms=4,
        bathrooms=3,
        floor_area=350.00,
        description="A beautiful 4-bedroom house in the heart of Kabulonga with a large garden and pool."
    )
    if pool: prop1.features.add(pool)
    if parking: prop1.features.add(parking)

    listing1 = Listing.objects.create(
        property=prop1,
        created_by=landlord,
        transaction_type=TransactionType.RENT,
        price=15000.00,
        currency="ZMW",
        price_period=PricePeriod.MONTH,
        title="Luxurious 4-Bed House in Kabulonga",
        description="Available immediately. Includes borehole water, solar backup, and 24/7 security.",
        status=ListingStatus.PUBLISHED
    )
    ListingMedia.objects.create(
        listing=listing1,
        file="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
        media_type=MediaType.IMAGE,
        display_order=1
    )

    # 5. Create Property 2 (Woodlands)
    prop2 = Property.objects.create(
        neighbourhood=woodlands,
        submitted_by=landlord,
        property_type=PropertyType.APARTMENT,
        bedrooms=2,
        bathrooms=1,
        floor_area=85.00,
        description="Modern 2-bedroom apartment in a secure complex."
    )
    if parking: prop2.features.add(parking)

    listing2 = Listing.objects.create(
        property=prop2,
        created_by=landlord,
        transaction_type=TransactionType.RENT,
        price=6500.00,
        currency="ZMW",
        price_period=PricePeriod.MONTH,
        title="Modern 2-Bed Apartment in Woodlands",
        description="Close to schools and shopping centres. Fibre internet ready.",
        status=ListingStatus.PUBLISHED
    )
    ListingMedia.objects.create(
        listing=listing2,
        file="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
        media_type=MediaType.IMAGE,
        display_order=1
    )

    print("Successfully created 2 published listings!")

if __name__ == "__main__":
    run()