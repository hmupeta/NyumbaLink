#!/usr/bin/env python3
"""NyumbaLink Phase 19: Landlord Analytics Dashboard."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Add views_count
MODELS_FILE = ROOT / "apps" / "properties" / "models.py"
text = MODELS_FILE.read_text(encoding="utf-8")

if "views_count" not in text:
    # Add views_count to Listing model
    old_model = '''    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    moderation_note = models.TextField(blank=True)'''
    
    new_model = '''    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    moderation_note = models.TextField(blank=True)
    views_count = models.PositiveIntegerField(default=0)'''
    
    text = text.replace(old_model, new_model)
    MODELS_FILE.write_text(text, encoding="utf-8")
    print("Patched models.py: added views_count to Listing")

# Update Serializer
SERIALIZERS_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZERS_FILE.read_text(encoding="utf-8")
if "views_count" not in text:
    text = text.replace(
        '"moderation_note", "media", "is_saved", "created_at", "updated_at",',
        '"moderation_note", "media", "is_saved", "views_count", "created_at", "updated_at",'
    )
    SERIALIZERS_FILE.write_text(text, encoding="utf-8")
    print("Patched serializers.py: exposed views_count")

# Update Views (Add track_view and analytics endpoints)
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "def track_view(self, request, pk=None):" not in text:
    # We add imports
    text = text.replace(
        "from .enums import ListingStatus",
        "from .enums import ListingStatus\nfrom django.db.models import Sum, Count"
    )
    
    # Add actions to ListingViewSet
    text = text.replace(
        '''    @action(detail=False, methods=["get"])
    def recommendations(self, request):''',
        '''    @action(detail=True, methods=["post"])
    def track_view(self, request, pk=None):
        listing = self.get_object()
        # Basic logic: don't track if the owner views it
        if request.user.is_authenticated and listing.created_by == request.user:
            return Response({"status": "ignored"})
        
        listing.views_count += 1
        listing.save(update_fields=["views_count"])
        return Response({"status": "tracked"})

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=403)
        
        # Aggregate data for this landlord
        listings = Listing.objects.filter(created_by=request.user)
        
        total_views = listings.aggregate(total=Sum("views_count"))["total"] or 0
        total_saves = SavedListing.objects.filter(listing__in=listings).count()
        total_unlocks = ContactUnlock.objects.filter(listing__in=listings).count()
        total_conversations = Conversation.objects.filter(listing__in=listings).count()
        
        # Get per-listing stats for the chart
        chart_data = []
        for l in listings:
            chart_data.append({
                "id": str(l.id),
                "title": l.title,
                "views": l.views_count,
                "saves": l.saved_by.count(),
                "unlocks": l.unlocks.count() if hasattr(l, 'unlocks') else 0,
            })

        return Response({
            "totals": {
                "views": total_views,
                "saves": total_saves,
                "unlocks": total_unlocks,
                "conversations": total_conversations
            },
            "chart_data": chart_data
        })

    @action(detail=False, methods=["get"])
    def recommendations(self, request):'''
    )
    
    # Add imports for SavedListing, ContactUnlock, Conversation
    text = text.replace(
        "from .models import HeroImage, Listing, ListingMedia, Property, Report",
        "from .models import HeroImage, Listing, ListingMedia, Property, Report, SavedListing\nfrom apps.payments.models import ContactUnlock\nfrom apps.messaging.models import Conversation"
    )
    
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: added track_view and analytics endpoints")


# ---------------------------------------------------------------- 2. Frontend API
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")
if "trackView" not in text:
    text = text.replace(
        "  getRecommendations: () => api<Listing[]>('/listings/recommendations/'),",
        "  getRecommendations: () => api<Listing[]>('/listings/recommendations/'),\n  trackView: (id: string) => api(`/listings/${id}/track_view/`, { method: 'POST' }),\n  getAnalytics: () => api<any>('/listings/analytics/'),"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("Patched listings.ts: added trackView and getAnalytics")

# ---------------------------------------------------------------- 3. Frontend: Track Views in Detail Page
DETAIL_FILE = FRONTEND / "src" / "pages" / "ListingDetailPage.tsx"
text = DETAIL_FILE.read_text(encoding="utf-8")
if "listingsApi.trackView" not in text:
    # Add useEffect import
    text = text.replace(
        "import { useState } from 'react'",
        "import { useState, useEffect } from 'react'"
    )
    # Add the effect inside the component
    text = text.replace(
        "  const { data: listing, isLoading, error } = useQuery({",
        "  useEffect(() => {\n    if (id) listingsApi.trackView(id).catch(() => {})\n  }, [id])\n\n  const { data: listing, isLoading, error } = useQuery({"
    )
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("Patched ListingDetailPage.tsx: fired trackView API on mount")

# ---------------------------------------------------------------- 4. Frontend: Analytics Page Component
ANALYTICS_PAGE = '''
import { useQuery } from '@tanstack/react-query'
import { listingsApi } from '../api/listings'
import Loading from '../components/Loading'

export default function AnalyticsDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: listingsApi.getAnalytics,
  })

  if (isLoading) return <Loading />
  if (!data) return <p className="text-gray-500">Could not load analytics.</p>

  const { totals, chart_data } = data
  const maxViews = Math.max(...chart_data.map((d: any) => d.views), 1)

  return (
    <div className="space-y-8">
      
      {/* Top Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Views</p>
          <p className="text-3xl font-bold text-gray-900">{totals.views}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Saves</p>
          <p className="text-3xl font-bold text-gray-900">{totals.saves}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Contacts Unlocked</p>
          <p className="text-3xl font-bold text-gray-900">{totals.unlocks}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Inquiries Received</p>
          <p className="text-3xl font-bold text-gray-900">{totals.conversations}</p>
        </div>
      </div>

      {/* Bar Chart */}
      <div className="bg-white border rounded-lg p-6 shadow-sm">
        <h3 className="font-bold text-lg mb-6">Views per Listing</h3>
        <div className="space-y-4">
          {chart_data.map((item: any) => (
            <div key={item.id}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium truncate max-w-xs">{item.title}</span>
                <span className="font-bold">{item.views} views</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div 
                  className="bg-emerald-500 h-3 rounded-full" 
                  style={{ width: `${(item.views / maxViews) * 100}%` }}
                ></div>
              </div>
            </div>
          ))}
          {chart_data.length === 0 && <p className="text-gray-500 text-sm">No listing data yet.</p>}
        </div>
      </div>

    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "AnalyticsDashboard.tsx").write_text(ANALYTICS_PAGE.strip() + "\n", encoding="utf-8")
print("Created src/pages/AnalyticsDashboard.tsx")

# ---------------------------------------------------------------- 5. Update Dashboard Tabs
DASHBOARD_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASHBOARD_FILE.read_text(encoding="utf-8")
if "AnalyticsDashboard" not in text:
    text = text.replace(
        "import ViewingsList from './ViewingsList'",
        "import ViewingsList from './ViewingsList'\nimport AnalyticsDashboard from './AnalyticsDashboard'"
    )
    text = text.replace(
        "const activeTab = searchParams.get('tab') || 'listings'",
        "const activeTab = searchParams.get('tab') || 'listings'"
    )
    
    # Add Analytics Button to Tabs
    old_tabs = '''        <button 
          onClick={() => setSearchParams({ tab: 'viewings' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'viewings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Viewing Requests
        </button>'''
    
    new_tabs = old_tabs + '''
        <button 
          onClick={() => setSearchParams({ tab: 'analytics' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'analytics' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Analytics
        </button>'''
    
    text = text.replace(old_tabs, new_tabs)
    
    # Add Analytics Tab Content
    old_content = '''      ) : (
        <ViewingsList />
      )}
    </div>
  )
}'''
    
    new_content = '''      ) : activeTab === 'viewings' ? (
        <ViewingsList />
      ) : (
        <AnalyticsDashboard />
      )}
    </div>
  )
}'''
    
    text = text.replace(old_content, new_content)
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("Patched DashboardPage.tsx: integrated Analytics tab")

# ---------------------------------------------------------------- 6. Run Migrations
print("\nApplying database migrations...")
subprocess.run([sys.executable, "manage.py", "makemigrations", "properties"])
subprocess.run([sys.executable, "manage.py", "migrate"])

print("""
Phase 19 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log out and view a listing as an anonymous user a few times. (This increments the view count).
  3. Log in as the landlord (demo@nyumbalink.com).
  4. Go to your Dashboard and click the new "Analytics" tab.
  5. You will see your Total Views, Saves, Unlocks, and Inquiries.
  6. Below that, a beautiful CSS bar chart showing which of your listings is getting the most traffic!
""")