from django.contrib.auth import get_user_model

from apps.locations.models import District, Locality, Neighbourhood, Province
from apps.properties.enums import PropertyType, TransactionType
from apps.properties.models import Listing, Property

User = get_user_model()


def make_location():
    province, _ = Province.objects.get_or_create(slug="lusaka", defaults={"name": "Lusaka", "code": "LS"})
    district, _ = District.objects.get_or_create(province=province, slug="lusaka", defaults={"name": "Lusaka"})
    locality, _ = Locality.objects.get_or_create(district=district, slug="lusaka", defaults={"name": "Lusaka"})
    hood, _ = Neighbourhood.objects.get_or_create(locality=locality, slug="kabulonga", defaults={"name": "Kabulonga"})
    return hood


def make_user(email="landlord@example.com", password="pw", **kw):
    return User.objects.create_user(email=email, password=password, **kw)


def make_property(submitter, **kw):
    hood = make_location()
    defaults = dict(
        neighbourhood=hood,
        submitted_by=submitter,
        property_type=PropertyType.HOUSE,
        bedrooms=3,
        bathrooms=2,
        latitude="-15.423456",
        longitude="28.321234",
    )
    defaults.update(kw)
    return Property.objects.create(**defaults)


def make_listing(prop, creator, **kw):
    defaults = dict(
        property=prop,
        created_by=creator,
        transaction_type=TransactionType.RENT,
        price="5000.00",
        currency="ZMW",
        title="3-bed house in Kabulonga",
    )
    defaults.update(kw)
    return Listing.objects.create(**defaults)
