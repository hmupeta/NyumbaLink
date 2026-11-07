import { api } from './client'
import type { Listing } from './types'

export const moderationApi = {
  // Listings
  getPendingListings: () => api<{results: Listing[]}>('/listings/?status=SUBMITTED'),
  approveListing: (id: string) => api(`/listings/${id}/publish/`, {
    method: 'POST', body: JSON.stringify({ note: 'Approved by staff' })
  }),
  rejectListing: (id: string, reason: string) => api(`/listings/${id}/reject/`, {
    method: 'POST', body: JSON.stringify({ reason })
  }),

  // KYC / Verifications
  getPendingKYC: () => api<{results: any[]}>('/verifications/?status=PENDING'),
  approveKYC: (id: string) => api(`/verifications/${id}/approve/`, { method: 'POST' }),
  rejectKYC: (id: string, reason: string) => api(`/verifications/${id}/reject/`, {
    method: 'POST', body: JSON.stringify({ reason })
  }),
  getKycHistory: () => api<{results: any[]}>('/verifications/'),

  // Reports
  getReports: () => api<{results: any[]}>('/reports/?status=OPEN'),
  resolveReport: (id: string) => api(`/reports/${id}/`, {
    method: 'PATCH', body: JSON.stringify({ status: 'RESOLVED' })
  })
}
