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
