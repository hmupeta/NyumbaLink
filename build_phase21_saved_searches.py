#!/usr/bin/env python3
"""NyumbaLink Phase 21: Saved Searches & Email Alerts."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Files

MODELS = '''
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class SavedSearch(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=128, help_text="e.g. Houses in Kabulonga")
    
    # Search criteria
    query = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(max_length=16, blank=True)
    property_type = models.CharField(max_length=32, blank=True)
    province = models.CharField(max_length=64, blank=True)
    district = models.CharField(max_length=64, blank=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]
        verbose_name = "saved search"
        verbose_name_plural = "saved searches"

    def __str__(self):
        return f"{self.user.email} - {self.name}"
'''

SIGNALS = '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from apps.properties.models import Listing
from .models import SavedSearch

@receiver(post_save, sender=Listing)
def notify_saved_searches(sender, instance, created, **kwargs):
    # We only care when a listing becomes PUBLISHED
    if instance.status != "PUBLISHED":
        return

    # Find matching saved searches
    matches = SavedSearch.objects.filter(
        models.Q(transaction_type="") | models.Q(transaction_type=instance.transaction_type),
        models.Q(property_type="") | models.Q(property_type=instance.property.type),
    )

    # Filter by price
    matches = matches.filter(
        models.Q(min_price__isnull=True) | models.Q(min_price__lte=instance.price),
        models.Q(max_price__isnull=True) | models.Q(max_price__gte=instance.price),
    )

    # Filter by location
    for search in matches:
        if search.province and search.province.lower() != instance.property.neighbourhood.locality.district.province.name.lower():
            continue
        if search.district and search.district.lower() != instance.property.neighbourhood.locality.district.name.lower():
            continue
        if search.min_bedrooms and instance.property.bedrooms and instance.property.bedrooms < search.min_bedrooms:
            continue
            
        # Send Email (using console backend in development)
        subject = f"New listing matches your saved search: {search.name}"
        message = f"""
Hello {search.user.first_name or search.user.email},

A new property matching your saved search "{search.name}" has just been listed on NyumbaLink!

Title: {instance.title}
Price: {instance.currency} {instance.price}
Location: {instance.property.neighbourhood.name}

View it here: http://localhost:5173/listings/{instance.id}

Best regards,
The NyumbaLink Team
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [search.user.email],
            fail_silently=True,
        )
'''

# Fix the Q import in signals
SIGNALS = SIGNALS.replace("models.Q", "Q").replace("from django.db.models.signals import post_save", "from django.db.models import Q\nfrom django.db.models.signals import post_save")

SERIALIZERS = '''
from rest_framework import serializers
from .models import SavedSearch

class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ("id", "name", "query", "transaction_type", "property_type", "province", "district", "min_price", "max_price", "min_bedrooms", "created_at")
        read_only_fields = ("id", "created_at")
'''

VIEWS = '''
from rest_framework import viewsets, permissions
from .models import SavedSearch
from .serializers import SavedSearchSerializer

class SavedSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
'''

URLS = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SavedSearchViewSet

router = DefaultRouter()
router.register("saved-searches", SavedSearchViewSet, basename="saved-search")
urlpatterns = router.urls
'''

BACKEND_FILES = {
    "apps/search/__init__.py": "",
    "apps/search/apps.py": "from django.apps import AppConfig\n\nclass SearchConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.search'\n    label = 'search'\n\n    def ready(self):\n        import apps.search.signals",
    "apps/search/models.py": MODELS.strip() + "\n",
    "apps/search/signals.py": SIGNALS.strip() + "\n",
    "apps/search/serializers.py": SERIALIZERS.strip() + "\n",
    "apps/search/views.py": VIEWS.strip() + "\n",
    "apps/search/urls.py": URLS.strip() + "\n",
    "apps/search/admin.py": "from django.contrib import admin\nfrom .models import SavedSearch\nadmin.site.register(SavedSearch)\n",
    "apps/search/migrations/__init__.py": "",
}

# ---------------------------------------------------------------- 2. Frontend Files
FRONTEND_API = '''
import { api } from './client'

export const searchApi = {
  list: () => api<{results: any[]}>('/saved-searches/'),
  create: (data: any) => api('/saved-searches/', { method: 'POST', body: JSON.stringify(data) }),
  delete: (id: string) => api(`/saved-searches/${id}/`, { method: 'DELETE' }),
}
'''
(FRONTEND / "src" / "api" / "search.ts").write_text(FRONTEND_API.strip() + "\n", encoding="utf-8")
print("Created src/api/search.ts")

