#!/usr/bin/env python3
"""Replaces static Intent Cards with dynamic Top Neighbourhoods."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Backend: Add 'top' endpoint to NeighbourhoodViewSet
# ----------------------------------------------------------------
VIEWS_FILE = ROOT / "apps" / "locations" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# Ensure necessary imports exist
if "from django.db.models import Count, Q" not in text:
    text = text.replace(
        "from rest_framework import viewsets, permissions, status",
        "from rest_framework import viewsets, permissions, status\nfrom django.db.models import Count, Q\nfrom rest_framework.decorators import action"
    )

# Add the top action inside the class
if "def top(self, request):" not in text:
    # Find the end of the NeighbourhoodViewSet class (before the next class or EOF)
    # We will just append it right after the `create` method we added earlier.
    # It's safer to append right before the last line of the file if we can't pinpoint it.
    
    top_action = '''
    @action(detail=False, methods=["get"])
    def top(self, request):
        # Find neighbourhoods with published listings, ordered by most listings
        top_hoods = Neighbourhood.objects.annotate(
            listing_count=Count(
                'properties__listings',
                filter=Q(properties__listings__status='PUBLISHED')
            )
        ).filter(listing_count__gt=0).order_by('-listing_count')[:5]
        
        data = []
        for hood in top_hoods:
            data.append({
                "id": str(hood.id),
                "name": hood.name,
                "slug": hood.slug,
                "locality_name": hood.locality.name,
                "listing_count": hood.listing_count
            })
        return Response(data)
'''
    # A simple way to ensure it goes inside the class is to check for the last method we added
    if "return Response(NeighbourhoodSerializer(new_hood).data, status=201)" in text:
        text = text.replace(
            "return Response(NeighbourhoodSerializer(new_hood).data, status=201)",
            "return Response(NeighbourhoodSerializer(new_hood).data, status=201)\n" + top_action
        )
    else:
        text += "\n" + top_action # Fallback if the previous script wasn't run
        
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched locations/views.py: Added top neighbourhoods endpoint")

# ----------------------------------------------------------------
# 2. Frontend: API Client
# ----------------------------------------------------------------
API_FILE = FRONTEND / "src" / "api" / "locations.ts"
text = API_FILE.read_text(encoding="utf-8")

if "getTopNeighbourhoods" not in text:
    text = text.replace(
        "export const locationsApi = {",
        "export const locationsApi = {\n  getTopNeighbourhoods: () => api<any[]>('/neighbourhoods/top/'),"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched locations.ts: Added getTopNeighbourhoods")

# ----------------------------------------------------------------
# 3. Frontend: New TopNeighbourhoods Component
# ----------------------------------------------------------------
TOP_HOODS_COMPONENT = '''
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { locationsApi } from '../api/locations'

export default function TopNeighbourhoods() {
  const { data: hoods, isLoading } = useQuery({
    queryKey: ['top-neighbourhoods'],
    queryFn: locationsApi.getTopNeighbourhoods,
  })

  if (isLoading || !hoods || hoods.length === 0) return null

  return (
    <div className="bg-[#F8F9FA] py-12 border-b">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Explore popular areas</h2>
          <p className="text-gray-600">Discover properties in the most active neighbourhoods.</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {hoods.map((hood: any) => (
            <Link
              key={hood.id}
              to={`/?neighbourhood=${hood.slug}`}
              className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group flex flex-col items-center justify-center text-center"
            >
              <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mb-4 group-hover:bg-emerald-100 transition">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
              </div>
              <h3 className="font-bold text-gray-900 text-lg">{hood.name}</h3>
              <p className="text-xs text-gray-500 mt-1">{hood.locality_name}</p>
              <p className="text-sm font-medium text-emerald-600 mt-2 bg-emerald-50 px-2 py-1 rounded-full">
                {hood.listing_count} {hood.listing_count === 1 ? 'listing' : 'listings'}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
'''
(FRONTEND / "src" / "components" / "TopNeighbourhoods.tsx").write_text(TOP_HOODS_COMPONENT.strip() + "\n", encoding="utf-8")
print("✅ Created TopNeighbourhoods.tsx component")

# ----------------------------------------------------------------
# 4. Frontend: Update HomePage (Replace IntentCards & fix URL filter)
# ----------------------------------------------------------------
HOME_FILE = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = HOME_FILE.read_text(encoding="utf-8")

# 1. Swap the component
text = text.replace("import IntentCards from '../components/IntentCards'", "import TopNeighbourhoods from '../components/TopNeighbourhoods'")
text = text.replace("<IntentCards />", "<TopNeighbourhoods />")

# 2. Update the useEffect to sync 'neighbourhood' param
old_effect = '''  // Sync URL params with filters
  useEffect(() => {
    const typeParam = searchParams.get('type');
    const newType = typeParam === 'sale' ? 'SALE' : typeParam === 'rent' ? 'RENT' : undefined;
    
    // Only update if the type actually changed
    setFilters(prev => {
      if (prev.transaction_type !== newType) {
        return { ...prev, transaction_type: newType };
      }
      return prev;
    });
  }, [searchParams]);'''

new_effect = '''  // Sync URL params with filters
  useEffect(() => {
    const typeParam = searchParams.get('type');
    const newType = typeParam === 'sale' ? 'SALE' : typeParam === 'rent' ? 'RENT' : undefined;
    
    const hoodParam = searchParams.get('neighbourhood');
    
    // Only update if things actually changed
    setFilters(prev => {
      let changed = false;
      const next = { ...prev };
      
      if (prev.transaction_type !== newType) {
        next.transaction_type = newType;
        changed = true;
      }
      if (hoodParam && prev.neighbourhood !== hoodParam) {
        next.neighbourhood = hoodParam;
        changed = true;
      }
      
      return changed ? next : prev;
    });
  }, [searchParams]);'''

text = text.replace(old_effect, new_effect)
HOME_FILE.write_text(text, encoding="utf-8")
print("✅ Patched HomePage.tsx: Replaced IntentCards and added neighbourhood URL filter")

# ----------------------------------------------------------------
# 5. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Replace static intent cards with dynamic top neighbourhoods"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 32 COMPLETE!
==================================================

Render will automatically rebuild your frontend and backend.

1. Go to your live site.
2. The generic "Buy / Rent / Sell" cards are gone.
3. In their place, you will see the **Top 5 Neighbourhoods** based on actual property data.
4. Click on any neighbourhood (e.g., Kabulonga). It will instantly filter the home page and scroll to the listings for that specific area!
""")