#!/usr/bin/env python3
"""Fixes for NyumbaLink Phase 3: Media serving and JWT token refresh."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- Backend Fixes

URLS_PY = '''
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.locations.urls")),
    path("api/v1/", include("apps.properties.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
'''.strip() + "\n"

SETTINGS_PATCH = '''
# Replace MEDIA_URL = "media/" with:
MEDIA_URL = "/media/"
'''.strip() + "\n"

# ---------------------------------------------------------------- Frontend Fixes

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

export async function api<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
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

  // Handle expired access tokens by refreshing them automatically
  if (res.status === 401 && !isRetry && !path.includes('/auth/')) {
    try {
      const refreshRes = await fetch(`${API_URL}/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
      })
      if (refreshRes.ok) {
        return api<T>(path, options, true)
      }
    } catch {
      // Refresh failed, fall through to error
    }
  }

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export { API_URL }
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
  // Handle full remote URLs accidentally saved in the DB
  if (url.includes('http%3A') || url.includes('https%3A')) {
    return decodeURIComponent(url.replace('/media/', ''))
  }
  if (url.startsWith('http')) return url
  // Handle local Django media files
  return `http://localhost:8000${url}`
}
'''

def run():
    print(f"NyumbaLink Fix Script -> {ROOT}\n")

    # 1. Fix Django URLs to serve media files
    print("Patching backend to serve media files...")
    urls_file = ROOT / "config" / "urls.py"
    if urls_file.exists():
        urls_file.write_text(URLS_PY, encoding="utf-8")
        print("  config/urls.py updated.")

    # 2. Fix MEDIA_URL in settings
    settings_file = ROOT / "config" / "settings" / "base.py"
    if settings_file.exists():
        text = settings_file.read_text(encoding="utf-8")
        if 'MEDIA_URL = "media/"' in text:
            text = text.replace('MEDIA_URL = "media/"', 'MEDIA_URL = "/media/"')
            settings_file.write_text(text, encoding="utf-8")
            print("  config/settings/base.py updated (MEDIA_URL).")

    # 3. Update Frontend API Client for Token Refresh
    print("\nPatching frontend API client for JWT refresh...")
    client_file = FRONTEND / "src" / "api" / "client.ts"
    if client_file.exists():
        client_file.write_text(API_CLIENT, encoding="utf-8")
        print("  src/api/client.ts updated.")

    # 4. Update Frontend Media URL helper
    print("Patching frontend media URL helper...")
    listings_file = FRONTEND / "src" / "api" / "listings.ts"
    if listings_file.exists():
        listings_file.write_text(API_LISTINGS, encoding="utf-8")
        print("  src/api/listings.ts updated.")

    print("""
Next steps:

  1. Restart your backend server (Ctrl+C, then `python manage.py runserver`).

  2. Restart your frontend (Ctrl+C, then `npm run dev`).

  3. VERY IMPORTANT: 
     Your old JWT token is expired. You must log out and log back in 
     for the auto-refresh feature to start working.

  4. Try uploading images and saving again!
""")

if __name__ == "__main__":
    run()