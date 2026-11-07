#!/usr/bin/env python3
"""Adds a 'Submit for Review' button so drafts enter the moderation queue."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Frontend API
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

if "submitForReview" not in text:
    text = text.replace(
        "  getMyListings: () => api<Paginated<Listing>>('/listings/my_listings/'),",
        "  getMyListings: () => api<Paginated<Listing>>('/listings/my_listings/'),\n  submitForReview: (id: string) => api(`/listings/${id}/submit/`, { method: 'POST' }),"
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("Patched listings.ts: added submitForReview")

# ---------------------------------------------------------------- 2. Frontend Dashboard
DASHBOARD_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASHBOARD_FILE.read_text(encoding="utf-8")

if "submitForReview" not in text:
    # Add the mutation
    text = text.replace(
        "  const { data, isLoading, error } = useQuery({",
        '''  const submitMutation = useMutation({
    mutationFn: (id: string) => listingsApi.submitForReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-listings'] })
      alert('Listing submitted for review!')
    }
  })

  const { data, isLoading, error } = useQuery({'''
    )
    
    # Ensure useMutation and useQueryClient are imported
    text = text.replace(
        "import { useQuery } from '@tanstack/react-query'",
        "import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'"
    )
    
    # Add queryClient instantiation
    text = text.replace(
        "  const activeTab = searchParams.get('tab') || 'listings'",
        "  const activeTab = searchParams.get('tab') || 'listings'\n  const queryClient = useQueryClient()"
    )

    # Update the Actions column to include the Submit button
    old_actions = '''                      <td className="px-4 py-3 text-right space-x-3">
                        <Link to={`/dashboard/listings/${l.id}`} className="text-gray-600 hover:underline text-sm font-medium">Manage</Link>
                        <Link to={`/dashboard/listings/${l.id}/edit`} className="text-emerald-600 hover:underline text-sm font-medium">Edit</Link>
                      </td>'''
    
    new_actions = '''                      <td className="px-4 py-3 text-right space-x-3">
                        {l.status === 'DRAFT' && (
                          <button 
                            onClick={() => submitMutation.mutate(l.id)}
                            disabled={submitMutation.isPending}
                            className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded text-xs font-bold hover:bg-emerald-200 transition"
                          >
                            Submit for Review
                          </button>
                        )}
                        <Link to={`/dashboard/listings/${l.id}`} className="text-gray-600 hover:underline text-sm font-medium">Manage</Link>
                        <Link to={`/dashboard/listings/${l.id}/edit`} className="text-emerald-600 hover:underline text-sm font-medium">Edit</Link>
                      </td>'''
    
    text = text.replace(old_actions, new_actions)
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("Patched DashboardPage.tsx: added Submit for Review button")

print("""
Fix applied! 

  1. Restart your frontend (npm run dev).
  2. Log in as the Landlord (demo@nyumbalink.com).
  3. Go to your Dashboard.
  4. Next to the "DRAFT" listing, you will now see a green "Submit for Review" button.
  5. Click it.
  6. Log back in as the Superuser (howardmupeta@nyumbalink.com) and go to Moderation -> Listings.
  7. The listing will now be waiting there for your approval!
""")