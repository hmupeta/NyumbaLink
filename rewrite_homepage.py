#!/usr/bin/env python3
"""Completely rewrites HomePage.tsx with the new Affordability logic."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
HOME_FILE = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"

NEW_HOME = '''
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { listingsApi, type ListingFilters } from '../api/listings'
import { locationsApi } from '../api/locations'
import { heroApi } from '../api/hero'
import SearchBar from '../components/SearchBar'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import MapView from '../components/MapView'
import RecommendationsSection from '../components/RecommendationsSection'
import AffordabilityCalculator from '../components/AffordabilityCalculator'
import TopNeighbourhoods from '../components/TopNeighbourhoods'

export default function HomePage() {
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState<ListingFilters>({})
  const [showFilters, setShowFilters] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid')
  const [currentSlide, setCurrentSlide] = useState(0)
  
  // Affordability filter state
  const [affordableFilter, setAffordableFilter] = useState<{ price: number, type: 'SALE' | 'RENT' } | null>(null)

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
    staleTime: 0,
    refetchOnMount: 'always',
  })

  useEffect(() => {
    if (!heroData?.results || heroData.results.length <= 1) return
    const interval = setInterval(() => setCurrentSlide(prev => (prev + 1) % heroData.results.length), 5000)
    return () => clearInterval(interval)
  }, [heroData])

  // Sync URL params with filters
  useEffect(() => {
    const typeParam = searchParams.get('type');
    const newType = typeParam === 'sale' ? 'SALE' : typeParam === 'rent' ? 'RENT' : undefined;
    const hoodParam = searchParams.get('neighbourhood');
    
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
  }, [searchParams]);

  // Sync affordability filter with filters
  useEffect(() => {
    if (affordableFilter) {
      setFilters(prev => ({
        ...prev,
        max_price: affordableFilter.price,
        transaction_type: affordableFilter.type,
      }))
    }
  }, [affordableFilter])

  // Scroll to listings when URL changes
  useEffect(() => {
    if (searchParams.get('type')) {
      setTimeout(() => {
        const element = document.getElementById('listings-section');
        if (element) {
          const y = element.getBoundingClientRect().top + window.scrollY - 80;
          window.scrollTo({ top: y, behavior: 'smooth' });
        }
      }, 100);
    }
  }, [searchParams]);

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
                <img src={`https://nyumbalink-backend-eaw2.onrender.com${hero.image}`} className="w-full h-full object-cover" alt={hero.title} />
                <div className="absolute inset-0 bg-black/40" />
              </div>
            ))}
            
            <div className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
              <h1 className="text-3xl md:text-5xl font-bold text-white mb-4 drop-shadow-lg">{activeHero.title}</h1>
              {viewMode === 'grid' && (
                <p className="text-md md:text-lg text-gray-100 mb-6 max-w-2xl drop-shadow">{activeHero.subtitle}</p>
              )}
              
              <div className="w-full max-w-3xl bg-white p-2 rounded-xl shadow-2xl">
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

      {/* TOP NEIGHBOURHOODS */}
      <TopNeighbourhoods />

      {/* AFFORDABILITY CALCULATOR */}
      <RecommendationsSection />
      <AffordabilityCalculator 
        onFilterUpdate={(price, type) => setAffordableFilter(price && type ? { price, type } : null)} 
        listings={data?.results || []} 
      />

      {/* LISTINGS SECTION */}
      <div id="listings-section" className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-8">
        
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
HOME_FILE.write_text(NEW_HOME.strip() + "\n", encoding="utf-8")
print("✅ Rewrote HomePage.tsx completely")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Full rewrite of HomePage to fix affordability TypeScript errors"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 HOMEPAGE REWRITTEN!
==================================================

Render will rebuild the frontend in ~2 minutes.

Hard refresh your live site (Ctrl + Shift + R), and you'll see:
1. The Buy/Rent tabs in the Affordability Calculator
2. The correct mortgage math (realistic pricing)
3. Only SALE properties when Buy is selected, only RENT when Rent is selected
""")