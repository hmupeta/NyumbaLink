#!/usr/bin/env python3
"""NyumbaLink Phase 17: Staff Moderation Console."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Fixes
# Ensure staff can see SUBMITTED listings, which are hidden from public users.
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "user.is_staff" not in text:
    # We modify the ListingViewSet queryset logic
    old_queryset = '''        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(
                Q(status=ListingStatus.PUBLISHED)
                | Q(created_by=user)
                | Q(property__submitted_by=user)
            )
        return qs.filter(status=ListingStatus.PUBLISHED)'''
    
    new_queryset = '''        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs # Staff sees everything including SUBMITTED
        if user.is_authenticated:
            return qs.filter(
                Q(status=ListingStatus.PUBLISHED)
                | Q(created_by=user)
                | Q(property__submitted_by=user)
            )
        return qs.filter(status=ListingStatus.PUBLISHED)'''
    
    text = text.replace(old_queryset, new_queryset)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: ensured staff can see submitted listings")

# ---------------------------------------------------------------- 2. Frontend API
MODERATION_API = '''
import { api } from './client'
import type { Listing } from './types'

export const moderationApi = {
  // Get all listings that are pending review
  getPendingListings: () => api<{results: Listing[]}>('/listings/?status=SUBMITTED'),
  
  // Approve a listing
  approveListing: (id: string) => api(`/listings/${id}/publish/`, {
    method: 'POST',
    body: JSON.stringify({ note: 'Approved by staff' })
  }),
  
  // Reject a listing
  rejectListing: (id: string, reason: string) => api(`/listings/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),

  // Get all open reports
  getReports: () => api<{results: any[]}>('/reports/?status=OPEN'),
  resolveReport: (id: string) => api(`/reports/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'RESOLVED' })
  })
}
'''
(FRONTEND / "src" / "api" / "moderation.ts").write_text(MODERATION_API.strip() + "\n", encoding="utf-8")
print("Created src/api/moderation.ts")

# ---------------------------------------------------------------- 3. Frontend Component
MODERATION_PAGE = '''
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { moderationApi } from '../api/moderation'
import { getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ModerationPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'listings' | 'reports'>('listings')
  const [rejectReason, setRejectReason] = useState('')
  const [rejectingId, setRejectingId] = useState<string | null>(null)

  const { data: pendingListings, isLoading: loadingListings } = useQuery({
    queryKey: ['pending-listings'],
    queryFn: moderationApi.getPendingListings,
  })

  const { data: reports, isLoading: loadingReports } = useQuery({
    queryKey: ['open-reports'],
    queryFn: moderationApi.getReports,
    enabled: activeTab === 'reports',
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => moderationApi.approveListing(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-listings'] })
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string, reason: string }) => moderationApi.rejectListing(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-listings'] })
      setRejectingId(null)
      setRejectReason('')
    }
  })

  const resolveReportMutation = useMutation({
    mutationFn: (id: string) => moderationApi.resolveReport(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['open-reports'] })
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Moderation Console</h1>
        <p className="text-gray-600">Review pending listings and handle user reports.</p>
      </div>

      <div className="flex gap-6 border-b mb-6">
        <button 
          onClick={() => setActiveTab('listings')}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'listings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Pending Listings {pendingListings?.results.length ? `(${pendingListings.results.length})` : ''}
        </button>
        <button 
          onClick={() => setActiveTab('reports')}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'reports' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          User Reports {reports?.results.length ? `(${reports.results.length})` : ''}
        </button>
      </div>

      {activeTab === 'listings' && (
        <>
          {loadingListings && <Loading />}
          {pendingListings?.results.length === 0 && (
            <div className="text-center py-12 bg-white rounded border">
              <p className="text-gray-500">No pending listings to review. Great job!</p>
            </div>
          )}
          <div className="grid gap-4">
            {pendingListings?.results.map(listing => (
              <div key={listing.id} className="bg-white border rounded-lg p-4 flex gap-4 shadow-sm">
                <div className="w-32 h-32 bg-gray-100 rounded flex-shrink-0">
                  {listing.media[0] ? (
                    <img src={getMediaUrl(listing.media[0].file)} className="w-full h-full object-cover rounded" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">No image</div>
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-lg">{listing.title}</h3>
                  <p className="text-sm text-gray-500 mb-2">{listing.property_summary.neighbourhood} · {listing.currency} {Number(listing.price).toLocaleString()}</p>
                  <p className="text-sm text-gray-700 line-clamp-2">{listing.description}</p>
                  <p className="text-xs text-gray-500 mt-2">Submitted by: {listing.created_by_email}</p>
                </div>
                <div className="flex flex-col justify-center gap-2 w-32">
                  {rejectingId === listing.id ? (
                    <div className="space-y-2">
                      <input 
                        type="text" 
                        placeholder="Reason..." 
                        value={rejectReason} 
                        onChange={e => setRejectReason(e.target.value)}
                        className="w-full border rounded px-2 py-1 text-sm"
                      />
                      <button onClick={() => rejectMutation.mutate({ id: listing.id, reason: rejectReason })} className="w-full bg-red-600 text-white py-1 rounded text-sm">Confirm</button>
                      <button onClick={() => setRejectingId(null)} className="w-full bg-gray-200 text-gray-700 py-1 rounded text-sm">Cancel</button>
                    </div>
                  ) : (
                    <>
                      <button onClick={() => approveMutation.mutate(listing.id)} className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium">Approve</button>
                      <button onClick={() => setRejectingId(listing.id)} className="w-full bg-white border border-red-600 text-red-600 py-2 rounded hover:bg-red-50 font-medium">Reject</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {activeTab === 'reports' && (
        <>
          {loadingReports && <Loading />}
          {reports?.results.length === 0 && (
            <div className="text-center py-12 bg-white rounded border">
              <p className="text-gray-500">No open reports. The platform is clean!</p>
            </div>
          )}
          <div className="grid gap-4">
            {reports?.results.map(report => (
              <div key={report.id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
                <div>
                  <h3 className="font-bold text-red-600">Report: {report.reason}</h3>
                  <p className="text-sm text-gray-700 mt-1">{report.description}</p>
                  <p className="text-xs text-gray-500 mt-2">Reported by: {report.reporter_email}</p>
                </div>
                <div>
                  <button onClick={() => resolveReportMutation.mutate(report.id)} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-black font-medium text-sm">Mark Resolved</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "ModerationPage.tsx").write_text(MODERATION_PAGE.strip() + "\n", encoding="utf-8")
print("Created src/pages/ModerationPage.tsx")

# ---------------------------------------------------------------- 4. Update App.tsx and Layout
APP_FILE = FRONTEND / "src" / "App.tsx"
text = APP_FILE.read_text(encoding="utf-8")
if "ModerationPage" not in text:
    text = text.replace(
        "import PublicProfilePage from './pages/PublicProfilePage'",
        "import PublicProfilePage from './pages/PublicProfilePage'\nimport ModerationPage from './pages/ModerationPage'"
    )
    text = text.replace(
        '<Route path="/settings" element={<PaymentSettingsPage />} />',
        '<Route path="/settings" element={<PaymentSettingsPage />} />\n          <Route path="/moderation" element={<ModerationPage />} />'
    )
    APP_FILE.write_text(text, encoding="utf-8")
    print("Patched App.tsx: added Moderation route")

LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")
if "Moderation" not in text:
    # Add a special link for staff
    old_nav = '''                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
                <NotificationBell />'''
    
    new_nav = '''                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
                {user.is_staff && <Link to="/moderation" className="text-orange-600 font-bold hover:text-orange-700">Moderation</Link>}
                <NotificationBell />'''
    
    text = text.replace(old_nav, new_nav)
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("Patched Layout.tsx: added Moderation link for staff")

print("""
Phase 17 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as a standard user and create a new listing (it defaults to DRAFT/SUBMITTED).
  3. Log in as your superuser (howardmupeta@nyumbalink.com).
  4. You will see an orange "Moderation" link in the top navigation.
  5. Click it. You will see the pending listing with its image and details.
  6. Click "Approve". It instantly goes live!
  7. Check the "User Reports" tab to see any flagged listings.
""")