#!/usr/bin/env python3
"""Adds the ability for users to report listings."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Frontend API
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

if "submitReport" not in text:
    text = text.replace(
        "  getAnalytics: () => api<any>('/listings/analytics/'),",
        "  getAnalytics: () => api<any>('/listings/analytics/'),\n  submitReport: (listingId: string, reason: string, description: string) => api('/reports/', {\n    method: 'POST',\n    body: JSON.stringify({ target_listing: listingId, reason, description })\n  }),"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("Patched listings.ts: added submitReport")

# ---------------------------------------------------------------- 2. Frontend Detail Page
DETAIL_FILE = FRONTEND / "src" / "pages" / "ListingDetailPage.tsx"
text = DETAIL_FILE.read_text(encoding="utf-8")

if "Report Listing" not in text:
    # Add state for the modal
    text = text.replace(
        "  const [showViewingModal, setShowViewingModal] = useState(false)",
        "  const [showViewingModal, setShowViewingModal] = useState(false)\n  const [showReportModal, setShowReportModal] = useState(false)\n  const [reportReason, setReportReason] = useState('FRAUD')\n  const [reportDesc, setReportDesc] = useState('')"
    )

    # Add mutation
    text = text.replace(
        "  const viewingMutation = useMutation({",
        "  const reportMutation = useMutation({\n    mutationFn: () => listingsApi.submitReport(id!, reportReason, reportDesc),\n    onSuccess: () => {\n      setShowReportModal(false)\n      alert('Thank you. Your report has been submitted to our moderation team.')\n    },\n    onError: () => alert('Failed to submit report.')\n  })\n\n  const viewingMutation = useMutation({"
    )

    # Add the "Report" link under the 'Advertised by' section
    old_advertised = '''          {/* THE ADVERTISED BY LINK */}
          <div className="mt-6 pt-4 border-t text-center">
             <p className="text-xs text-gray-500 mb-1">Advertised by</p>
             <Link to={`/profiles/${listing.created_by}`} className="text-sm font-bold text-emerald-700 hover:underline">
                View Landlord Profile
             </Link>
          </div>'''
    
    new_advertised = '''          {/* THE ADVERTISED BY LINK */}
          <div className="mt-6 pt-4 border-t text-center">
             <p className="text-xs text-gray-500 mb-1">Advertised by</p>
             <Link to={`/profiles/${listing.created_by}`} className="text-sm font-bold text-emerald-700 hover:underline">
                View Landlord Profile
             </Link>
             {user && user.id !== listing.created_by && (
               <button onClick={() => setShowReportModal(true)} className="block mx-auto mt-4 text-xs text-red-500 hover:underline">
                 Report this Listing
               </button>
             )}
          </div>'''

    text = text.replace(old_advertised, new_advertised)

    # Add the Modal at the bottom before the closing </div>
    old_modals = '''      {showViewingModal && ('''
    new_modals = '''      {showReportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-96">
            <h2 className="text-lg font-bold mb-4 text-red-600">Report Listing</h2>
            <p className="text-sm text-gray-600 mb-4">Help us keep NyumbaLink safe. Why are you reporting this?</p>
            
            <select value={reportReason} onChange={e => setReportReason(e.target.value)} className="w-full border rounded px-3 py-2 mb-3 text-sm">
              <option value="FRAUD">Fraud or Scam</option>
              <option value="DUPLICATE">Duplicate Listing</option>
              <option value="WRONG_INFO">Inaccurate Information</option>
              <option value="UNAVAILABLE">Property No Longer Available</option>
              <option value="OFFENSIVE">Offensive Content</option>
            </select>

            <textarea 
              value={reportDesc} onChange={e => setReportDesc(e.target.value)}
              placeholder="Additional details (optional)..." 
              className="w-full border rounded px-3 py-2 mb-4 text-sm" rows={3}
            />

            <div className="flex gap-2">
              <button onClick={() => setShowReportModal(false)} className="flex-1 bg-gray-100 py-2 rounded hover:bg-gray-200">Cancel</button>
              <button 
                onClick={() => reportMutation.mutate()} 
                disabled={reportMutation.isPending}
                className="flex-1 bg-red-600 text-white py-2 rounded hover:bg-red-700 disabled:opacity-50"
              >
                {reportMutation.isPending ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showViewingModal && ('''

    text = text.replace(old_modals, new_modals)
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("Patched ListingDetailPage.tsx: added report modal and button")

print("""
Done! Restart your frontend (npm run dev).

How to test:
  1. Log in as a Seeker (e.g., seeker@nyumbalink.com).
  2. Go to any listing.
  3. At the bottom of the right-hand contact card, click "Report this Listing" in red.
  4. Select a reason and submit.
  5. Log in as the Superuser (howardmupeta@nyumbalink.com).
  6. Go to Moderation -> Reports.
  7. You will now see the report! Click "Mark Resolved" to clear it.
""")