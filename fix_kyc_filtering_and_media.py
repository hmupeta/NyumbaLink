#!/usr/bin/env python3
"""Fixes KYC status filtering, disables approval for empty KYC, and fixes media URLs."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Add Filtering
VIEWS_FILE = ROOT / "apps" / "verification" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "filterset_fields" not in text:
    text = text.replace(
        "    http_method_names = [\"get\", \"post\", \"head\", \"options\"]",
        "    http_method_names = [\"get\", \"post\", \"head\", \"options\"]\n    filterset_fields = (\"status\", \"verification_type\")"
    )
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched apps/verification/views.py: added filterset_fields")

# ---------------------------------------------------------------- 2. Frontend: Bulletproof getMediaUrl
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

old_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // Clean up encoded URLs (from dummy seed data)
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  
  // If it's already an external URL (like Unsplash), return it directly
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // Sometimes Django pre-formats the URL incorrectly with a single slash
  if (url.startsWith('/media/https:/')) {
     return 'https://' + url.replace('/media/https:/', '')
  }

  // Otherwise, it's a local media file
  return `http://localhost:8000${url.startsWith('/') ? '' : '/'}${url}`
}'''

new_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // If the URL is somehow prefixed with /media/ but contains http
  if (url.includes('/media/http')) {
    const match = url.match(/https?:\\/\\/.*/)
    if (match) return match[0]
  }
  
  // Clean up encoded URLs
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  
  // Standard external URLs
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // Standard local media
  return `http://localhost:8000${url.startsWith('/') ? '' : '/'}${url}`
}'''

text = text.replace(old_url_logic, new_url_logic)
API_FILE.write_text(text, encoding="utf-8")
print("Patched src/api/listings.ts: fixed getMediaUrl regex")

# ---------------------------------------------------------------- 3. Frontend: Moderation UX
MOD_FILE = FRONTEND / "src" / "pages" / "ModerationPage.tsx"
text = MOD_FILE.read_text(encoding="utf-8")

# We only change the KYC render section
old_kyc_action = '''                  <div className="flex gap-2">
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
                  </div>'''

new_kyc_action = '''                  <div className="flex gap-2">
                    {rejectingId === kyc.id ? (
                      <div className="flex gap-2 items-center">
                        <input type="text" placeholder="Reason..." value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="border rounded px-2 py-1 text-sm w-48" />
                        <button onClick={() => rejectKYC.mutate({ id: kyc.id, reason: rejectReason })} className="bg-red-600 text-white px-3 py-1 rounded text-sm">Confirm</button>
                        <button onClick={() => setRejectingId(null)} className="bg-gray-200 px-3 py-1 rounded text-sm">Cancel</button>
                      </div>
                    ) : (
                      <>
                        <button 
                          onClick={() => approveKYC.mutate(kyc.id)} 
                          disabled={kyc.documents.length === 0}
                          className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Approve
                        </button>
                        <button onClick={() => setRejectingId(kyc.id)} className="bg-white border border-red-600 text-red-600 px-4 py-2 rounded hover:bg-red-50 font-medium text-sm">Reject</button>
                      </>
                    )}
                  </div>'''

text = text.replace(old_kyc_action, new_kyc_action)

# Add a visual warning if no documents are uploaded
old_doc_warning = '''                    {kyc.documents.length === 0 && <span className="text-sm text-gray-400">No documents uploaded.</span>}'''
new_doc_warning = '''                    {kyc.documents.length === 0 && <span className="text-sm text-red-500 font-medium">No documents uploaded. You must reject this request.</span>}'''
text = text.replace(old_doc_warning, new_doc_warning)

MOD_FILE.write_text(text, encoding="utf-8")
print("Patched src/pages/ModerationPage.tsx: disabled Approve button when no docs")

print("""
Fixes applied!
  1. Restart your backend.
  2. Refresh your frontend (npm run dev).
  3. KYC rejections will now immediately remove the item from the list.
  4. The "Approve" button will be greyed out and disabled if the user forgot to upload documents.
  5. The external Unsplash image will now load properly without breaking.
""")