#!/usr/bin/env python3
"""Fixes notification links and builds the Viewing Requests Dashboard."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Fix (Signals)
SIGNALS_FILE = ROOT / "apps" / "notifications" / "signals.py"
text = SIGNALS_FILE.read_text(encoding="utf-8")

# Change the link for viewing requests to point to a specific tab
text = text.replace(
    'link=f"/dashboard"',
    'link=f"/dashboard?tab=viewings"'
)
SIGNALS_FILE.write_text(text, encoding="utf-8")
print("Patched signals.py: Viewing notification now links to /dashboard?tab=viewings")

# ---------------------------------------------------------------- 2. Frontend: The Viewings Component
# (Recreating this to ensure it exists and uses the correct API)
VIEWINGS_LIST = '''
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { messagingApi } from '../api/messaging'
import Loading from '../components/Loading'

export default function ViewingsList() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['viewings'],
    queryFn: () => messagingApi.listViewings(),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => messagingApi.updateViewingStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['viewings'] })
  })

  if (isLoading) return <Loading />

  return (
    <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
      <table className="w-full text-left">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 font-semibold text-sm">Property</th>
            <th className="px-4 py-3 font-semibold text-sm">Seeker</th>
            <th className="px-4 py-3 font-semibold text-sm">Requested Date</th>
            <th className="px-4 py-3 font-semibold text-sm">Status</th>
            <th className="px-4 py-3 font-semibold text-sm text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data?.results.map((v: any) => (
            <tr key={v.id}>
              <td className="px-4 py-3 text-sm">{v.listing_title}</td>
              <td className="px-4 py-3 text-sm">{v.seeker_email}</td>
              <td className="px-4 py-3 text-sm">{new Date(v.requested_date).toLocaleString()}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  v.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                  v.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>{v.status}</span>
              </td>
              <td className="px-4 py-3 text-right space-x-3">
                {v.status === 'PENDING' ? (
                  <>
                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'APPROVED' })} className="text-emerald-600 text-sm font-medium hover:underline">Approve</button>
                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'REJECTED' })} className="text-red-600 text-sm font-medium hover:underline">Reject</button>
                  </>
                ) : (
                  <span className="text-gray-400 text-sm italic">Action taken</span>
                )}
              </td>
            </tr>
          ))}
          {data?.results.length === 0 && (
            <tr><td colSpan={5} className="p-8 text-center text-gray-500">No viewing requests yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "ViewingsList.tsx").write_text(VIEWINGS_LIST.strip() + "\n", encoding="utf-8")
print("Created src/pages/ViewingsList.tsx")

# ---------------------------------------------------------------- 3. Frontend: Dashboard with Tabs
DASHBOARD_PAGE = '''
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { listingsApi } from '../api/listings'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ViewingsList from './ViewingsList'

export default function DashboardPage() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') || 'listings'

  const { data, isLoading, error } = useQuery({
    queryKey: ['my-listings'],
    queryFn: () => listingsApi.list({ page: 1 }),
  })

  const myListings = data?.results.filter(l => l.created_by === user?.id) || []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold">Landlord Dashboard</h1>
          <p className="text-gray-600">Manage your properties and listing requests.</p>
        </div>
        <div className="flex gap-3">
          <Link
            to={`/profiles/${user?.id}`}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 font-medium text-sm transition"
          >
            View Public Profile
          </Link>
          <Link
            to="/dashboard/listings/new"
            className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium text-sm transition shadow-sm"
          >
            + Create Listing
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b mb-6">
        <button 
          onClick={() => setSearchParams({ tab: 'listings' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'listings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          My Listings
        </button>
        <button 
          onClick={() => setSearchParams({ tab: 'viewings' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'viewings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Viewing Requests
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'listings' ? (
        <>
          {isLoading && <Loading />}
          {error && <ErrorMessage message="Could not load your listings." />}
          
          {data && myListings.length === 0 && (
            <div className="text-center py-12 bg-white rounded border shadow-sm">
              <p className="text-gray-500 mb-4">You haven't created any listings yet.</p>
              <Link to="/dashboard/listings/new" className="text-emerald-600 hover:underline">
                Create your first listing
              </Link>
            </div>
          )}

          {myListings.length > 0 && (
            <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
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
                      <td className="px-4 py-3 text-sm">{l.title}</td>
                      <td className="px-4 py-3 text-sm">{l.currency} {Number(l.price).toLocaleString()}</td>
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
                        <Link to={`/dashboard/listings/${l.id}`} className="text-gray-600 hover:underline text-sm font-medium">Manage</Link>
                        <Link to={`/dashboard/listings/${l.id}/edit`} className="text-emerald-600 hover:underline text-sm font-medium">Edit</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <ViewingsList />
      )}
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "DashboardPage.tsx").write_text(DASHBOARD_PAGE.strip() + "\n", encoding="utf-8")
print("Patched DashboardPage.tsx: added tabs for Listings and Viewings")

print("""
Done! Restart your backend and frontend.

Test the flow:
  1. Go to the Dashboard and click the "Viewing Requests" tab.
  2. You will see the pending viewing request from the seeker.
  3. Click the Bell icon, and click the notification again.
  4. Notice how it automatically switches the dashboard to the "Viewing Requests" tab!
  5. Click "Approve" to confirm the viewing.
""")