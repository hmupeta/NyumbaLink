#!/usr/bin/env python3
"""Fixes listing moderation filtering and bulletproofs media URLs."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Fix ListingFilter
VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# Add status to the ListingFilter class so ?status=SUBMITTED actually works
old_filter = '''class ListingFilter(filters.FilterSet):
    province = filters.CharFilter(field_name="property__neighbourhood__locality__district__province__slug")'''
    
new_filter = '''class ListingFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    province = filters.CharFilter(field_name="property__neighbourhood__locality__district__province__slug")'''

if "status = filters.CharFilter" not in text:
    text = text.replace(old_filter, new_filter)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("Patched views.py: added status filter to ListingFilter")

# ---------------------------------------------------------------- 2. Frontend: Bulletproof URL
API_FILE = FRONTEND / "src" / "api" / "listings.ts"
text = API_FILE.read_text(encoding="utf-8")

new_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // 1. If it's a mangled Unsplash URL like https:/images... fix the slashes
  if (url.includes('https:/') && !url.includes('https://')) {
    return url.replace('https:/', 'https://')
  }

  // 2. If the URL got prefixed with /media/ but is an external link
  if (url.includes('/media/http')) {
    const match = url.match(/https?:\\/\\/.*/)
    if (match) return match[0]
  }
  
  // 3. Clean up encoded URLs
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  
  // 4. Standard external URLs
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 5. Standard local media
  return `http://localhost:8000${url.startsWith('/') ? '' : '/'}${url}`
}'''

# Replace the whole function
import re
text = re.sub(r'export const getMediaUrl = \(url: string\) => \{[\s\S]*?return `http://localhost:8000\$\{url\.startsWith\(\'\/\'\) \? \'\' : \'\/\'\}\$\{url\}`\n\}', new_url_logic, text)

API_FILE.write_text(text, encoding="utf-8")
print("Patched src/api/listings.ts: fixed mangled Unsplash URLs")

# ---------------------------------------------------------------- 3. Frontend: Fix Moderation UI
MOD_FILE = FRONTEND / "src" / "pages" / "ModerationPage.tsx"
text = MOD_FILE.read_text(encoding="utf-8")

# Only show approve/reject buttons if the listing is SUBMITTED
old_action = '''                <div className="flex flex-col justify-center gap-2 w-32">
                  {rejectingId === listing.id ? ('''

new_action = '''                <div className="flex flex-col justify-center gap-2 w-32">
                  {listing.status !== 'SUBMITTED' ? (
                     <span className="text-xs text-center text-gray-500 italic">Already Published</span>
                  ) : rejectingId === listing.id ? ('''

text = text.replace(old_action, new_action)
MOD_FILE.write_text(text, encoding="utf-8")
print("Patched src/pages/ModerationPage.tsx: hide actions for non-submitted listings")

print("""
Done!
  1. Restart your backend (to load the new filter).
  2. Refresh your frontend.
  3. The Moderation Console "Listings" tab should now ONLY show DRAFT or SUBMITTED listings (which might be zero right now, since your demo listings are already published).
  4. The broken Unsplash image in the console will now load correctly!
""")