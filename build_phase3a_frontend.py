#!/usr/bin/env python3
"""NyumbaLink Phase 3a frontend: Vite + React + TS + Tailwind + React Query."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- files

INDEX_HTML = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>NyumbaLink — Find your place. Connect your world.</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'''

VITE_CONFIG = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
'''

TAILWIND_CONFIG = '''/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
'''

POSTCSS_CONFIG = '''export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
'''

ENV_LOCAL = "VITE_API_URL=http://localhost:8000/api/v1\n"

INDEX_CSS = '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''

MAIN_TSX = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
'''

APP_TSX = '''import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ListingDetailPage from './pages/ListingDetailPage'
import NotFoundPage from './pages/NotFoundPage'
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
          {/* Landlord dashboard routes arrive in Phase 3b */}
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
'''

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
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export { API_URL }
'''

API_TYPES = '''export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
}

export interface ListingMedia {
  id: string
  file: string
  media_type: 'IMAGE' | 'VIDEO' | 'TOUR'
  caption: string
  display_order: number
}

export interface PropertySummary {
  id: string
  property_type: string
  bedrooms: number | null
  bathrooms: string | null
  neighbourhood: string
}

export interface Listing {
  id: string
  property: string
  property_summary: PropertySummary
  created_by: string
  created_by_email: string
  transaction_type: 'RENT' | 'SALE' | 'SHORT_LET'
  price: string
  currency: string
  price_period: 'MONTH' | 'YEAR' | 'ONCE'
  deposit_months: string | null
  title: string
  description: string
  available_from: string | null
  status: string
  published_at: string | null
  expires_at: string | null
  media: ListingMedia[]
  created_at: string
  updated_at: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
'''

API_AUTH = '''import { api } from './client'
import type { User } from './types'

export const authApi = {
  login: (email: string, password: string) =>
    api<{ user: User }>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, firstName = '', lastName = '') =>
    api<{ user: User }>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify({
        email, password,
        first_name: firstName,
        last_name: lastName,
      }),
    }),

  logout: () => api<void>('/auth/logout/', { method: 'POST' }),
  me: () => api<User>('/auth/me/'),
}
'''

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
}
'''

AUTH_CONTEXT = '''import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, firstName?: string, lastName?: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const { user } = await authApi.login(email, password)
    setUser(user)
  }

  const register = async (email: string, password: string, firstName?: string, lastName?: string) => {
    const { user } = await authApi.register(email, password, firstName, lastName)
    setUser(user)
  }

  const logout = async () => {
    await authApi.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
'''

PROTECTED_ROUTE = '''import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="p-8 text-center text-gray-500">Loading…</div>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return <Outlet />
}
'''

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
                <span className="text-gray-600 hidden sm:inline">{user.email}</span>
                {user.is_staff && (
                  <a
                    href="http://localhost:8000/admin/"
                    className="text-emerald-700 hover:underline"
                  >
                    Admin
                  </a>
                )}
                <button
                  onClick={handleLogout}
                  className="text-gray-700 hover:text-red-600"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700">
                  Login
                </Link>
                <Link
                  to="/register"
                  className="bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700"
                >
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

SEARCH_BAR = '''import { useState, type FormEvent } from 'react'

interface Props {
  initialValue?: string
  onSearch: (value: string) => void
}

export default function SearchBar({ initialValue = '', onSearch }: Props) {
  const [value, setValue] = useState(initialValue)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(value.trim())
  }

  return (
    <form onSubmit={submit} className="flex gap-2 w-full max-w-2xl">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search by neighbourhood, description…"
        className="flex-1 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <button
        type="submit"
        className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700"
      >
        Search
      </button>
    </form>
  )
}
'''

LISTING_CARD = '''import { Link } from 'react-router-dom'
import type { Listing } from '../api/types'

function formatPrice(price: string, currency: string, period: string) {
  const n = Number(price)
  const fmt = new Intl.NumberFormat('en-ZM', {
    style: 'currency', currency, maximumFractionDigits: 0,
  }).format(n)
  if (period === 'MONTH') return `${fmt}/mo`
  if (period === 'YEAR') return `${fmt}/yr`
  return fmt
}

export default function ListingCard({ listing }: { listing: Listing }) {
  const cover = listing.media.find((m) => m.media_type === 'IMAGE')

  return (
    <Link
      to={`/listings/${listing.id}`}
      className="block bg-white border rounded-lg overflow-hidden hover:shadow-lg transition"
    >
      <div className="aspect-video bg-gray-100">
        {cover ? (
          <img src={cover.file} alt={listing.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
            No photo
          </div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold truncate">{listing.title}</h3>
        <p className="text-sm text-gray-600 mt-1">{listing.property_summary.neighbourhood}</p>
        <p className="mt-2 font-bold text-emerald-700">
          {formatPrice(listing.price, listing.currency, listing.price_period)}
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {listing.property_summary.property_type}
          {listing.property_summary.bedrooms ? ` · ${listing.property_summary.bedrooms} bed` : ''}
        </p>
      </div>
    </Link>
  )
}
'''

LISTING_GRID = '''import ListingCard from './ListingCard'
import type { Listing } from '../api/types'

export default function ListingGrid({ listings }: { listings: Listing[] }) {
  if (listings.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 bg-white rounded border">
        No listings found. Try adjusting your search.
      </div>
    )
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {listings.map((l) => <ListingCard key={l.id} listing={l} />)}
    </div>
  )
}
'''

LOADING = '''export default function Loading({ label = 'Loading…' }: { label?: string }) {
  return <div className="py-12 text-center text-gray-500">{label}</div>
}
'''

ERROR_MSG = '''export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="my-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
      {message}
    </div>
  )
}
'''

HOME_PAGE = '''import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, type ListingFilters } from '../api/listings'
import SearchBar from '../components/SearchBar'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function HomePage() {
  const [filters, setFilters] = useState<ListingFilters>({})

  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Find your place in Zambia</h1>
        <p className="text-gray-600 mb-6">
          Browse verified listings in Lusaka and beyond.
        </p>
        <SearchBar
          initialValue={filters.search}
          onSearch={(v) => setFilters((f) => ({ ...f, search: v || undefined }))}
        />
      </div>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Could not load listings. Is the backend running?" />}
      {data && (
        <>
          <p className="text-sm text-gray-600 mb-4">
            {data.count} listing{data.count === 1 ? '' : 's'}
          </p>
          <ListingGrid listings={data.results} />
        </>
      )}
    </div>
  )
}
'''

LOGIN_PAGE = '''import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import ErrorMessage from '../components/ErrorMessage'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError((err as Error).message || 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold mb-6">Log in to NyumbaLink</h1>
      {error && <ErrorMessage message={error} />}
      <form onSubmit={submit} className="space-y-4 bg-white p-6 rounded border">
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Password</label>
          <input
            type="password" required value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>
        <button
          type="submit" disabled={submitting}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50"
        >
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p className="mt-6 text-sm text-center text-gray-600">
        No account?{' '}
        <Link to="/register" className="text-emerald-700 hover:underline">
          Register
        </Link>
      </p>
    </div>
  )
}
'''

REGISTER_PAGE = '''import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import ErrorMessage from '../components/ErrorMessage'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setSubmitting(true)
    try {
      await register(email, password, firstName, lastName)
      navigate('/', { replace: true })
    } catch (err) {
      setError((err as Error).message || 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold mb-6">Create your account</h1>
      {error && <ErrorMessage message={error} />}
      <form onSubmit={submit} className="space-y-4 bg-white p-6 rounded border">
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">First name</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Last name</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Password</label>
          <input type="password" required value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          <p className="text-xs text-gray-500 mt-1">At least 8 characters.</p>
        </div>
        <button type="submit" disabled={submitting}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50">
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="mt-6 text-sm text-center text-gray-600">
        Already have an account?{' '}
        <Link to="/login" className="text-emerald-700 hover:underline">Log in</Link>
      </p>
    </div>
  )
}
'''

DETAIL_PAGE = '''import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listingsApi } from '../api/listings'
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
            <img key={m.id} src={m.file} alt={m.caption || listing.title}
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

NOT_FOUND = '''import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="max-w-md mx-auto px-4 py-16 text-center">
      <h1 className="text-4xl font-bold mb-4">404</h1>
      <p className="text-gray-600 mb-6">That page does not exist.</p>
      <Link to="/" className="text-emerald-700 hover:underline">Go home</Link>
    </div>
  )
}
'''

FRONTEND_FILES = {
    "index.html": INDEX_HTML,
    "vite.config.ts": VITE_CONFIG,
    "tailwind.config.js": TAILWIND_CONFIG,
    "postcss.config.js": POSTCSS_CONFIG,
    ".env.local": ENV_LOCAL,
    "src/index.css": INDEX_CSS,
    "src/main.tsx": MAIN_TSX,
    "src/App.tsx": APP_TSX,
    "src/api/client.ts": API_CLIENT,
    "src/api/types.ts": API_TYPES,
    "src/api/auth.ts": API_AUTH,
    "src/api/listings.ts": API_LISTINGS,
    "src/auth/AuthContext.tsx": AUTH_CONTEXT,
    "src/auth/ProtectedRoute.tsx": PROTECTED_ROUTE,
    "src/components/Layout.tsx": LAYOUT,
    "src/components/SearchBar.tsx": SEARCH_BAR,
    "src/components/ListingCard.tsx": LISTING_CARD,
    "src/components/ListingGrid.tsx": LISTING_GRID,
    "src/components/Loading.tsx": LOADING,
    "src/components/ErrorMessage.tsx": ERROR_MSG,
    "src/pages/HomePage.tsx": HOME_PAGE,
    "src/pages/LoginPage.tsx": LOGIN_PAGE,
    "src/pages/RegisterPage.tsx": REGISTER_PAGE,
    "src/pages/ListingDetailPage.tsx": DETAIL_PAGE,
    "src/pages/NotFoundPage.tsx": NOT_FOUND,
}

# ---------------------------------------------------------------- backend CORS fix

DEV_PY = ROOT / "config" / "settings" / "dev.py"

def patch_dev_cors() -> str:
    if not DEV_PY.exists():
        return "SKIP  dev.py not found"
    text = DEV_PY.read_text(encoding="utf-8")
    if "CORS_ALLOW_ALL_ORIGINS = True" not in text:
        return "ok    dev.py already explicit origins"
    new = (
        "# CORS_ALLOW_ALL_ORIGINS removed — incompatible with CORS_ALLOW_CREDENTIALS.\n"
        "# Base settings already define CORS_ALLOWED_ORIGINS for localhost:5173.\n"
    )
    text = text.replace("CORS_ALLOW_ALL_ORIGINS = True", new.strip(), 1)
    DEV_PY.write_text(text, encoding="utf-8")
    return "PATCH dev.py: CORS_ALLOW_ALL_ORIGINS -> explicit origins from base"

# ---------------------------------------------------------------- engine

def run(cmd: list[str], cwd: Path) -> int:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, shell=(sys.platform == "win32")).returncode


def check_prereqs() -> bool:
    for tool in ("node", "npm"):
        if shutil.which(tool) is None:
            print(f"ERROR: {tool} not on PATH. Install Node.js LTS from https://nodejs.org/")
            return False
    v = subprocess.run(["node", "--version"], capture_output=True, text=True)
    print(f"Node {v.stdout.strip()}")
    if not (ROOT / "manage.py").exists():
        print("ERROR: run this from the Django project root.")
        return False
    return True


def main() -> int:
    print(f"NyumbaLink Phase 3a frontend -> {ROOT}\n")
    if not check_prereqs():
        return 1

    # 1. Backend CORS fix
    print("Patching backend CORS:")
    print(f"  {patch_dev_cors()}\n")

    # 2. Scaffold Vite
    if FRONTEND.exists() and any(FRONTEND.iterdir()):
        print(f"frontend/ already exists — skipping vite scaffold.")
        print(f"  (delete {FRONTEND} to regenerate from scratch)\n")
    else:
        print("Scaffolding Vite project:")
        rc = run(
            ["npm", "create", "vite@latest", "frontend", "--", "--template", "react-ts"],
            ROOT,
        )
        if rc != 0:
            print("vite scaffold failed — check Node version and try again.")
            return rc

    # 3. Install deps
    print("\nInstalling dependencies:")
    for cmd in [
        ["npm", "install"],
        ["npm", "install", "react-router-dom", "@tanstack/react-query"],
        ["npm", "install", "-D", "tailwindcss@3", "postcss", "autoprefixer"],
    ]:
        if run(cmd, FRONTEND) != 0:
            print(f"dependency install failed: {' '.join(cmd)}")
            return 1

    # 4. Write source files
    print("\nWriting source files:")
    written = 0
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written += 1
    print(f"  {written} files written")

    # 5. Remove dead default files
    for dead in ["src/App.css", "src/assets/react.svg"]:
        p = FRONTEND / dead
        if p.exists():
            p.unlink()
            print(f"  removed {dead}")

    print("""
Next steps:

  1. Start backend (Terminal 1):
       .\\venv\\Scripts\\python.exe manage.py runserver

  2. Start frontend (Terminal 2):
       cd frontend
       npm run dev

  3. Open http://localhost:5173 in a browser

  4. Verify:
       - Home page loads (probably shows "0 listings")
       - Register a new account → should land on home, header shows email
       - Logout, then log back in with howardmupeta@nyumbalink.com
       - Visit http://localhost:5173/listings/anything → 404 page loads correctly

  5. Commit:
       git add -A
       git commit -m "Phase 3a: React frontend — auth, home, listing detail"
       git tag phase-3a
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())