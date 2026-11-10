#!/usr/bin/env python3
"""Forces the React frontend to only fetch PUBLISHED listings on the public site."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Frontend: Force status=PUBLISHED in listingsApi.list()
# ----------------------------------------------------------------
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

old_list = '''  list: (filters: ListingFilters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    const qs = params.toString()
    return api<Paginated<Listing>>(`/listings/${qs ? `?${qs}` : ''}`)
  },'''

new_list = '''  list: (filters: ListingFilters = {}) => {
    const params = new URLSearchParams()
    
    // FORCE PUBLIC LISTINGS TO ONLY SHOW PUBLISHED
    params.append('status', 'PUBLISHED')

    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    const qs = params.toString()
    return api<Paginated<Listing>>(`/listings/${qs ? `?${qs}` : ''}`)
  },'''

if old_list in text:
    text = text.replace(old_list, new_list)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listings.ts: Public list now forces status=PUBLISHED")
else:
    print("⚠️ Could not find the exact list method in listings.ts.")

# ----------------------------------------------------------------
# 2. Frontend: Ensure HomePage refetches on mount (bypasses cache)
# ----------------------------------------------------------------
HOME_FILE = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = HOME_FILE.read_text(encoding="utf-8")

old_query = '''  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
  })'''

new_query = '''  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
    staleTime: 0,
    refetchOnMount: 'always',
  })'''

if old_query in text:
    text = text.replace(old_query, new_query)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched HomePage.tsx: Forced refetch on mount")
else:
    print("⚠️ Could not find exact useQuery block in HomePage.tsx.")

# ----------------------------------------------------------------
# 3. Push to GitHub (Render will rebuild automatically)
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Force public web listings to only show PUBLISHED"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 WEB CACHE AND FILTER FIX PUSHED!
==================================================

Wait about 2 minutes for Render to deploy the frontend, then:
1. Hard refresh your Web browser (Ctrl + Shift + R).
2. The Draft listing will disappear from the public homepage.
3. It will still be visible in your Landlord Dashboard and Moderation Console.
""")