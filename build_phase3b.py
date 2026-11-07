#!/usr/bin/env python3
"""NyumbaLink Phase 3b: Landlord Dashboard & Listing Creation."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- API Client Update
# We need to support FormData for image uploads, so we adjust the client
API_CLIENT = '''const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number
  data: unknown
  constructor(status: number, data: unknown) {
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? String((data as Record<string, unknown>).detail)
        : `HTTP ${status}`
    super(detail)
    this.status = status
    this.data = data
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData
  
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  })

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export { API_URL }
'''

# ---------------------------------------------------------------- API Listings Update
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
  createProperty: (data: any) => api<{id: string}>(`/properties/`, { method: 'POST', body: JSON.stringify(data) }),
  createListing: (data: any) => api<Listing>(`/listings/`, { method: 'POST', body: JSON.stringify(data) }),
  uploadMedia: (listingId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('media_type', 'IMAGE')
    return api(`/listings/${listingId}/media/`, { method: 'POST', body: formData })
  }
}
'''

# ---------------------------------------------------------------- Dashboard Page
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
                <th className="px-4 py-3 font-semibold text-sm">Actions</th>
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
                  <td className="px-4 py-3">
                    <Link to={`/listings/${l.id}`} className="text-emerald-600 hover:underline text-sm">
                      View
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

# ---------------------------------------------------------------- Create Listing Page
CREATE_LISTING_PAGE = '''import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { listingsApi } from '../api/listings'
import ErrorMessage from '../components/ErrorMessage'

export default function CreateListingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const { data: hoods } = useQuery({
    queryKey: ['neighbourhoods'],
    queryFn: () => api<any>('/neighbourhoods/?page=1'),
  })

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      // 1. Create Property
      const property = await listingsApi.createProperty({
        neighbourhood: formData.get('neighbourhood'),
        property_type: formData.get('property_type'),
        bedrooms: Number(formData.get('bedrooms')),
        bathrooms: Number(formData.get('bathrooms')),
        floor_area: Number(formData.get('floor_area')),
        description: formData.get('description'),
      })

      // 2. Create Listing
      const listing = await listingsApi.createListing({
        property: property.id,
        transaction_type: 'RENT',
        price: Number(formData.get('price')),
        title: formData.get('title'),
        description: formData.get('description'),
      })

      // 3. Upload Image (if provided)
      if (file) {
        await listingsApi.uploadMedia(listing.id, file)
      }
      
      return listing
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-listings'] })
      navigate('/dashboard')
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to create listing')
    }
  })

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    const formData = new FormData(e.currentTarget)
    mutation.mutate(formData)
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Create a New Listing</h1>
      {error && <ErrorMessage message={error} />}
      
      <form onSubmit={submit} className="bg-white border rounded p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Listing Title</label>
          <input name="title" required className="w-full border rounded px-3 py-2" placeholder="e.g. Modern 2-Bed Apartment" />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Property Type</label>
            <select name="property_type" required className="w-full border rounded px-3 py-2">
              <option value="HOUSE">House</option>
              <option value="APARTMENT">Apartment</option>
              <option value="TOWNHOUSE">Townhouse</option>
              <option value="LAND">Land</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Neighbourhood</label>
            <select name="neighbourhood" required className="w-full border rounded px-3 py-2">
              <option value="">Select location...</option>
              {hoods?.results.map((h: any) => (
                <option key={h.id} value={h.id}>{h.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Bedrooms</label>
            <input type="number" name="bedrooms" required min="0" defaultValue="2" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Bathrooms</label>
            <input type="number" step="0.5" name="bathrooms" required min="0" defaultValue="1" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Floor Area (m²)</label>
            <input type="number" name="floor_area" required min="0" defaultValue="80" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Monthly Rent (ZMW)</label>
            <input type="number" name="price" required min="0" defaultValue="5000" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea name="description" rows={4} className="w-full border rounded px-3 py-2" placeholder="Describe the property..." />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Cover Image</label>
          <input 
            type="file" 
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full border rounded px-3 py-2" 
          />
        </div>

        <button 
          type="submit" 
          disabled={mutation.isPending}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Creating...' : 'Create Listing'}
        </button>
      </form>
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
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
'''

# ---------------------------------------------------------------- Layout Nav Update
LAYOUT = '''import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700">
            NyumbaLink
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className="text-gray-700 hover:text-emerald-700 font-medium">
                  Dashboard
                </Link>
                <span className="text-gray-300">|</span>
                <span className="text-gray-600 hidden sm:inline">{user.email}</span>
                {user.is_staff && (
                  <a href="http://localhost:8000/admin/" className="text-emerald-700 hover:underline">
                    Admin
                  </a>
                )}
                <button onClick={handleLogout} className="text-gray-700 hover:text-red-600">
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700">Login</Link>
                <Link to="/register" className="bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700">
                  Register
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t bg-white py-4 text-center text-sm text-gray-500">
        NyumbaLink · Find your place. Connect your world.
      </footer>
    </div>
  )
}
'''

FRONTEND_FILES = {
    "src/api/client.ts": API_CLIENT,
    "src/api/listings.ts": API_LISTINGS,
    "src/pages/DashboardPage.tsx": DASHBOARD_PAGE,
    "src/pages/CreateListingPage.tsx": CREATE_LISTING_PAGE,
    "src/App.tsx": APP_TSX,
    "src/components/Layout.tsx": LAYOUT,
}

def run():
    print(f"NyumbaLink Phase 3b -> {ROOT}\n")
    if not (ROOT / "manage.py").exists():
        print("ERROR: run from project root.")
        return

    print("Writing frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("""
Next steps:

  1. Make sure your frontend dev server is running:
       cd frontend
       npm run dev

  2. Make sure your backend server is running (new terminal):
       .\\venv\\Scripts\\python.exe manage.py runserver

  3. In the browser:
       - Log in as demo@nyumbalink.com / Password123!
       - You will now see a "Dashboard" link in the header.
       - Click "Dashboard" -> "Create Listing"
       - Fill out the form and upload an image.
       - The listing will be created with a DRAFT status (invisible to public).
       
  4. To approve your own listing:
       - Go to http://127.0.0.1:8000/admin/
       - Go to Properties -> Listings
       - Select your new listing and use the "Publish selected..." action.
       - Now it shows up on the public homepage!
""")

if __name__ == "__main__":
    run()