SAVED_SEARCHES_TAB = '''
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { searchApi } from '../api/search'
import Loading from '../components/Loading'

export default function SavedSearchesList() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['saved-searches'],
    queryFn: searchApi.list,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => searchApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['saved-searches'] })
  })

  if (isLoading) return <Loading />

  return (
    <div className="space-y-4">
      {data?.results.length === 0 && (
        <div className="text-center py-12 bg-white rounded border">
          <p className="text-gray-500">You haven't saved any searches yet.</p>
          <Link to="/" className="text-emerald-600 hover:underline mt-2 block">Go to home page to search</Link>
        </div>
      )}
      {data?.results.map((search: any) => (
        <div key={search.id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
          <div>
            <h3 className="font-bold text-lg text-gray-900">{search.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {search.transaction_type || 'Any type'} 
              {search.property_type ? ` · ${search.property_type}` : ''}
              {search.max_price ? ` · Under ${search.max_price}` : ''}
              {search.district ? ` · ${search.district}` : ''}
            </p>
          </div>
          <div className="flex gap-4">
            <Link 
              to={`/?search=${search.query}&type=${search.transaction_type?.toLowerCase()}`}
              className="text-emerald-600 hover:underline font-medium text-sm"
            >
              View Results
            </Link>
            <button 
              onClick={() => deleteMutation.mutate(search.id)}
              className="text-red-500 hover:text-red-700 text-sm font-medium"
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "SavedSearchesList.tsx").write_text(SAVED_SEARCHES_TAB.strip() + "\n", encoding="utf-8")
print("Created src/pages/SavedSearchesList.tsx")

# ---------------------------------------------------------------- 3. Patch HomePage (Save Button)
HOME_FILE = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = HOME_FILE.read_text(encoding="utf-8")

if "Save Search" not in text:
    # Add imports
    text = text.replace(
        "import { useQuery } from '@tanstack/react-query'",
        "import { useQuery, useMutation } from '@tanstack/react-query'\nimport { useAuth } from '../auth/AuthContext'\nimport { searchApi } from '../api/search'"
    )
    text = text.replace(
        "export default function HomePage() {",
        "export default function HomePage() {\n  const { user } = useAuth();"
    )
    
    # Add mutation
    text = text.replace(
        "  const updateFilter = (key: keyof ListingFilters, value: any) => {",
        '''  const saveSearchMutation = useMutation({
    mutationFn: () => {
      const name = filters.search ? `Search: ${filters.search}` : 'Custom Property Search';
      return searchApi.create({
        name,
        query: filters.search || '',
        transaction_type: filters.transaction_type || '',
        property_type: filters.property_type || '',
        district: filters.district || '',
        max_price: filters.max_price || null,
        min_bedrooms: filters.min_bedrooms || null,
      })
    },
    onSuccess: () => alert('Search saved! We will email you when new properties match.'),
    onError: () => alert('Failed to save search. Please log in.')
  })

  const updateFilter = (key: keyof ListingFilters, value: any) => {'''
    )

    # Add Button next to Filters
    old_buttons = '''          <div className="flex gap-2">
            <button 
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded border font-medium flex items-center gap-2 ${showFilters ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white text-gray-700'}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
              Filters
            </button>
          </div>'''
    
    new_buttons = '''          <div className="flex gap-2">
            <button 
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded border font-medium flex items-center gap-2 ${showFilters ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white text-gray-700'}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
              Filters
            </button>
            {user && (
              <button 
                onClick={() => saveSearchMutation.mutate()}
                disabled={saveSearchMutation.isPending}
                className="px-4 py-2 rounded border bg-white border-gray-300 text-gray-700 font-medium hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                Save Search
              </button>
            )}
          </div>'''
    
    text = text.replace(old_buttons, new_buttons)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("Patched HomePage.tsx: added Save Search button")

# ---------------------------------------------------------------- 4. Patch Dashboard
DASHBOARD_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASHBOARD_FILE.read_text(encoding="utf-8")
if "SavedSearchesList" not in text:
    text = text.replace(
        "import ViewingsList from './ViewingsList'",
        "import ViewingsList from './ViewingsList'\nimport SavedSearchesList from './SavedSearchesList'"
    )
    text = text.replace(
        "const activeTab = searchParams.get('tab') || 'listings'",
        "const activeTab = searchParams.get('tab') || 'listings'"
    )
    # Add Tab Button
    old_tabs = '''        <button 
          onClick={() => setSearchParams({ tab: 'analytics' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'analytics' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Analytics
        </button>'''
    
    new_tabs = old_tabs + '''
        <button 
          onClick={() => setSearchParams({ tab: 'searches' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'searches' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Saved Searches
        </button>'''
    
    text = text.replace(old_tabs, new_tabs)
    
    # Add Tab Content
    old_content = '''      ) : (
        <AnalyticsDashboard />
      )}'''
    new_content = '''      ) : activeTab === 'analytics' ? (
        <AnalyticsDashboard />
      ) : (
        <SavedSearchesList />
      )}'''
    
    text = text.replace(old_content, new_content)
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("Patched DashboardPage.tsx: added Saved Searches tab")

# ---------------------------------------------------------------- 5. Execute
def run():
    print(f"NyumbaLink Phase 21 (Saved Searches) -> {ROOT}\n")

    print("Writing backend files:")
    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nPatching settings and urls:")
    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.search"' not in text:
        text = text.replace('    "apps.notifications",\n', '    "apps.notifications",\n    "apps.search",\n')
        # Also ensure email backend is console for dev
        if 'EMAIL_BACKEND' not in text:
            text += '\nEMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"\nDEFAULT_FROM_EMAIL = "alerts@nyumbalink.com"\n'
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")

    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.search.urls")' not in text:
        text = text.replace(
            'path("api/v1/", include("apps.notifications.urls")),\n',
            'path("api/v1/", include("apps.notifications.urls")),\n    path("api/v1/", include("apps.search.urls")),\n'
        )
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "search"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 21 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as a standard user (seeker@nyumbalink.com).
  3. On the Home Page, apply some filters (e.g., Max Price 10,000).
  4. Click the new "Save Search" button.
  5. Go to your Dashboard -> "Saved Searches" tab to see it listed.
  6. Log out, and log in as a Landlord (demo@nyumbalink.com).
  7. Create a NEW listing that matches the seeker's criteria, and approve it in Moderation so it becomes PUBLISHED.
  8. Look at your backend terminal: You will see a formatted EMAIL printed in the console (simulating an email being sent to the seeker).
""")

if __name__ == "__main__":
    run()