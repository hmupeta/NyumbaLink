#!/usr/bin/env python3
"""NyumbaLink Phase 8: Advanced Search, Filters, and Saved Listings."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Models & Views

SAVED_MODEL = '''
class SavedListing(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_listings")
    listing = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="saved_by")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "saved listing"
        verbose_name_plural = "saved listings"
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="uniq_user_saved_listing"),
        ]

    def __str__(self):
        return f"{self.user.email} saved {self.listing.title}"
'''

# We inject this into apps/properties/models.py
MODELS_FILE = ROOT / "apps" / "properties" / "models.py"
text = MODELS_FILE.read_text(encoding="utf-8")
if "class SavedListing" not in text:
    # Append to the end of the file
    text += "\n" + SAVED_MODEL.strip() + "\n"
    MODELS_FILE.write_text(text, encoding="utf-8")
    print("Patched apps/properties/models.py: added SavedListing model")

# Update serializers to include is_saved and coordinates
SERIALIZERS_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZERS_FILE.read_text(encoding="utf-8")

if "is_saved" not in text:
    old_listing = '''class ListingSerializer(serializers.ModelSerializer):
    media = ListingMediaSerializer(many=True, read_only=True)
    property_summary = serializers.SerializerMethodField()
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)'''
    
    new_listing = '''class ListingSerializer(serializers.ModelSerializer):
    media = ListingMediaSerializer(many=True, read_only=True)
    property_summary = serializers.SerializerMethodField()
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    is_saved = serializers.SerializerMethodField()'''
    
    text = text.replace(old_listing, new_listing)
    
    # Add is_saved method and fields
    old_fields = '''            "status", "published_at", "expires_at", "rejection_reason",
            "moderation_note", "media", "created_at", "updated_at",
        )'''
    
    new_fields = '''            "status", "published_at", "expires_at", "rejection_reason",
            "moderation_note", "media", "is_saved", "created_at", "updated_at",
        )'''
    
    text = text.replace(old_fields, new_fields)
    
    # Add the get_is_saved method before get_property_summary
    old_method = '''    def get_property_summary(self, obj):'''
    new_method = '''    def get_is_saved(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.saved_by.filter(user=request.user).exists()
        return False

    def get_property_summary(self, obj):'''
    
    text = text.replace(old_method, new_method)
    
    # Make sure context is passed to serializer in views
    SERIALIZERS_FILE.write_text(text, encoding="utf-8")
    print("Patched serializers.py: added is_saved logic")

# Add SavedListingViewSet to views.py
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "class SavedListingViewSet" not in text:
    text += '''

class SavedListingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SavedListing.objects.filter(user=self.request.user).select_related("listing")
    
    def create(self, request):
        listing_id = request.data.get("listing_id")
        saved, created = SavedListing.objects.get_or_create(user=request.user, listing_id=listing_id)
        return Response({"status": "saved"})
        
    def destroy(self, request, pk=None):
        # pk here will be the listing_id based on our frontend URL structure
        SavedListing.objects.filter(user=request.user, listing_id=pk).delete()
        return Response(status=204)
'''
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: added SavedListingViewSet")

# Update urls.py
URLS_FILE = ROOT / "apps" / "properties" / "urls.py"
text = URLS_FILE.read_text(encoding="utf-8")
if "saved-listings" not in text:
    text = text.replace(
        'router.register("reports", ReportViewSet, basename="report")',
        'router.register("reports", ReportViewSet, basename="report")\nrouter.register("saved-listings", SavedListingViewSet, basename="saved-listing")'
    )
    text = text.replace(
        'from .views import ListingMediaViewSet, ListingViewSet, PropertyViewSet, ReportViewSet',
        'from .views import ListingMediaViewSet, ListingViewSet, PropertyViewSet, ReportViewSet, SavedListingViewSet'
    )
    URLS_FILE.write_text(text, encoding="utf-8")
    print("Patched urls.py: mounted SavedListingViewSet")

# ---------------------------------------------------------------- 2. Frontend: API & UI

FRONTEND_API = '''
import { api } from './client'
import type { Listing, Paginated } from './types'

export interface ListingFilters {
  search?: string
  transaction_type?: string
  province?: string
  district?: string
  neighbourhood?: string
  property_type?: string
  min_price?: number
  max_price?: number
  min_bedrooms?: number
  page?: number
}

export const listingsApi = {
  list: (filters: ListingFilters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    const qs = params.toString()
    return api<Paginated<Listing>>(`/listings/${qs ? `?${qs}` : ''}`)
  },
  get: (id: string) => api<Listing>(`/listings/${id}/`),
  getProperty: (id: string) => api<any>(`/properties/${id}/`),
  
  createProperty: (data: any) => api<{id: string}>(`/properties/`, { method: 'POST', body: JSON.stringify(data) }),
  createListing: (data: any) => api<Listing>(`/listings/`, { method: 'POST', body: JSON.stringify(data) }),
  
  updateProperty: (id: string, data: any) => api(`/properties/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateListing: (id: string, data: any) => api(`/listings/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),

  uploadMedia: (listingId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('media_type', 'IMAGE')
    return api(`/listings/${listingId}/media/`, { method: 'POST', body: formData })
  },
  deleteMedia: (listingId: string, mediaId: string) => 
    api(`/listings/${listingId}/media/${mediaId}/`, { method: 'DELETE' }),

  // Saved Listings
  listSaved: () => api<{results: any[]}>('/saved-listings/'),
  toggleSave: (listingId: string, isSaved: boolean) => {
    if (isSaved) {
      return api(`/saved-listings/${listingId}/`, { method: 'DELETE' })
    } else {
      return api('/saved-listings/', { method: 'POST', body: JSON.stringify({ listing_id: listingId }) })
    }
  }
}

export const getMediaUrl = (url: string) => {
  if (!url) return ''
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}
'''

LISTING_CARD = '''
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import type { Listing } from '../api/types'

function formatPrice(price: string, currency: string, period: string) {
  const n = Number(price)
  const fmt = new Intl.NumberFormat('en-ZM', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n)
  if (period === 'MONTH') return `${fmt}/mo`
  if (period === 'YEAR') return `${fmt}/yr`
  return fmt
}

export default function ListingCard({ listing }: { listing: Listing & { is_saved?: boolean } }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const cover = listing.media.find((m) => m.media_type === 'IMAGE')

  const saveMutation = useMutation({
    mutationFn: () => listingsApi.toggleSave(listing.id, !!listing.is_saved),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['listings'] })
      queryClient.invalidateQueries({ queryKey: ['saved-listings'] })
    }
  })

  const handleSave = (e: React.MouseEvent) => {
    e.preventDefault()
    if (!user) {
      alert("Please log in to save properties.")
      return
    }
    saveMutation.mutate()
  }

  return (
    <Link to={`/listings/${listing.id}`} className="block bg-white border rounded-lg overflow-hidden hover:shadow-lg transition group relative">
      
      {/* Heart / Save Button */}
      <button 
        onClick={handleSave}
        className="absolute top-3 right-3 z-10 p-2 bg-white/80 backdrop-blur rounded-full shadow hover:bg-white transition"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill={listing.is_saved ? "#ef4444" : "none"} stroke={listing.is_saved ? "#ef4444" : "currentColor"} strokeWidth="2" className={listing.is_saved ? "text-red-500" : "text-gray-600"}>
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
        </svg>
      </button>

      <div className="aspect-video bg-gray-100">
        {cover ? (
          <img src={getMediaUrl(cover.file)} alt={listing.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">No photo</div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold truncate pr-6">{listing.title}</h3>
        <p className="text-sm text-gray-600 mt-1">{listing.property_summary.neighbourhood}</p>
        <p className="mt-2 font-bold text-emerald-700">{formatPrice(listing.price, listing.currency, listing.price_period)}</p>
        <p className="text-sm text-gray-500 mt-1">
          {listing.property_summary.property_type}
          {listing.property_summary.bedrooms ? ` · ${listing.property_summary.bedrooms} bed` : ''}
        </p>
      </div>
    </Link>
  )
}
'''

HOME_PAGE = '''
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, type ListingFilters } from '../api/listings'
import SearchBar from '../components/SearchBar'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function HomePage() {
  const [filters, setFilters] = useState<ListingFilters>({})
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
  })

  const updateFilter = (key: keyof ListingFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value || undefined }))
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Find your place in Zambia</h1>
        <p className="text-gray-600 mb-6">Browse verified listings in Lusaka and beyond.</p>
        
        <div className="flex gap-4 items-start">
          <div className="flex-1">
            <SearchBar initialValue={filters.search} onSearch={(v) => updateFilter('search', v)} />
          </div>
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded border font-medium flex items-center gap-2 ${showFilters ? 'bg-emerald-50 border-emerald-500 text-emerald-700' : 'bg-white text-gray-700'}`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
            Filters
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-white p-6 rounded-lg border shadow-sm mb-8 grid grid-cols-2 md:grid-cols-4 gap-6">
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
            <label className="block text-sm font-medium mb-1">Transaction</label>
            <select 
              value={filters.transaction_type || ''} onChange={(e) => updateFilter('transaction_type', e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">Any</option>
              <option value="RENT">For Rent</option>
              <option value="SALE">For Sale</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Min Bedrooms</label>
            <input 
              type="number" min="0" value={filters.min_bedrooms || ''} onChange={(e) => updateFilter('min_bedrooms', e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. 2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Max Price (ZMW)</label>
            <input 
              type="number" min="0" value={filters.max_price || ''} onChange={(e) => updateFilter('max_price', e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. 10000"
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
  )
}
'''

SAVED_PAGE = '''
import { useQuery } from '@tanstack/react-query'
import { listingsApi } from '../api/listings'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'

export default function SavedPropertiesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['saved-listings'],
    queryFn: () => listingsApi.listSaved(),
  })

  if (isLoading) return <Loading />

  const listings = data?.results.map((r: any) => r.listing) || []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Saved Properties</h1>
      {listings.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-white rounded border">
          You haven't saved any properties yet. Click the heart icon on a listing to save it.
        </div>
      ) : (
        <ListingGrid listings={listings} />
      )}
    </div>
  )
}
'''

LAYOUT = '''
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path ? 'text-emerald-700 font-bold' : 'text-gray-700 hover:text-emerald-700'

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700">NyumbaLink</Link>
          <nav className="flex items-center gap-6 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
                <Link to="/saved" className={isActive('/saved')}>Saved</Link>
                <Link to="/inbox" className={isActive('/inbox')}>Inbox</Link>
                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
                <span className="text-gray-300">|</span>
                <span className="text-gray-600 hidden sm:inline">{user.email}</span>
                <button onClick={() => { logout(); navigate('/') }} className="text-red-600 hover:underline">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700">Login</Link>
                <Link to="/register" className="bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700">Register</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t bg-white py-4 text-center text-sm text-gray-500">NyumbaLink · Find your place. Connect your world.</footer>
    </div>
  )
}
'''

APP_TSX = '''
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ListingDetailPage from './pages/ListingDetailPage'
import NotFoundPage from './pages/NotFoundPage'
import DashboardPage from './pages/DashboardPage'
import CreateListingPage from './pages/CreateListingPage'
import ManageListingPage from './pages/ManageListingPage'
import EditListingPage from './pages/EditListingPage'
import VerificationPage from './pages/VerificationPage'
import WalletPage from './pages/WalletPage'
import PaymentSettingsPage from './pages/PaymentSettingsPage'
import InboxPage from './pages/InboxPage'
import SavedPropertiesPage from './pages/SavedPropertiesPage'
import ProtectedRoute from './auth/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="/listings/:id" element={<ListingDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/listings/new" element={<CreateListingPage />} />
          <Route path="/dashboard/listings/:id" element={<ManageListingPage />} />
          <Route path="/dashboard/listings/:id/edit" element={<EditListingPage />} />
          <Route path="/verification" element={<VerificationPage />} />
          <Route path="/wallet" element={<WalletPage />} />
          <Route path="/settings" element={<PaymentSettingsPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/saved" element={<SavedPropertiesPage />} />
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
'''

# ---------------------------------------------------------------- 3. Write Frontend Files

FRONTEND_FILES = {
    "src/api/listings.ts": FRONTEND_API,
    "src/components/ListingCard.tsx": LISTING_CARD,
    "src/pages/HomePage.tsx": HOME_PAGE,
    "src/pages/SavedPropertiesPage.tsx": SAVED_PAGE,
    "src/components/Layout.tsx": LAYOUT,
    "src/App.tsx": APP_TSX,
}

def run():
    print(f"NyumbaLink Phase 8 (Search & Saved) -> {ROOT}\n")
    
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
Phase 8 Complete.

Test the flow:

  1. Restart backend (runserver) and frontend (npm run dev).
  2. On the Home Page, click the "Filters" button.
  3. Select "Apartment" and set Min Bedrooms to 2.
  4. Click the Heart icon on any property card. (You must be logged in).
  5. The heart turns red.
  6. Click "Saved" in the top navigation to see only your hearted properties.
  7. Return to Home, and notice the filters stay applied while you browse.
""")

if __name__ == "__main__":
    run()