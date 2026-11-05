from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.properties.models import PropertyFeature

FEATURES = [
    ("Parking", "parking"), ("Garage", "parking"),
    ("Borehole", "utilities"), ("Municipal water", "utilities"),
    ("Solar backup", "utilities"), ("Generator", "utilities"),
    ("ZESCO power", "utilities"), ("Fibre internet", "utilities"),
    ("Swimming pool", "amenities"), ("Gym", "amenities"),
    ("Garden", "amenities"), ("Balcony", "amenities"),
    ("Furnished", "amenities"), ("Air conditioning", "amenities"),
    ("Security guard", "security"), ("Electric fence", "security"),
    ("Gated community", "security"), ("CCTV", "security"),
    ("Pet friendly", "policy"), ("Wheelchair accessible", "policy"),
]


class Command(BaseCommand):
    help = "Seed common property features."

    def handle(self, *args, **options):
        created = 0
        for name, category in FEATURES:
            _, was_created = PropertyFeature.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "category": category}
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new features."))
