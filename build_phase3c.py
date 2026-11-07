#!/usr/bin/env python3
"""NyumbaLink Phase 3c: Landlord Management, Edit, and Image Uploads."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- API Update
API_LISTINGS = '''import { api } from './client'
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
  }
}

export const getMediaUrl = (url: string) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}
'''

# ---------------------------------------------------------------- Manage Page
MANAGE_LISTING_PAGE = '''import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ManageListingPage() {
  const { id } = useParams<{ id: string }>()
  
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['manage-listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) return <Loading />
  if (error || !listing) return <div className="p-8"><ErrorMessage message="Listing not found." /></div>

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Link to="/dashboard" className="text-sm text-emerald-700 hover:underline">
          ← Back to Dashboard
        </Link>
        <Link to={`/dashboard/listings/${listing.id}/edit`} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900 text-sm">
          Edit Listing
        </Link>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="aspect-video bg-gray-100 flex items-center justify-center">
              {listing.media[0] ? (
                <img src={getMediaUrl(listing.media[0].file)} alt="Cover" className="w-full h-full object-cover" />
              ) : (
                <span className="text-gray-400">No image uploaded</span>
              )}
            </div>
            <div className="p-6">
              <div className="flex justify-between items-start mb-2">
                <h1 className="text-2xl font-bold">{listing.title}</h1>
                <span className={`px-3 py-1 rounded text-xs font-bold ${
                  listing.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {listing.status}
                </span>
              </div>
              <p className="text-gray-600 mb-4">{listing.property_summary.neighbourhood} · {listing.property_summary.property_type}</p>
              
              <h2 className="font-semibold border-b pb-2 mb-2 mt-6">Description</h2>
              <p className="whitespace-pre-line text-gray-700">{listing.description || 'No description provided.'}</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white border rounded-lg p-6">
            <h3 className="font-bold text-lg mb-4">Rental Tracking</h3>
            <p className="text-sm text-gray-500 mb-4">Manage tenants and rent collection for this property.</p>
            
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Current Tenant</span>
                <span className="font-medium text-gray-400">None assigned</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Lease Start</span>
                <span className="font-medium text-gray-400">-</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Rent Due</span>
                <span className="font-medium text-gray-400">-</span>
              </div>
            </div>
            <button disabled className="mt-6 w-full bg-gray-100 text-gray-500 py-2 rounded cursor-not-allowed text-sm">
              Add Tenant (Coming in Phase 5)
            </button>
          </div>

          <div className="bg-white border rounded-lg p-6">
            <h3 className="font-bold text-lg mb-2">Financials</h3>
            <p className="text-3xl font-bold text-emerald-700">
              {listing.currency} {Number(listing.price).toLocaleString()}
              <span className="text-sm font-normal text-gray-500">/mo</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- Edit Page
EDIT_LISTING_PAGE = '''import { useState, useEffect, type FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { listingsApi, getMediaUrl } from '../api/listings'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

export default function EditListingPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  const [newFiles, setNewFiles] = useState<File[]>([])

  const { data: listing, isLoading: loadingListing } = useQuery({
    queryKey: ['manage-listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  const { data: property, isLoading: loadingProperty } = useQuery({
    queryKey: ['property', listing?.property],
    queryFn: () => listingsApi.getProperty(listing!.property),
    enabled: !!listing?.property,
  })

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      // 1. Update Property
      await listingsApi.updateProperty(listing!.property, {
        property_type: formData.get('property_type'),
        bedrooms: Number(formData.get('bedrooms')),
        bathrooms: Number(formData.get('bathrooms')),
        floor_area: Number(formData.get('floor_area')),
        description: formData.get('description'),
      })

      // 2. Update Listing
      await listingsApi.updateListing(listing!.id, {
        title: formData.get('title'),
        price: Number(formData.get('price')),
        description: formData.get('description'),
      })

      // 3. Upload new images
      for (const file of newFiles) {
        await listingsApi.uploadMedia(listing!.id, file)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manage-listing', id] })
      queryClient.invalidateQueries({ queryKey: ['listings'] })
      navigate(`/dashboard/listings/${id}`)
    },
    onError: (err: any) => setError(err.message || 'Failed to update listing')
  })

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    mutation.mutate(new FormData(e.currentTarget))
  }

  if (loadingListing || loadingProperty) return <Loading />
  if (!listing || !property) return <div className="p-8"><ErrorMessage message="Data not found." /></div>

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Edit Listing</h1>
      {error && <ErrorMessage message={error} />}
      
      <form onSubmit={submit} className="bg-white border rounded p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Listing Title</label>
          <input name="title" required defaultValue={listing.title} className="w-full border rounded px-3 py-2" />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Property Type</label>
            <select name="property_type" defaultValue={property.property_type} required className="w-full border rounded px-3 py-2">
              <option value="HOUSE">House</option>
              <option value="APARTMENT">Apartment</option>
              <option value="TOWNHOUSE">Townhouse</option>
              <option value="LAND">Land</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Monthly Rent (ZMW)</label>
            <input type="number" name="price" defaultValue={Number(listing.price)} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Bedrooms</label>
            <input type="number" name="bedrooms" defaultValue={property.bedrooms || 0} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Bathrooms</label>
            <input type="number" step="0.5" name="bathrooms" defaultValue={Number(property.bathrooms) || 0} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Floor Area (m²)</label>
            <input type="number" name="floor_area" defaultValue={Number(property.floor_area) || 0} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea name="description" defaultValue={listing.description} rows={4} className="w-full border rounded px-3 py-2" />
        </div>

        <div className="border-t pt-4 mt-4">
          <label className="block text-sm font-medium mb-2">Current Images</label>
          <div className="flex gap-2 overflow-x-auto mb-4">
            {listing.media.map(m => (
              <img key={m.id} src={getMediaUrl(m.file)} className="w-24 h-24 object-cover rounded border" />
            ))}
            {listing.media.length === 0 && <span className="text-gray-400 text-sm">No images yet.</span>}
          </div>

          <label className="block text-sm font-medium mb-1">Upload New Images (Select multiple)</label>
          <input 
            type="file" 
            accept="image/*"
            multiple
            onChange={(e) => setNewFiles(Array.from(e.target.files || []))}
            className="w-full border rounded px-3 py-2" 
          />
        </div>

        <button 
          type="submit" 
          disabled={mutation.isPending}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50 mt-4"
        >
          {mutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  )
}
'''

# ---------------------------------------------------------------- Fix Detail Page Image
DETAIL_PAGE = '''import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) return <Loading />
  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <ErrorMessage message="Listing not found or no longer available." />
      </div>
    )
  }
  if (!listing) return null

  const images = listing.media.filter((m) => m.media_type === 'IMAGE')

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/" className="text-sm text-emerald-700 hover:underline">
        ← Back to listings
      </Link>

      <h1 className="text-3xl font-bold mt-4 mb-2">{listing.title}</h1>
      <p className="text-gray-600 mb-6">
        {listing.property_summary.neighbourhood} · {listing.property_summary.property_type}
        {listing.property_summary.bedrooms ? ` · ${listing.property_summary.bedrooms} bedrooms` : ''}
      </p>

      {images.length > 0 && (
        <div className="grid gap-2 mb-6" style={{ gridTemplateColumns: images.length > 1 ? '2fr 1fr' : '1fr' }}>
          {images.slice(0, 2).map((m) => (
            <img key={m.id} src={getMediaUrl(m.file)} alt={m.caption || listing.title}
              className="w-full h-64 object-cover rounded" />
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="font-semibold text-lg mb-2">Description</h2>
          <p className="whitespace-pre-line text-gray-700">
            {listing.description || 'No description provided.'}
          </p>
        </div>
        <aside className="border rounded-lg p-4 h-fit bg-white">
          <p className="text-2xl font-bold text-emerald-700">
            {listing.currency} {Number(listing.price).toLocaleString()}
            {listing.price_period === 'MONTH' && (
              <span className="text-base text-gray-500">/mo</span>
            )}
          </p>
          <p className="text-sm text-gray-600 mt-1">
            {listing.transaction_type === 'RENT' ? 'For rent'
              : listing.transaction_type === 'SALE' ? 'For sale'
              : 'Short let'}
          </p>
          <button className="mt-4 w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700">
            Contact advertiser
          </button>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Advertised by {listing.created_by_email}
          </p>
        </aside>
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- Dashboard Page Update
DASHBOARD_PAGE = '''import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listingsApi } from '../api/listings'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function DashboardPage() {
  const { user } = useAuth()
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-listings'],
    queryFn: () => listingsApi.list({ page: 1 }),
  })

  // Filter listings to only those created by the logged-in user
  const myListings = data?.results.filter(l => l.created_by === user?.id) || []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold">Landlord Dashboard</h1>
          <p className="text-gray-600">Manage your properties and listings.</p>
        </div>
        <Link
          to="/dashboard/listings/new"
          className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700"
        >
          + Create Listing
        </Link>
      </div>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Could not load your listings." />}
      
      {data && myListings.length === 0 && (
        <div className="text-center py-12 bg-white rounded border">
          <p className="text-gray-500 mb-4">You haven't created any listings yet.</p>
          <Link to="/dashboard/listings/new" className="text-emerald-600 hover:underline">
            Create your first listing
          </Link>
        </div>
      )}

      {myListings.length > 0 && (
        <div className="bg-white border rounded overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 font-semibold text-sm">Title</th>
                <th className="px-4 py-3 font-semibold text-sm">Price</th>
                <th className="px-4 py-3 font-semibold text-sm">Status</th>
                <th className="px-4 py-3 font-semibold text-sm text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {myListings.map(l => (
                <tr key={l.id}>
                  <td className="px-4 py-3">{l.title}</td>
                  <td className="px-4 py-3">{l.currency} {Number(l.price).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      l.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' :
                      l.status === 'SUBMITTED' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {l.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <Link to={`/dashboard/listings/${l.id}`} className="text-gray-600 hover:underline text-sm font-medium">
                      Manage
                    </Link>
                    <Link to={`/dashboard/listings/${l.id}/edit`} className="text-emerald-600 hover:underline text-sm font-medium">
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
'''

# ---------------------------------------------------------------- App Router Update
APP_TSX = '''import { Routes, Route } from 'react-router-dom'
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
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
'''

FRONTEND_FILES = {
    "src/api/listings.ts": API_LISTINGS,
    "src/pages/ManageListingPage.tsx": MANAGE_LISTING_PAGE,
    "src/pages/EditListingPage.tsx": EDIT_LISTING_PAGE,
    "src/pages/ListingDetailPage.tsx": DETAIL_PAGE,
    "src/pages/DashboardPage.tsx": DASHBOARD_PAGE,
    "src/App.tsx": APP_TSX,
}

def run():
    print(f"NyumbaLink Phase 3c -> {ROOT}\n")
    
    print("Writing frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("""
Next steps:

  1. Make sure your frontend dev server is running (npm run dev).

  2. In the browser:
       - Go to Dashboard.
       - Notice the new "Manage" and "Edit" links in the table.
       - Click "Manage" -> You will see the Landlord view with Status, Images, 
         and the Rental Tracking placeholder.
       - Click "Edit" -> You can now upload MULTIPLE images and edit the details.

  3. Test the image upload:
       - Create a new listing or edit an existing one.
       - Select 2-3 images from your computer.
       - Save. The images should now load on both the public listing page 
         and the manage page (the broken Unsplash image issue is fixed).
""")

if __name__ == "__main__":
    run()