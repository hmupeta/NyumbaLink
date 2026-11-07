#!/usr/bin/env python3
"""NyumbaLink Phase 10: Interactive Map Search."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Expose Coordinates
SERIALIZERS_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZERS_FILE.read_text(encoding="utf-8")

if "latitude" not in text:
    old_summary = '''        return {
            "id": str(p.id),
            "property_type": p.property_type,
            "bedrooms": p.bedrooms,
            "bathrooms": str(p.bathrooms) if p.bathrooms is not None else None,
            "neighbourhood": p.neighbourhood.name,
        }'''
    
    new_summary = '''        return {
            "id": str(p.id),
            "property_type": p.property_type,
            "bedrooms": p.bedrooms,
            "bathrooms": str(p.bathrooms) if p.bathrooms is not None else None,
            "neighbourhood": p.neighbourhood.name,
            "latitude": float(p.latitude) if p.latitude else None,
            "longitude": float(p.longitude) if p.longitude else None,
        }'''
    
    text = text.replace(old_summary, new_summary)
    SERIALIZERS_FILE.write_text(text, encoding="utf-8")
    print("Patched serializers.py: exposed latitude/longitude in property_summary")

# Seed coordinates for existing demo data
SEED_SCRIPT = '''
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()
from apps.properties.models import Property

# Kabulonga approx coordinates
Property.objects.filter(title__icontains="Kabulonga").update(latitude="-15.423456", longitude="28.321234")
# Woodlands approx coordinates
Property.objects.filter(title__icontains="Woodlands").update(latitude="-15.415678", longitude="28.305123")

print("Updated demo properties with real Lusaka coordinates.")
'''
with open("seed_coords.py", "w") as f:
    f.write(SEED_SCRIPT)
subprocess.run([sys.executable, "seed_coords.py"])
os.remove("seed_coords.py")

# ---------------------------------------------------------------- 2. Frontend: Map Component
MAP_COMPONENT = '''
import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Link } from 'react-router-dom'
import { getMediaUrl } from '../api/listings'
import type { Listing } from '../api/types'

// Fix missing marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// Custom Price Pin CSS
const createPriceIcon = (price: string, currency: string) => {
  return L.divIcon({
    className: 'custom-price-pin',
    html: `<div class="bg-emerald-600 text-white font-bold px-3 py-1 rounded-full text-sm shadow-md border-2 border-white whitespace-nowrap hover:bg-emerald-700 transition cursor-pointer">
            ${currency} ${Number(price).toLocaleString()}
           </div>`,
    iconSize: [80, 30],
    iconAnchor: [40, 15],
  })
}

// Component to recenter map when listings change
function MapBounds({ listings }: { listings: Listing[] }) {
  const map = useMap()
  useEffect(() => {
    const validListings = listings.filter(l => l.property_summary?.latitude && l.property_summary?.longitude)
    if (validListings.length > 0) {
      const bounds = L.latLngBounds(
        validListings.map(l => [l.property_summary.latitude!, l.property_summary.longitude!])
      )
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 })
    }
  }, [listings, map])
  return null
}

export default function MapView({ listings }: { listings: Listing[] }) {
  const validListings = listings.filter(l => l.property_summary?.latitude && l.property_summary?.longitude)
  
  // Default to Lusaka center
  const defaultCenter: [number, number] = [-15.416, 28.283]

  return (
    <div className="w-full h-[calc(100vh-140px)] rounded-lg overflow-hidden shadow-inner border relative z-0">
      <MapContainer center={defaultCenter} zoom={12} scrollWheelZoom={true} className="w-full h-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapBounds listings={validListings} />
        {validListings.map((listing) => (
          <Marker
            key={listing.id}
            position={[listing.property_summary.latitude!, listing.property_summary.longitude!]}
            icon={createPriceIcon(listing.price, listing.currency)}
          >
            <Popup className="zillow-popup">
              <Link to={`/listings/${listing.id}`} className="block w-48 no-underline text-black">
                <img 
                  src={listing.media[0] ? getMediaUrl(listing.media[0].file) : ''} 
                  className="w-full h-24 object-cover rounded-t-md mb-2" 
                  alt={listing.title} 
                />
                <div className="p-1">
                  <p className="font-bold text-sm m-0 truncate">{listing.title}</p>
                  <p className="text-xs text-gray-500 m-0">{listing.property_summary.neighbourhood}</p>
                  <p className="text-emerald-700 font-bold text-sm mt-1 m-0">
                    {listing.currency} {Number(listing.price).toLocaleString()}
                  </p>
                </div>
              </Link>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
'''

# ---------------------------------------------------------------- 3. Frontend: Updated Home Page
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
import MapView from '../components/MapView'

export default function HomePage() {
  const [filters, setFilters] = useState<ListingFilters>({})
  const [showFilters, setShowFilters] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid')
  const [currentSlide, setCurrentSlide] = useState(0)

  const { data: heroData } = useQuery({ queryKey: ['hero-images'], queryFn: heroApi.list })
  const { data: provinces } = useQuery({ queryKey: ['provinces'], queryFn: locationsApi.getProvinces })
  const { data: districts } = useQuery({
    queryKey: ['districts', filters.province],
    queryFn: () => locationsApi.getDistricts(filters.province!),
    enabled: !!filters.province,
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
  })

  useEffect(() => {
    if (!heroData?.results || heroData.results.length <= 1) return
    const interval = setInterval(() => setCurrentSlide(prev => (prev + 1) % heroData.results.length), 5000)
    return () => clearInterval(interval)
  }, [heroData])

  const updateFilter = (key: keyof ListingFilters, value: any) => {
    setFilters(prev => {
      const next = { ...prev, [key]: value || undefined }
      if (key === 'province') next.district = undefined
      return next
    })
  }

  const activeHero = heroData?.results?.[currentSlide]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* HERO SECTION - Shrink if Map View is active to save space */}
      <div className={`transition-all duration-500 ${viewMode === 'map' ? 'h-40' : 'h-[400px]'}`}>
        {activeHero ? (
          <div className="relative w-full h-full overflow-hidden bg-gray-900">
            {heroData?.results.map((hero: any, idx: number) => (
              <div key={hero.id} className={`absolute inset-0 transition-opacity duration-1000 ${idx === currentSlide ? 'opacity-100' : 'opacity-0'}`}>
                <img src={getMediaUrl(hero.image)} className="w-full h-full object-cover" alt={hero.title} />
                <div className="absolute inset-0 bg-black/40" />
              </div>
            ))}
            <div className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
              <h1 className="text-3xl md:text-5xl font-bold text-white mb-2 drop-shadow-lg">{activeHero.title}</h1>
              {viewMode === 'grid' && (
                <p className="text-md md:text-lg text-gray-100 mb-6 max-w-2xl drop-shadow">{activeHero.subtitle}</p>
              )}
              <div className="w-full max-w-2xl">
                <SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} />
              </div>
            </div>
          </div>
        ) : (
          <div className="w-full h-full bg-emerald-700 flex flex-col items-center justify-center px-4">
            <h1 className="text-3xl font-bold text-white mb-4">Find your place. Connect your world.</h1>
            <div className="w-full max-w-2xl">
              <SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} />
            </div>
          </div>
        )}
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-6">
        
        {/* TOOLBAR */}
        <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
          <div className="flex gap-2">
            <button 
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded border font-medium flex items-center gap-2 ${showFilters ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white text-gray-700'}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
              Filters
            </button>
          </div>

          <div className="flex bg-white rounded border shadow-sm overflow-hidden">
            <button 
              onClick={() => setViewMode('grid')}
              className={`px-4 py-2 text-sm font-medium flex items-center gap-2 ${viewMode === 'grid' ? 'bg-emerald-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Grid View
            </button>
            <button 
              onClick={() => setViewMode('map')}
              className={`px-4 py-2 text-sm font-medium flex items-center gap-2 ${viewMode === 'map' ? 'bg-emerald-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Map View
            </button>
          </div>
        </div>

        {/* FILTER PANEL */}
        {showFilters && (
          <div className="bg-white p-6 rounded-lg border shadow-sm mb-6 grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Province</label>
              <select value={filters.province || ''} onChange={(e) => updateFilter('province', e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">All Provinces</option>
                {provinces?.results.map((p: any) => <option key={p.id} value={p.slug}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">District</label>
              <select value={filters.district || ''} onChange={(e) => updateFilter('district', e.target.value)} disabled={!filters.province} className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-100">
                <option value="">All Districts</option>
                {districts?.results.map((d: any) => <option key={d.id} value={d.slug}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Property Type</label>
              <select value={filters.property_type || ''} onChange={(e) => updateFilter('property_type', e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">Any</option>
                <option value="HOUSE">House</option>
                <option value="APARTMENT">Apartment</option>
                <option value="TOWNHOUSE">Townhouse</option>
                <option value="LAND">Land</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Price (ZMW)</label>
              <input type="number" value={filters.max_price || ''} onChange={(e) => updateFilter('max_price', e.target.value)} className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. 10000" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Min Bedrooms</label>
              <input type="number" value={filters.min_bedrooms || ''} onChange={(e) => updateFilter('min_bedrooms', e.target.value)} className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. 2" />
            </div>
          </div>
        )}

        {isLoading && <Loading />}
        {error && <ErrorMessage message="Could not load listings." />}
        
        {data && (
          <div>
            <p className="text-sm text-gray-600 mb-4">{data.count} listing{data.count === 1 ? '' : 's'} found</p>
            
            {viewMode === 'map' ? (
              <MapView listings={data.results} />
            ) : (
              <ListingGrid listings={data.results} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- 4. Execution

FRONTEND_FILES = {
    "src/components/MapView.tsx": MAP_COMPONENT,
    "src/pages/HomePage.tsx": HOME_PAGE,
}

def run():
    print(f"NyumbaLink Phase 10 (Interactive Map) -> {ROOT}\n")
    
    print("1. Installing Frontend Dependencies (Leaflet)...")
    subprocess.run(["npm", "install", "leaflet", "react-leaflet", "@types/leaflet"], cwd=FRONTEND, shell=True)

    print("\n2. Writing frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  {rel}")

    print("""
Phase 10 Complete.

Next steps:
  1. Restart the frontend (npm run dev).
  2. Go to http://localhost:5173.
  3. Above the listings, click the "Map View" toggle.
  4. You will see an interactive OpenStreetMap with custom green price pills.
  5. Click a pill to see a mini property card popup with a photo, title, and price.
  6. Click the popup to go to the listing detail page.
""")

if __name__ == "__main__":
    run()