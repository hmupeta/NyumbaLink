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
  getRecommendations: () => api<Listing[]>('/listings/recommendations/'),
  getMyListings: () => api<Paginated<Listing>>('/listings/my_listings/'),
  submitForReview: (id: string) => api(`/listings/${id}/submit/`, { method: 'POST' }),
  trackView: (id: string) => api(`/listings/${id}/track_view/`, { method: 'POST' }),
  getAnalytics: () => api<any>('/listings/analytics/'),
  submitReport: (listingId: string, reason: string, description: string) => api('/reports/', {
    method: 'POST',
    body: JSON.stringify({ target_listing: listingId, reason, description })
  }),
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
  
  // 1. Handle dummy seed data (e.g. https%3A/images.unsplash.com/... or /media/https%3A/...)
  if (url.includes('https%3A') || url.includes('http%3A') || url.includes('/media/http')) {
    const match = url.match(/https?(?:%3A|\:)/)
    if (match && match.index !== undefined) {
      const externalUrl = url.substring(match.index);
      return decodeURIComponent(externalUrl);
    }
  }
  
  // 2. Standard external URLs (like proper Unsplash links)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 3. Standard local media paths (Render backend)
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}
