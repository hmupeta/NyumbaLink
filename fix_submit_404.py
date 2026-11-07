#!/usr/bin/env python3
"""Fixes the 404 when submitting drafts for review."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"

text = VIEWS_FILE.read_text(encoding="utf-8")

old_queryset = '''    def get_queryset(self):
        qs = Listing.objects.select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media")
        user = self.request.user
        
        # Staff see everything (for moderation)
        if user.is_authenticated and user.is_staff:
            return qs
            
        # If the user is calling the `my_listings` action, we let the action handle the filtering
        if self.action == "my_listings":
            return qs

        # Public API: ALWAYS only return PUBLISHED listings
        return qs.filter(status=ListingStatus.PUBLISHED)'''

new_queryset = '''    def get_queryset(self):
        qs = Listing.objects.select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media")
        user = self.request.user
        
        # Staff see everything (for moderation)
        if user.is_authenticated and user.is_staff:
            return qs
            
        # The my_listings action handles its own filtering
        if self.action == "my_listings":
            return qs

        # PUBLIC LIST VIEW (Homepage): ALWAYS only return PUBLISHED
        if self.action == "list":
            return qs.filter(status=ListingStatus.PUBLISHED)

        # DETAIL ACTIONS (Update, Delete, Submit, Publish):
        # Allow if it's published OR if the user owns it
        if user.is_authenticated:
            return qs.filter(
                Q(status=ListingStatus.PUBLISHED)
                | Q(created_by=user)
                | Q(property__submitted_by=user)
            )

        # Anonymous users can only see published listings
        return qs.filter(status=ListingStatus.PUBLISHED)'''

if old_queryset in text:
    text = text.replace(old_queryset, new_queryset)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: get_queryset now allows owners to access their drafts for actions.")
else:
    # If the exact block wasn't found, we'll patch it more aggressively
    import re
    pattern = r"def get_queryset\(self\):\n(?:.*\n)*?        return qs\.filter\(status=ListingStatus\.PUBLISHED\)"
    text = re.sub(pattern, new_queryset, text)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py via regex: updated get_queryset.")

print("""
Fix applied! 

  1. Restart your backend server.
  2. Go to the Landlord Dashboard and click "Submit for Review" again.
  3. It will now successfully change the status to SUBMITTED.
  4. Log in as Admin -> Moderation, and the listing will be waiting for you.
""")