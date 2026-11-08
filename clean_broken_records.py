# Save as clean_broken_records.py
import os, sys, re, django
from getpass import getpass

RENDER_DB_URL = getpass("Paste your Render External Database URL: ").strip()
match = re.search(r"(postgres(?:ql)?://[^\s]+)", RENDER_DB_URL)
if not match: sys.exit(1)

os.environ["DATABASE_URL"] = match.group(1)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
django.setup()

from apps.properties.models import ListingMedia

def clean():
    deleted = 0
    for media in ListingMedia.objects.all():
        # If it's not a proper URL (meaning it's a broken local path), delete it
        if not str(media.file.name).startswith('http'):
            print(f"Deleting broken record: {media.file.name}")
            media.delete()
            deleted += 1
    print(f"Deleted {deleted} broken records.")

if __name__ == "__main__":
    clean()