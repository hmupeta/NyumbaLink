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
  
  // 1. If it's a mangled Unsplash URL like https:/images... fix the slashes
  if (url.includes('https:/') && !url.includes('https://')) {
    return url.replace('https:/', 'https://')
  }

  // 2. If the URL got prefixed with /media/ but is an external link
  if (url.includes('/media/http')) {
    const match = url.match(/https?:\/\/.*/)
    if (match) return match[0]
  }
  
  // 3. Clean up encoded URLs
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  
  // 4. Standard external URLs (Unsplash, etc.)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 5. Standard local media paths
  // Dynamically use the current API URL (e.g., https://nyumbalink-backend.../api/v1 -> https://nyumbalink-backend...)
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}
