#!/usr/bin/env python3
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.properties.models import Property

# We need to match through the listing title
# Kabulonga
kabulonga_props = Property.objects.filter(listings__title__icontains="Kabulonga")
kabulonga_props.update(latitude="-15.423456", longitude="28.321234")
print(f"Updated {kabulonga_props.count()} Kabulonga properties")

# Woodlands
woodlands_props = Property.objects.filter(listings__title__icontains="Woodlands")
woodlands_props.update(latitude="-15.415678", longitude="28.305123")
print(f"Updated {woodlands_props.count()} Woodlands properties")