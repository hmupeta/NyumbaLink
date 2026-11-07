#!/usr/bin/env python3
"""NyumbaLink Phase 9: Hero Carousel & Location Filters."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Hero Images

MODELS_FILE = ROOT / "apps" / "properties" / "models.py"
text = MODELS_FILE.read_text(encoding="utf-8")

if "class HeroImage" not in text:
    HERO_MODEL = '''
class HeroImage(TimeStampedModel):
    title = models.CharField(max_length=128, blank=True, help_text="Optional text overlay")
    subtitle = models.CharField(max_length=256, blank=True)
    image = models.ImageField(upload_to="hero_images/")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta(TimeStampedModel.Meta):
        ordering = ["display_order", "-created_at"]
        verbose_name = "hero image"
        verbose_name_plural = "hero images"

    def __str__(self):
        return self.title or f"Hero #{self.display_order}"
'''
    text += "\n" + HERO_MODEL.strip() + "\n"
    MODELS_FILE.write_text(text, encoding="utf-8")
    print("Patched models.py: added HeroImage")

ADMIN_FILE = ROOT / "apps" / "properties" / "admin.py"
text = ADMIN_FILE.read_text(encoding="utf-8")
if "HeroImageAdmin" not in text:
    text = text.replace(
        "from .models import AuditLog, Listing, ListingMedia, Property, PropertyAuthority, PropertyFeature, Report",
        "from .models import AuditLog, HeroImage, Listing, ListingMedia, Property, PropertyAuthority, PropertyFeature, Report"
    )
    text += '''

@admin.register(HeroImage)
class HeroImageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
'''
    ADMIN_FILE.write_text(text, encoding="utf-8")
    print("Patched admin.py: registered HeroImage")

# Serializers and Views
SERIALIZERS_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZERS_FILE.read_text(encoding="utf-8")
if "HeroImageSerializer" not in text:
    text = text.replace(
        "from .models import Listing, ListingMedia, Property, PropertyFeature",
        "from .models import HeroImage, Listing, ListingMedia, Property, PropertyFeature"
    )
    text += '''

class HeroImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroImage
        fields = ("id", "title", "subtitle", "image", "display_order")
'''
    SERIALIZERS_FILE.write_text(text, encoding="utf-8")
    print("Patched serializers.py: added HeroImageSerializer")

VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")
if "HeroImageViewSet" not in text:
    text = text.replace(
        "from .models import Listing, ListingMedia, Property, Report",
        "from .models import HeroImage, Listing, ListingMedia, Property, Report"
    )
    text = text.replace(
        "    ReportSerializer,\n)",
        "    ReportSerializer,\n    HeroImageSerializer,\n)"
    )
    text += '''

class HeroImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeroImage.objects.filter(is_active=True)
    serializer_class = HeroImageSerializer
    permission_classes = [permissions.AllowAny]
'''
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: added HeroImageViewSet")

URLS_FILE = ROOT / "apps" / "properties" / "urls.py"
text = URLS_FILE.read_text(encoding="utf-8")
if 'router.register("hero-images"' not in text:
    text = text.replace(
        'from .views import ListingMediaViewSet, ListingViewSet, PropertyViewSet, ReportViewSet, SavedListingViewSet',
        'from .views import HeroImageViewSet, ListingMediaViewSet, ListingViewSet, PropertyViewSet, ReportViewSet, SavedListingViewSet'
    )
    text = text.replace(
        'router.register("saved-listings", SavedListingViewSet, basename="saved-listing")',
        'router.register("saved-listings", SavedListingViewSet, basename="saved-listing")\nrouter.register("hero-images", HeroImageViewSet, basename="hero-image")'
    )
    URLS_FILE.write_text(text, encoding="utf-8")
    print("Patched urls.py: mounted HeroImageViewSet")

# ---------------------------------------------------------------- 2. Frontend: APIs

LOCATIONS_API = '''
import { api } from './client'

export const locationsApi = {
  getProvinces: () => api<{results: any[]}>('/provinces/'),
  getDistricts: (provinceSlug: string) => api<{results: any[]}>(`/districts/?province__slug=${provinceSlug}`),
}
'''

HERO_API = '''
import { api } from './client'

export const heroApi = {
  list: () => api<{results: any[]}>('/hero-images/'),
}
'''

HOME_PAGE = '''
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, type ListingFilters, getMediaUrl } from '../api/listings'
import { locationsApi } from '../api/locations'
import { heroApi } from '../api/hero'
import SearchBar from '../components/SearchBar'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function HomePage() {
  const [filters, setFilters] = useState<ListingFilters>({})
  const [showFilters, setShowFilters] = useState(false)
  const [currentSlide, setCurrentSlide] = useState(0)

  // Fetch Hero Images
  const { data: heroData } = useQuery({
    queryKey: ['hero-images'],
    queryFn: heroApi.list,
  })

  // Fetch Provinces for Location Filter
  const { data: provinces } = useQuery({
    queryKey: ['provinces'],
    queryFn: locationsApi.getProvinces,
  })

  // Fetch Districts based on selected Province
  const { data: districts } = useQuery({
    queryKey: ['districts', filters.province],
    queryFn: () => locationsApi.getDistricts(filters.province!),
    enabled: !!filters.province,
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
  })

  // Auto-roll hero carousel
  useEffect(() => {
    if (!heroData?.results || heroData.results.length <= 1) return
    const interval = setInterval(() => {
      setCurrentSlide(prev => (prev + 1) % heroData.results.length)
    }, 5000)
    return () => clearInterval(interval)
  }, [heroData])

  const updateFilter = (key: keyof ListingFilters, value: any) => {
    setFilters(prev => {
      const next = { ...prev, [key]: value || undefined }
      if (key === 'province') next.district = undefined // Reset district when province changes
      return next
    })
  }

  const activeHero = heroData?.results?.[currentSlide]

  return (
    <div className="min-h-screen bg-gray-50">
      
      {/* HERO SECTION */}
      {activeHero ? (
        <div className="relative w-full h-[500px] overflow-hidden bg-gray-900">
          {heroData.results.map((hero: any, idx: number) => (
            <div 
              key={hero.id} 
              className={`absolute inset-0 transition-opacity duration-1000 ${idx === currentSlide ? 'opacity-100' : 'opacity-0'}`}
            >
              <img src={getMediaUrl(hero.image)} className="w-full h-full object-cover" alt={hero.title} />
              <div className="absolute inset-0 bg-black/40" />
            </div>
          ))}
          
          <div className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-4 drop-shadow-lg">
              {activeHero.title || "Find your perfect place"}
            </h1>
            <p className="text-lg md:text-xl text-gray-100 mb-8 max-w-2xl drop-shadow">
              {activeHero.subtitle || "Browse verified listings in Zambia"}
            </p>
            <div className="w-full max-w-2xl">
              <SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} />
            </div>
          </div>

          {/* Carousel Indicators */}
          <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-2 z-20">
            {heroData.results.map((_: any, idx: number) => (
              <button 
                key={idx} onClick={() => setCurrentSlide(idx)}
                className={`w-2 h-2 rounded-full transition-all ${idx === currentSlide ? 'bg-white w-6' : 'bg-white/50'}`}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="w-full py-20 bg-emerald-700 text-center px-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">Find your place. Connect your world.</h1>
          <div className="w-full max-w-2xl mx-auto mt-6">
            <SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} />
          </div>
        </div>
      )}

      {/* SEARCH & FILTERS SECTION */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex gap-4 items-start mb-6">
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded border font-medium flex items-center gap-2 ${showFilters ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white text-gray-700'}`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
            Filters
          </button>
        </div>

        {showFilters && (
          <div className="bg-white p-6 rounded-lg border shadow-sm mb-8 grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Province</label>
              <select 
                value={filters.province || ''} onChange={(e) => updateFilter('province', e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">All Provinces</option>
                {provinces?.results.map((p: any) => (
                  <option key={p.id} value={p.slug}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">District</label>
              <select 
                value={filters.district || ''} onChange={(e) => updateFilter('district', e.target.value)}
                disabled={!filters.province}
                className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
              >
                <option value="">All Districts</option>
                {districts?.results.map((d: any) => (
                  <option key={d.id} value={d.slug}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Property Type</label>
              <select 
                value={filters.property_type || ''} onChange={(e) => updateFilter('property_type', e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">Any</option>
                <option value="HOUSE">House</option>
                <option value="APARTMENT">Apartment</option>
                <option value="TOWNHOUSE">Townhouse</option>
                <option value="LAND">Land</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Price (ZMW)</label>
              <input 
                type="number" min="0" value={filters.max_price || ''} onChange={(e) => updateFilter('max_price', e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. 10000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Min Bedrooms</label>
              <input 
                type="number" min="0" value={filters.min_bedrooms || ''} onChange={(e) => updateFilter('min_bedrooms', e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. 2"
              />
            </div>
          </div>
        )}

        {isLoading && <Loading />}
        {error && <ErrorMessage message="Could not load listings." />}
        {data && (
          <>
            <p className="text-sm text-gray-600 mb-4">{data.count} listing{data.count === 1 ? '' : 's'}</p>
            <ListingGrid listings={data.results} />
          </>
        )}
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- 3. Write files

FRONTEND_FILES = {
    "src/api/locations.ts": LOCATIONS_API,
    "src/api/hero.ts": HERO_API,
    "src/pages/HomePage.tsx": HOME_PAGE,
}

def run():
    print(f"NyumbaLink Phase 9 (Hero & Location) -> {ROOT}\n")
    
    print("Writing frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  {rel}")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "properties"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 9 Complete.

Next steps:
  1. Restart backend (runserver) and frontend (npm run dev).
  2. Go to http://127.0.0.1:8000/admin/ and log in.
  3. Under Properties -> Hero images, upload 2-3 high-quality landscape images.
  4. Go to the Home Page (http://localhost:5173).
  5. You will see a full-screen rolling Hero image.
  6. Click "Filters" and notice the new "Province" and "District" dropdowns. 
     (Selecting Lusaka -> Lusaka will filter only Lusaka properties).
""")

if __name__ == "__main__":
    run()