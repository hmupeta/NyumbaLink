#!/usr/bin/env python3
"""Fixes dashboard caching and adds explicit error/data debugging."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Fix Dashboard Page
DASH_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASH_FILE.read_text(encoding="utf-8")

# Force refetch on mount and disable stale time
if "staleTime: 0" not in text:
    text = text.replace(
        "  const { data, isLoading, error } = useQuery({\n    queryKey: ['my-listings'],\n    queryFn: () => listingsApi.getMyListings(),\n  })",
        "  const { data, isLoading, error, refetch } = useQuery({\n    queryKey: ['my-listings'],\n    queryFn: () => listingsApi.getMyListings(),\n    staleTime: 0,\n    refetchOnMount: 'always',\n  })"
    )
    
    # Add a refresh button next to the Create Listing button
    text = text.replace(
        '''        <div className="flex gap-3">
          <Link
            to={`/profiles/${user?.id}`}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 font-medium text-sm transition"
          >
            View Public Profile
          </Link>''',
        '''        <div className="flex gap-3">
          <button 
            onClick={() => refetch()} 
            className="bg-gray-100 border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-200 font-medium text-sm transition"
          >
            Refresh Data
          </button>
          <Link
            to={`/profiles/${user?.id}`}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 font-medium text-sm transition"
          >
            View Public Profile
          </Link>'''
    )
    
    # Add debug info to the empty state
    text = text.replace(
        '''            <div className="text-center py-12 bg-white rounded border shadow-sm">
              <p className="text-gray-500 mb-4">You haven't created any listings yet.</p>
              <Link to="/dashboard/listings/new" className="text-emerald-600 hover:underline">
                Create your first listing
              </Link>
            </div>''',
        '''            <div className="text-center py-12 bg-white rounded border shadow-sm">
              <p className="text-gray-500 mb-4">You haven't created any listings yet.</p>
              <p className="text-xs text-gray-400 mb-4">(Backend returned count: {data?.count || 0})</p>
              <Link to="/dashboard/listings/new" className="text-emerald-600 hover:underline">
                Create your first listing
              </Link>
            </div>'''
    )
    
    DASH_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched DashboardPage.tsx: Disabled caching, added Refresh button, added debug count")

# ---------------------------------------------------------------- 2. Update React Query Client
MAIN_FILE = FRONTEND / "src" / "main.tsx"
text = MAIN_FILE.read_text(encoding="utf-8")

if "staleTime: 0" not in text:
    text = text.replace(
        "defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 } },",
        "defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true, staleTime: 0 } },"
    )
    MAIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched main.tsx: Changed global cache staleTime to 0")

# ---------------------------------------------------------------- 3. Push
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Dashboard caching and add refresh button"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Next steps:
1. Wait for Render to finish deploying the Frontend.
2. Open your live site and go to the Dashboard.
3. Click the new "Refresh Data" button.
4. If it still says "You haven't created any listings yet", look at the small text below it.

It will now say "(Backend returned count: X)".

- If it says "count: 0", the backend is not finding the listings for your user.
- If it says "count: 2", the UI is failing to render them.
""")