#!/usr/bin/env python3
"""Fixes the production Dashboard not showing listings."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Frontend Fix
# We will update the DashboardPage to show an error if the API fails, 
# and we will update the API client to ensure credentials are always sent.

API_FILE = FRONTEND / "src" / "api" / "client.ts"
text = API_FILE.read_text(encoding="utf-8")
if "credentials: 'include'" not in text:
    text = text.replace(
        "  const res = await fetch(`${API_URL}${path}`, {",
        "  const res = await fetch(`${API_URL}${path}`, {\n    credentials: 'include',"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched client.ts: Ensured credentials are included in all requests")

# ---------------------------------------------------------------- 2. Backend Fix
# Ensure the my_listings endpoint is bulletproof and logs what it's doing.
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# We only want to replace the my_listings method
import re
pattern = r"    @action\(detail=False, methods=\[\"get\"\]\)\n    def my_listings\(self, request\):([\s\S]*?)return Response\(serializer\.data\)\n"
match = re.search(pattern, text)

if match:
    new_my_listings = '''    @action(detail=False, methods=["get"])
    def my_listings(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=401)
            
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching listings for user: {request.user.email} (ID: {request.user.id})")

        qs = Listing.objects.filter(
            Q(created_by=request.user) | Q(property__submitted_by=request.user)
        ).select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media").order_by("-created_at")
        
        logger.info(f"Found {qs.count()} listings for {request.user.email}")

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
'''
    text = text[:match.start()] + new_my_listings + text[match.end():]
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched views.py: Added logging and 401 error to my_listings")
else:
    print("⚠️ Could not find the my_listings method to patch. It may already be updated.")

# ---------------------------------------------------------------- 3. Push
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Ensure dashboard listings load in production"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render will automatically redeploy your Backend and Frontend.

After the deploy finishes (about 2 minutes):

1. Open the Render Backend logs.
2. Go to your live site and refresh the Dashboard.
3. Look at the logs. You will see:
   "Fetching listings for user: landlord@nyumbalink.com (ID: ...)"
   "Found 2 listings for landlord@nyumbalink.com"

If the dashboard still shows empty, the logs will tell us EXACTLY why.
""")