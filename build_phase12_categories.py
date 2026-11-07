#!/usr/bin/env python3
"""NyumbaLink Phase 12: Hero Tabs and Intent Cards."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Intent Cards Component
INTENT_CARDS = '''
import { Link } from 'react-router-dom'

export default function IntentCards() {
  return (
    <div className="bg-[#F8F9FA] py-16 border-b">
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid md:grid-cols-3 gap-6">
          
          {/* Card 1: Buy */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col items-center text-center">
            <div className="w-32 h-32 mb-6 rounded-full bg-blue-50 flex items-center justify-center">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#006AFF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Buy a home</h3>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              Find your place with an immersive photo experience and the most listings, including things you won't find anywhere else.
            </p>
            <Link to="/?type=sale" className="mt-auto px-6 py-2.5 border-2 border-[#006AFF] text-[#006AFF] font-semibold rounded-lg hover:bg-blue-50 transition">
              Browse homes
            </Link>
          </div>

          {/* Card 2: Rent */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col items-center text-center">
            <div className="w-32 h-32 mb-6 rounded-full bg-emerald-50 flex items-center justify-center">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="3" y1="9" x2="21" y2="9"></line>
                <line x1="9" y1="21" x2="9" y2="9"></line>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Rent a home</h3>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              We're creating a seamless online experience – from shopping on the largest rental network, to applying, to paying rent.
            </p>
            <Link to="/?type=rent" className="mt-auto px-6 py-2.5 border-2 border-emerald-600 text-emerald-700 font-semibold rounded-lg hover:bg-emerald-50 transition">
              Find rentals
            </Link>
          </div>

          {/* Card 3: Sell/List */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col items-center text-center">
            <div className="w-32 h-32 mb-6 rounded-full bg-orange-50 flex items-center justify-center">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#EA580C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Sell or List a home</h3>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              No matter what path you take to sell your home, we can help you navigate a successful sale.
            </p>
            <Link to="/dashboard/listings/new" className="mt-auto px-6 py-2.5 border-2 border-orange-500 text-orange-600 font-semibold rounded-lg hover:bg-orange-50 transition">
              List your property
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- 2. Updated Home Page (with Tabs)
HOME_PAGE = '''
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { listingsApi, type ListingFilters, getMediaUrl } from '../api/listings'
import { locationsApi } from '../api/locations'
import { heroApi } from '../api/hero'
import SearchBar from '../components/SearchBar'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import MapView from '../components/MapView'
import RecommendationsSection from '../components/RecommendationsSection'
import AffordabilityCalculator from '../components/AffordabilityCalculator'
import IntentCards from '../components/IntentCards'

export default function HomePage() {
  const [searchParams] = useSearchParams()
  const initialType = searchParams.get('type') === 'sale' ? 'SALE' : searchParams.get('type') === 'rent' ? 'RENT' : undefined
  
  const [filters, setFilters] = useState<ListingFilters>({ transaction_type: initialType })
  const [showFilters, setShowFilters] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid')
  const [affordableBudget, setAffordableBudget] = useState<number | undefined>()
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

  useEffect(() => {
    if (affordableBudget) setFilters(prev => ({ ...prev, max_price: affordableBudget }))
  }, [affordableBudget])

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
      
      {/* HERO SECTION */}
      <div className={`transition-all duration-500 ${viewMode === 'map' ? 'h-40' : 'h-[450px]'}`}>
        {activeHero ? (
          <div className="relative w-full h-full overflow-hidden bg-gray-900">
            {heroData?.results.map((hero: any, idx: number) => (
              <div key={hero.id} className={`absolute inset-0 transition-opacity duration-1000 ${idx === currentSlide ? 'opacity-100' : 'opacity-0'}`}>
                <img src={getMediaUrl(hero.image)} className="w-full h-full object-cover" alt={hero.title} />
                <div className="absolute inset-0 bg-black/40" />
              </div>
            ))}
            
            <div className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
              <h1 className="text-3xl md:text-5xl font-bold text-white mb-4 drop-shadow-lg">{activeHero.title}</h1>
              {viewMode === 'grid' && (
                <p className="text-md md:text-lg text-gray-100 mb-6 max-w-2xl drop-shadow">{activeHero.subtitle}</p>
              )}
              
              <div className="w-full max-w-3xl bg-white p-2 rounded-xl shadow-2xl">
                {/* HERO TABS */}
                <div className="flex border-b mb-2">
                  <button 
                    onClick={() => updateFilter('transaction_type', 'RENT')}
                    className={`px-6 py-3 font-semibold text-sm transition border-b-2 ${filters.transaction_type === 'RENT' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
                  >
                    Rent
                  </button>
                  <button 
                    onClick={() => updateFilter('transaction_type', 'SALE')}
                    className={`px-6 py-3 font-semibold text-sm transition border-b-2 ${filters.transaction_type === 'SALE' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
                  >
                    Buy
                  </button>
                  <button 
                    onClick={() => updateFilter('transaction_type', undefined)}
                    className={`px-6 py-3 font-semibold text-sm transition border-b-2 ${!filters.transaction_type ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
                  >
                    All
                  </button>
                </div>
                <div className="p-1">
                  <SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} />
                </div>
              </div>

            </div>
          </div>
        ) : (
          <div className="w-full h-full bg-emerald-700 flex flex-col items-center justify-center px-4">
             <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Find your place. Connect your world.</h1>
             <div className="w-full max-w-2xl"><SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} /></div>
          </div>
        )}
      </div>

      {/* INTENT CARDS (Buy / Rent / Sell) */}
      <IntentCards />

      {/* ZILLOW FEATURES (Recommendations & Calculator) */}
      <RecommendationsSection />
      <AffordabilityCalculator onBudgetChange={setAffordableBudget} listings={data?.results || []} />

      {/* MAIN CONTENT */}
      <div className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-8">
        
        {/* TOOLBAR */}
        <div className="flex flex-wrap justify-between items-center gap-4 mb-6 border-b pb-4">
          <h2 className="text-2xl font-bold text-gray-900">
            {filters.transaction_type === 'SALE' ? 'Homes for Sale' : filters.transaction_type === 'RENT' ? 'Homes for Rent' : 'All Properties'}
          </h2>
          <div className="flex gap-4">
            <button onClick={() => setShowFilters(!showFilters)} className={`px-4 py-2 rounded border font-medium flex items-center gap-2 ${showFilters ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white text-gray-700'}`}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg> Filters
            </button>
            <div className="flex bg-white rounded border shadow-sm overflow-hidden">
              <button onClick={() => setViewMode('grid')} className={`px-4 py-2 text-sm font-medium ${viewMode === 'grid' ? 'bg-emerald-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>Grid</button>
              <button onClick={() => setViewMode('map')} className={`px-4 py-2 text-sm font-medium ${viewMode === 'map' ? 'bg-emerald-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>Map</button>
            </div>
          </div>
        </div>

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
                <option value="">Any</option><option value="HOUSE">House</option><option value="APARTMENT">Apartment</option><option value="TOWNHOUSE">Townhouse</option><option value="LAND">Land</option>
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
            {viewMode === 'map' ? <MapView listings={data.results} /> : <ListingGrid listings={data.results} />}
          </div>
        )}
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- 3. Write Files

FRONTEND_FILES = {
    "src/components/IntentCards.tsx": INTENT_CARDS,
    "src/pages/HomePage.tsx": HOME_PAGE,
}

def run():
    print(f"NyumbaLink Phase 12 (Categorization) -> {ROOT}\n")
    
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  {rel}")

    print("""
Phase 12 Complete.

Next steps:
  1. Restart your frontend (npm run dev).
  2. Go to http://localhost:5173.
  3. You will see:
     - A beautiful new "Rent | Buy | All" tab switcher inside the hero search box.
     - Three large Zillow-style intent cards below the hero ("Buy a home", "Rent a home", "Sell a home").
  4. Click "Rent a home" or "Buy a home" and watch the page scroll down and instantly filter the results.
  5. The Intent Cards have distinct brand colors (Blue for Buy, Green for Rent, Orange for Sell).
""")

if __name__ == "__main__":
    run()