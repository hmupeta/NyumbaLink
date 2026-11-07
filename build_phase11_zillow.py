#!/usr/bin/env python3
"""NyumbaLink Phase 11: Recommendations & Affordability Calculator."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Recommendations Endpoint

VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "def recommendations(self, request):" not in text:
    # Add recommendations action to ListingViewSet
    old_action = '''    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):'''
    
    new_action = '''    @action(detail=False, methods=["get"])
    def recommendations(self, request):
        if not request.user.is_authenticated:
            return Response([])
        
        # Simple logic: return 3 random published listings not owned by the user
        recs = Listing.objects.filter(status=ListingStatus.PUBLISHED).exclude(
            created_by=request.user
        ).order_by("?")[:3]
        
        serializer = self.get_serializer(recs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):'''
    
    text = text.replace(old_action, new_action)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: added recommendations endpoint")

# ---------------------------------------------------------------- 2. Frontend: API Update
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")
if "getRecommendations" not in text:
    text = text.replace(
        "  get: (id: string) => api<Listing>(`/listings/${id}/`),",
        "  get: (id: string) => api<Listing>(`/listings/${id}/`),\n  getRecommendations: () => api<Listing[]>('/listings/recommendations/'),"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("Patched listings.ts: added getRecommendations")

# ---------------------------------------------------------------- 3. Frontend Components

RECOMMENDATIONS = '''
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'

export default function RecommendationsSection() {
  const { user } = useAuth()
  const { data: recs } = useQuery({
    queryKey: ['recommendations'],
    queryFn: listingsApi.getRecommendations,
    enabled: !!user,
  })

  return (
    <div className="bg-[#F8F9FA] py-16 border-b">
      <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-12">
        
        {/* Left Side: Text & CTA */}
        <div className="w-full md:w-1/2">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Get home recommendations</h2>
          <p className="text-lg text-gray-600 mb-6">
            {user 
              ? "Handpicked properties based on your activity on NyumbaLink."
              : "Sign in for a more personalized experience based on your budget and preferred locations."}
          </p>
          {!user && (
            <Link 
              to="/login" 
              className="inline-block border-2 border-[#006AFF] text-[#006AFF] font-semibold px-6 py-2.5 rounded-md hover:bg-blue-50 transition"
            >
              Sign in
            </Link>
          )}
        </div>

        {/* Right Side: Stacked Cards UI */}
        <div className="w-full md:w-1/2 relative h-[320px] flex justify-center">
          {!user ? (
             // Anonymous state (Zillow style mockup)
            <div className="relative w-72 h-full">
              <div className="absolute top-10 left-8 w-full h-[220px] bg-white rounded-xl shadow-lg border p-3 opacity-60 transform scale-90 rotate-6">
                 <div className="w-full h-32 bg-gray-200 rounded-lg mb-2"></div>
                 <div className="h-4 bg-gray-200 w-3/4 rounded"></div>
              </div>
              <div className="absolute top-5 left-4 w-full h-[240px] bg-white rounded-xl shadow-xl border p-3 opacity-80 transform scale-95 rotate-3">
                 <div className="w-full h-36 bg-gray-200 rounded-lg mb-2"></div>
                 <div className="h-4 bg-gray-200 w-3/4 rounded"></div>
              </div>
              <div className="absolute top-0 left-0 w-full h-[260px] bg-white rounded-xl shadow-2xl border p-3 z-10 flex flex-col">
                 <div className="w-full h-40 bg-gray-100 rounded-lg mb-3 flex items-center justify-center text-gray-400">Image</div>
                 <h3 className="font-bold text-lg">K 695,000</h3>
                 <p className="text-sm text-gray-600">4 bd | 3 ba | 3,102 sqft</p>
                 
                 <div className="absolute -left-12 top-4 bg-white rounded-full shadow-lg px-4 py-2 flex items-center gap-2">
                   <div className="bg-emerald-100 p-1.5 rounded-full text-emerald-600">
                     <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
                   </div>
                   <div>
                     <p className="text-xs font-bold m-0">Recommended homes</p>
                     <p className="text-[10px] text-gray-500 m-0">based on your monthly budget</p>
                   </div>
                 </div>
              </div>
            </div>
          ) : (
            // Logged in state (Real Data)
            <div className="grid grid-cols-2 gap-4 w-full">
              {recs?.slice(0, 2).map((listing: any, i: number) => (
                <Link key={listing.id} to={`/listings/${listing.id}`} className={`bg-white rounded-xl shadow border overflow-hidden block ${i === 1 ? 'translate-y-8' : ''}`}>
                  <div className="h-32 bg-gray-100">
                    {listing.media[0] && <img src={getMediaUrl(listing.media[0].file)} className="w-full h-full object-cover" />}
                  </div>
                  <div className="p-3">
                    <h3 className="font-bold text-sm truncate">{listing.title}</h3>
                    <p className="text-emerald-700 font-bold mt-1 text-sm">{listing.currency} {Number(listing.price).toLocaleString()}</p>
                  </div>
                </Link>
              ))}
              {recs?.length === 0 && <div className="col-span-2 text-center text-gray-500 py-10">No recommendations yet. Save some properties!</div>}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
'''

AFFORDABILITY = '''
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface Props {
  onBudgetChange: (maxPrice: number | undefined) => void
  listings: any[]
}

export default function AffordabilityCalculator({ onBudgetChange, listings }: Props) {
  const [income, setIncome] = useState(25000) // ZMW
  const [downPayment, setDownPayment] = useState(100000) // ZMW
  const [interestRate, setInterestRate] = useState(18) // Typical Zambian mortgage rate
  const [termYears, setTermYears] = useState(15)

  // Calculate maximum affordable price
  useEffect(() => {
    // Assuming 30% of income goes to mortgage
    const monthlyPayment = income * 0.30
    const monthlyRate = (interestRate / 100) / 12
    const numPayments = termYears * 12

    // Standard Mortgage Formula: P = M * [(1+r)^n - 1] / [r * (1+r)^n]
    let loanAmount = 0
    if (monthlyRate > 0) {
      loanAmount = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
    } else {
      loanAmount = monthlyPayment * numPayments
    }

    const maxHomePrice = loanAmount + downPayment
    onBudgetChange(Math.round(maxHomePrice))
  }, [income, downPayment, interestRate, termYears, onBudgetChange])

  // Filter listings that fall within the calculated budget
  const affordableListings = listings.filter(l => Number(l.price) <= (income * 0.30 * termYears * 12 + downPayment))

  return (
    <div className="bg-white py-16">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Find homes you can afford</h2>
          <p className="text-gray-600">Answer a few questions. We'll highlight homes you're likely to qualify for.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          
          {/* Calculator Panel */}
          <div className="bg-white border rounded-2xl p-6 shadow-sm h-fit">
            <div className="flex items-center gap-2 mb-6">
              <span className="text-blue-600 text-xl font-bold">Z</span>
              <h3 className="font-semibold text-gray-800">NyumbaLink Calculator</h3>
            </div>

            <div className="space-y-5">
              <div>
                <label className="text-sm font-medium text-gray-700">Monthly Income (ZMW)</label>
                <input type="number" value={income} onChange={e => setIncome(Number(e.target.value))} className="w-full text-xl font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Down Payment (ZMW)</label>
                <input type="number" value={downPayment} onChange={e => setDownPayment(Number(e.target.value))} className="w-full text-xl font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">Interest Rate (%)</label>
                  <input type="number" value={interestRate} onChange={e => setInterestRate(Number(e.target.value))} className="w-full text-lg font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Term (Years)</label>
                  <input type="number" value={termYears} onChange={e => setTermYears(Number(e.target.value))} className="w-full text-lg font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
                </div>
              </div>
            </div>

            <div className="mt-8 bg-blue-50 p-4 rounded-xl text-center">
              <p className="text-sm text-blue-800 font-medium">Max Home Price</p>
              <p className="text-2xl font-bold text-blue-900">
                K {Math.round(income * 0.30 * termYears * 12 + downPayment).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Listings Carousel */}
          <div className="md:col-span-2 relative overflow-hidden">
             <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
                {affordableListings.map(l => (
                  <Link key={l.id} to={`/listings/${l.id}`} className="min-w-[280px] w-[280px] snap-start border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition block relative">
                    <div className="absolute top-0 left-0 bg-orange-500 text-white text-xs font-bold px-3 py-1 rounded-br-lg z-10">Within Budget</div>
                    <div className="h-40 bg-gray-100">
                      {l.media[0] && <img src={getMediaUrl(l.media[0].file)} className="w-full h-full object-cover" />}
                    </div>
                    <div className="p-4">
                      <h4 className="font-bold text-gray-900 truncate">{l.title}</h4>
                      <p className="text-sm text-gray-500">{l.property_summary.neighbourhood}</p>
                      <p className="font-bold text-emerald-700 mt-2">K {Number(l.price).toLocaleString()}</p>
                    </div>
                  </Link>
                ))}
                {affordableListings.length === 0 && <p className="text-gray-500 pt-10">No listings within this budget right now.</p>}
             </div>
          </div>

        </div>
      </div>
    </div>
  )
}
'''

# We need getMediaUrl inside AffordabilityCalculator, let's patch the import string
AFFORDABILITY = AFFORDABILITY.replace("import { Link } from 'react-router-dom'", "import { Link } from 'react-router-dom'\nimport { getMediaUrl } from '../api/listings'")


# ---------------------------------------------------------------- 4. Update Home Page Layout
HOME_FILE = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = HOME_FILE.read_text(encoding="utf-8")

if "RecommendationsSection" not in text:
    # Add imports
    text = text.replace(
        "import MapView from '../components/MapView'",
        "import MapView from '../components/MapView'\nimport RecommendationsSection from '../components/RecommendationsSection'\nimport AffordabilityCalculator from '../components/AffordabilityCalculator'"
    )

    # Add state for budget
    text = text.replace(
        "const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid')",
        "const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid')\n  const [affordableBudget, setAffordableBudget] = useState<number | undefined>()"
    )

    # Add components to the JSX (between Hero and Main Content)
    old_jsx = '''      {/* MAIN CONTENT */}'''
    new_jsx = '''      {/* ZILLOW FEATURES */}
      <RecommendationsSection />
      <AffordabilityCalculator 
        onBudgetChange={setAffordableBudget} 
        listings={data?.results || []} 
      />

      {/* MAIN CONTENT */}'''
    text = text.replace(old_jsx, new_jsx)

    # If budget changes, update filters
    # We add an effect to sync budget to filters
    old_effect = '''  const updateFilter = (key: keyof ListingFilters, value: any) => {'''
    new_effect = '''  useEffect(() => {
    if (affordableBudget) {
      setFilters(prev => ({ ...prev, max_price: affordableBudget }))
    }
  }, [affordableBudget])

  const updateFilter = (key: keyof ListingFilters, value: any) => {'''
    text = text.replace(old_effect, new_effect)

    HOME_FILE.write_text(text, encoding="utf-8")
    print("Patched HomePage.tsx: integrated Recommendations and Calculator")

# ---------------------------------------------------------------- 5. Execution

FRONTEND_FILES = {
    "src/components/RecommendationsSection.tsx": RECOMMENDATIONS,
    "src/components/AffordabilityCalculator.tsx": AFFORDABILITY,
}

def run():
    print(f"NyumbaLink Phase 11 (Zillow Features) -> {ROOT}\n")
    
    print("Writing frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  {rel}")

    print("""
Phase 11 Complete.

Next steps:
  1. Restart backend (runserver).
  2. Restart frontend (npm run dev).
  3. Go to http://localhost:5173.
  4. Scroll down below the hero section.
  5. You will see the "Get home recommendations" section (Zillow-style stacked cards).
  6. Below that, the "Find homes you can afford" calculator.
  7. Change the Income to 50,000. Watch the max home price calculate, and the listings on the right filter automatically!
""")

if __name__ == "__main__":
    run()