#!/usr/bin/env python3
"""Fixes the bug where Draft listings appear on the public Home Page."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Fix
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

old_queryset = '''    def get_queryset(self):
        qs = Listing.objects.select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media")
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(
                Q(status=ListingStatus.PUBLISHED)
                | Q(created_by=user)
                | Q(property__submitted_by=user)
            )
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
            
        # If the user is calling the `my_listings` action, we let the action handle the filtering
        if self.action == "my_listings":
            return qs

        # Public API: ALWAYS only return PUBLISHED listings
        return qs.filter(status=ListingStatus.PUBLISHED)'''

# Replace the queryset
text = text.replace(old_queryset, new_queryset)

# Add the dedicated my_listings action
if "def my_listings(self, request):" not in text:
    old_action = '''    @action(detail=False, methods=["get"])
    def recommendations(self, request):'''
    
    new_action = '''    @action(detail=False, methods=["get"])
    def my_listings(self, request):
        if not request.user.is_authenticated:
            return Response([])
            
        qs = Listing.objects.filter(
            Q(created_by=request.user) | Q(property__submitted_by=request.user)
        ).select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media").order_by("-created_at")
        
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def recommendations(self, request):'''
    
    text = text.replace(old_action, new_action)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: separated public listings from dashboard listings")

# ---------------------------------------------------------------- 2. Frontend API
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")
if "getMyListings" not in text:
    text = text.replace(
        "  getRecommendations: () => api<Listing[]>('/listings/recommendations/'),",
        "  getRecommendations: () => api<Listing[]>('/listings/recommendations/'),\n  getMyListings: () => api<Paginated<Listing>>('/listings/my_listings/'),"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("Patched listings.ts: added getMyListings")

# ---------------------------------------------------------------- 3. Frontend Dashboard
DASHBOARD_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASHBOARD_FILE.read_text(encoding="utf-8")

if "listingsApi.getMyListings" not in text:
    # Change the query to use the new endpoint
    text = text.replace(
        "    queryFn: () => listingsApi.list({ page: 1 }),",
        "    queryFn: () => listingsApi.getMyListings(),"
    )
    # Remove the old client-side filter, because the backend already does it
    text = text.replace(
        "  const myListings = data?.results.filter(l => l.created_by === user?.id) || []",
        "  const myListings = data?.results || []"
    )
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("Patched DashboardPage.tsx: updated to use getMyListings")

print("""
Fix applied! 

  1. Restart your backend server (this is crucial for the new endpoint to load).
  2. Refresh your frontend.
  3. Go to the Home Page. The "Modern 2 Bed-roomed Flats" draft will disappear.
  4. Go to your Dashboard. It will still show all 3 listings (Draft, Published, Published) because it uses the new secure dashboard API.
""")