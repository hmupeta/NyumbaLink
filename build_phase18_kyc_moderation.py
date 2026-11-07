#!/usr/bin/env python3
"""NyumbaLink Phase 18: KYC Moderation in the React Console."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Verification Views
# Add approve/reject actions to the VerificationCaseViewSet
VIEWS_FILE = ROOT / "apps" / "verification" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "def approve(self, request, pk=None):" not in text:
    # Add imports
    text = text.replace(
        "from rest_framework.response import Response",
        "from rest_framework.response import Response\nfrom django.utils import timezone\nfrom apps.notifications.services import create_notification"
    )
    
    # Add the actions
    text += '''

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can approve."}, status=403)
        case = self.get_object()
        case.status = "APPROVED"
        case.reviewed_by = request.user
        case.reviewed_at = timezone.now()
        case.save()

        create_notification(
            user=case.user,
            title="Verification Approved",
            message=f"Your {case.get_verification_type_display()} has been approved!",
            link=f"/profiles/{case.user.id}"
        )
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can reject."}, status=403)
        case = self.get_object()
        reason = request.data.get("reason", "Documents unclear or invalid.")
        case.status = "REJECTED"
        case.rejection_reason = reason
        case.reviewed_by = request.user
        case.reviewed_at = timezone.now()
        case.save()

        create_notification(
            user=case.user,
            title="Verification Rejected",
            message=f"Your {case.get_verification_type_display()} was rejected: {reason}",
            link=f"/verification"
        )
        return Response({"status": "rejected"})
'''
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched apps/verification/views.py: added approve/reject actions")


# ---------------------------------------------------------------- 2. Frontend API
MODERATION_API = '''
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

  // Reports
  getReports: () => api<{results: any[]}>('/reports/?status=OPEN'),
  resolveReport: (id: string) => api(`/reports/${id}/`, {
    method: 'PATCH', body: JSON.stringify({ status: 'RESOLVED' })
  })
}
'''
(FRONTEND / "src" / "api" / "moderation.ts").write_text(MODERATION_API.strip() + "\n", encoding="utf-8")
print("Patched src/api/moderation.ts: added KYC endpoints")

# ---------------------------------------------------------------- 3. Frontend Moderation Page
MODERATION_PAGE = '''
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { moderationApi } from '../api/moderation'
import { getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'

export default function ModerationPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'listings' | 'kyc' | 'reports'>('listings')
  
  // Rejection state
  const [rejectReason, setRejectReason] = useState('')
  const [rejectingId, setRejectingId] = useState<string | null>(null)

  // --- Queries ---
  const { data: pendingListings, isLoading: loadingListings } = useQuery({
    queryKey: ['pending-listings'],
    queryFn: moderationApi.getPendingListings,
  })

  const { data: pendingKYC, isLoading: loadingKYC } = useQuery({
    queryKey: ['pending-kyc'],
    queryFn: moderationApi.getPendingKYC,
    enabled: activeTab === 'kyc',
  })

  const { data: reports, isLoading: loadingReports } = useQuery({
    queryKey: ['open-reports'],
    queryFn: moderationApi.getReports,
    enabled: activeTab === 'reports',
  })

  // --- Mutations ---
  const approveListing = useMutation({
    mutationFn: (id: string) => moderationApi.approveListing(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-listings'] })
  })
  const rejectListing = useMutation({
    mutationFn: ({ id, reason }: { id: string, reason: string }) => moderationApi.rejectListing(id, reason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending-listings'] }); setRejectingId(null); setRejectReason('') }
  })

  const approveKYC = useMutation({
    mutationFn: (id: string) => moderationApi.approveKYC(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-kyc'] })
  })
  const rejectKYC = useMutation({
    mutationFn: ({ id, reason }: { id: string, reason: string }) => moderationApi.rejectKYC(id, reason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending-kyc'] }); setRejectingId(null); setRejectReason('') }
  })

  const resolveReport = useMutation({
    mutationFn: (id: string) => moderationApi.resolveReport(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['open-reports'] })
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Moderation Console</h1>
        <p className="text-gray-600">Review pending listings, KYC applications, and user reports.</p>
      </div>

      <div className="flex gap-6 border-b mb-6">
        <button onClick={() => setActiveTab('listings')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'listings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          Listings {pendingListings?.results.length ? `(${pendingListings.results.length})` : ''}
        </button>
        <button onClick={() => setActiveTab('kyc')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'kyc' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          KYC Requests {pendingKYC?.results.length ? `(${pendingKYC.results.length})` : ''}
        </button>
        <button onClick={() => setActiveTab('reports')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'reports' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          Reports {reports?.results.length ? `(${reports.results.length})` : ''}
        </button>
      </div>

      {/* LISTINGS TAB */}
      {activeTab === 'listings' && (
        <>
          {loadingListings && <Loading />}
          {pendingListings?.results.length === 0 && <p className="text-gray-500 py-8">No pending listings.</p>}
          <div className="grid gap-4">
            {pendingListings?.results.map(listing => (
              <div key={listing.id} className="bg-white border rounded-lg p-4 flex gap-4 shadow-sm">
                <div className="w-32 h-32 bg-gray-100 rounded flex-shrink-0">
                  {listing.media[0] && <img src={getMediaUrl(listing.media[0].file)} className="w-full h-full object-cover rounded" />}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-lg">{listing.title}</h3>
                  <p className="text-sm text-gray-500 mb-1">{listing.property_summary.neighbourhood} · {listing.currency} {Number(listing.price).toLocaleString()}</p>
                  <p className="text-xs text-gray-500">By: {listing.created_by_email}</p>
                </div>
                <div className="flex flex-col justify-center gap-2 w-32">
                  {rejectingId === listing.id ? (
                    <div className="space-y-2">
                      <input type="text" placeholder="Reason..." value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="w-full border rounded px-2 py-1 text-sm" />
                      <button onClick={() => rejectListing.mutate({ id: listing.id, reason: rejectReason })} className="w-full bg-red-600 text-white py-1 rounded text-sm">Confirm</button>
                      <button onClick={() => setRejectingId(null)} className="w-full bg-gray-200 text-gray-700 py-1 rounded text-sm">Cancel</button>
                    </div>
                  ) : (
                    <>
                      <button onClick={() => approveListing.mutate(listing.id)} className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium">Approve</button>
                      <button onClick={() => setRejectingId(listing.id)} className="w-full bg-white border border-red-600 text-red-600 py-2 rounded hover:bg-red-50 font-medium">Reject</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* KYC TAB */}
      {activeTab === 'kyc' && (
        <>
          {loadingKYC && <Loading />}
          {pendingKYC?.results.length === 0 && <p className="text-gray-500 py-8">No pending KYC requests.</p>}
          <div className="grid gap-4">
            {pendingKYC?.results.map((kyc: any) => (
              <div key={kyc.id} className="bg-white border rounded-lg p-4 shadow-sm">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-bold text-lg text-gray-900">{kyc.type_label}</h3>
                    <p className="text-sm text-gray-600">User: <span className="font-medium text-gray-900">{kyc.user_email}</span></p>
                    <p className="text-xs text-gray-400 mt-1">Submitted: {new Date(kyc.created_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex gap-2">
                    {rejectingId === kyc.id ? (
                      <div className="flex gap-2 items-center">
                        <input type="text" placeholder="Reason..." value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="border rounded px-2 py-1 text-sm w-48" />
                        <button onClick={() => rejectKYC.mutate({ id: kyc.id, reason: rejectReason })} className="bg-red-600 text-white px-3 py-1 rounded text-sm">Confirm</button>
                        <button onClick={() => setRejectingId(null)} className="bg-gray-200 px-3 py-1 rounded text-sm">Cancel</button>
                      </div>
                    ) : (
                      <>
                        <button onClick={() => approveKYC.mutate(kyc.id)} className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium text-sm">Approve</button>
                        <button onClick={() => setRejectingId(kyc.id)} className="bg-white border border-red-600 text-red-600 px-4 py-2 rounded hover:bg-red-50 font-medium text-sm">Reject</button>
                      </>
                    )}
                  </div>
                </div>
                
                {/* Documents */}
                <div className="bg-gray-50 p-3 rounded border">
                  <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Attached Documents</h4>
                  <div className="flex gap-4">
                    {kyc.documents.map((doc: any) => (
                      <a key={doc.id} href={getMediaUrl(doc.file)} target="_blank" rel="noreferrer" className="flex items-center gap-2 bg-white border px-3 py-2 rounded shadow-sm hover:shadow-md transition">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                        <span className="text-sm font-medium text-gray-700">{doc.document_type}</span>
                      </a>
                    ))}
                    {kyc.documents.length === 0 && <span className="text-sm text-gray-400">No documents uploaded.</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* REPORTS TAB */}
      {activeTab === 'reports' && (
        <>
          {loadingReports && <Loading />}
          {reports?.results.length === 0 && <p className="text-gray-500 py-8">No open reports.</p>}
          <div className="grid gap-4">
            {reports?.results.map(report => (
              <div key={report.id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
                <div>
                  <h3 className="font-bold text-red-600">Report: {report.reason}</h3>
                  <p className="text-sm text-gray-700 mt-1">{report.description}</p>
                  <p className="text-xs text-gray-500 mt-2">By: {report.reporter_email}</p>
                </div>
                <button onClick={() => resolveReport.mutate(report.id)} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-black font-medium text-sm">Mark Resolved</button>
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
print("Patched src/pages/ModerationPage.tsx: added KYC Tab")

print("""
Phase 18 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as a standard user (e.g. demo@nyumbalink.com).
  3. Go to the Verification page and click "Start Verification". Upload a dummy image.
  4. Log out, and log in as the Superuser (howardmupeta@nyumbalink.com).
  5. Go to Moderation. You will see a new tab called "KYC Requests (1)".
  6. Click it. You will see the user's request and a clickable link to the document they uploaded.
  7. Click Approve.
  8. Check the Notifications bell on the standard user's account (or their profile) to see the approval reflected!
""")