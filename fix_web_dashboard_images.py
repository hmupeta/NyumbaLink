#!/usr/bin/env python3
"""Adds scrollable galleries to ManageListingPage and thumbnails to DashboardPage."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Update DashboardPage.tsx (Add Thumbnails)
# ----------------------------------------------------------------
DASH_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASH_FILE.read_text(encoding="utf-8")

# Ensure getMediaUrl is imported
if "getMediaUrl" not in text:
    text = text.replace(
        "import { listingsApi } from '../api/listings'",
        "import { listingsApi, getMediaUrl } from '../api/listings'"
    )

# Replace the Title column with a flex container containing the thumbnail
old_title_cell = '''                      <td className="px-4 py-3 text-sm">{l.title}</td>'''
new_title_cell = '''                      <td className="px-4 py-3 text-sm">
                        <div className="flex items-center gap-3">
                          {l.media?.length > 0 && l.media[0].media_type === 'IMAGE' ? (
                            <img 
                              src={getMediaUrl(l.media[0].file)} 
                              alt={l.title} 
                              className="w-12 h-12 rounded object-cover shadow-sm border"
                            />
                          ) : (
                            <div className="w-12 h-12 rounded bg-gray-100 border flex items-center justify-center text-xs text-gray-400">
                              No Img
                            </div>
                          )}
                          <span className="font-medium line-clamp-2">{l.title}</span>
                        </div>
                      </td>'''

if old_title_cell in text:
    text = text.replace(old_title_cell, new_title_cell)
    DASH_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched DashboardPage.tsx: Added property thumbnails")
else:
    print("⚠️ Could not find exact title cell in DashboardPage.tsx")

# ----------------------------------------------------------------
# 2. Update ManageListingPage.tsx (Scrollable Gallery)
# ----------------------------------------------------------------
MANAGE_FILE = FRONTEND / "src" / "pages" / "ManageListingPage.tsx"
text = MANAGE_FILE.read_text(encoding="utf-8")

# Find the single image block
old_image_block = '''          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="aspect-video bg-gray-100 flex items-center justify-center">
              {listing.media[0] ? (
                <img src={getMediaUrl(listing.media[0].file)} alt="Cover" className="w-full h-full object-cover" />
              ) : (
                <span className="text-gray-400">No image uploaded</span>
              )}
            </div>'''

new_image_block = '''          <div className="bg-white border rounded-lg overflow-hidden">
            {/* SCROLLABLE GALLERY */}
            <div className="p-4 bg-gray-50 border-b">
              <h3 className="text-sm font-semibold text-gray-600 mb-3">Property Gallery ({listing.media.filter(m => m.media_type === 'IMAGE').length} images)</h3>
              <div className="flex gap-4 overflow-x-auto snap-x pb-2">
                {listing.media.filter(m => m.media_type === 'IMAGE').map((m) => (
                  <img 
                    key={m.id}
                    src={getMediaUrl(m.file)} 
                    alt="Property" 
                    className="h-48 w-auto object-cover rounded-lg shadow-sm border snap-start flex-shrink-0" 
                  />
                ))}
                {listing.media.filter(m => m.media_type === 'IMAGE').length === 0 && (
                  <div className="h-48 w-full bg-gray-200 rounded-lg flex items-center justify-center text-gray-400">
                    No images uploaded
                  </div>
                )}
              </div>
            </div>'''

if old_image_block in text:
    text = text.replace(old_image_block, new_image_block)
    MANAGE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched ManageListingPage.tsx: Replaced single image with scrollable gallery")
else:
    print("⚠️ Could not find exact image block in ManageListingPage.tsx")

# ----------------------------------------------------------------
# 3. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add thumbnails to dashboard and scrollable gallery to manage page"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 DASHBOARD AND GALLERY UPDATES PUSHED!
==================================================

Wait about 2 minutes for Render to rebuild the frontend.

1. **Dashboard**: Your "My Listings" table will now have a small thumbnail of the property next to the title.
2. **Manage Page**: When you click "Manage", instead of one giant image, you will see a horizontal scrollable gallery of all the images you uploaded for that property.
""")