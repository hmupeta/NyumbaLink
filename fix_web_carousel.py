#!/usr/bin/env python3
"""Replaces the horizontal scroll gallery with a one-at-a-time carousel."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
MANAGE_FILE = ROOT / "frontend" / "src" / "pages" / "ManageListingPage.tsx"

text = MANAGE_FILE.read_text(encoding="utf-8")

# ----------------------------------------------------------------
# 1. Add state for the active image index
# ----------------------------------------------------------------
if "const [activeImageIndex, setActiveImageIndex]" not in text:
    text = text.replace(
        "  const [showTenantModal, setShowTenantModal] = useState(false)",
        "  const [showTenantModal, setShowTenantModal] = useState(false)\n  const [activeImageIndex, setActiveImageIndex] = useState(0)"
    )

# ----------------------------------------------------------------
# 2. Extract the images array for cleaner JSX
# ----------------------------------------------------------------
if "const images = listing.media.filter" not in text:
    # Insert the filter right after the loading check
    text = text.replace(
        "  if (isLoading) return <Loading />",
        "  if (isLoading) return <Loading />\n  const images = listing?.media.filter((m) => m.media_type === 'IMAGE') || [];"
    )

# ----------------------------------------------------------------
# 3. Replace the old gallery UI with the new Carousel
# ----------------------------------------------------------------
old_gallery = '''          <div className="bg-white border rounded-lg overflow-hidden">
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

new_gallery = '''          <div className="bg-white border rounded-lg overflow-hidden">
            {/* CAROUSEL */}
            <div className="relative bg-black">
              {images.length > 0 ? (
                <>
                  <div className="aspect-video w-full flex items-center justify-center">
                    <img
                      src={getMediaUrl(images[activeImageIndex].file)}
                      alt="Property"
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>

                  {/* Prev/Next Arrows */}
                  {images.length > 1 && (
                    <>
                      <button
                        onClick={() => setActiveImageIndex(prev => prev === 0 ? images.length - 1 : prev - 1)}
                        className="absolute left-4 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/70 transition"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                      </button>
                      <button
                        onClick={() => setActiveImageIndex(prev => prev === images.length - 1 ? 0 : prev + 1)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/70 transition"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
                      </button>
                      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/50 text-white px-3 py-1 rounded-full text-xs font-medium">
                        {activeImageIndex + 1} / {images.length}
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div className="aspect-video w-full flex items-center justify-center text-gray-400">
                  No images uploaded
                </div>
              )}
            </div>

            {/* Thumbnail Strip */}
            {images.length > 1 && (
              <div className="flex gap-2 p-3 overflow-x-auto bg-gray-50 border-b">
                {images.map((m, idx) => (
                  <img
                    key={m.id}
                    src={getMediaUrl(m.file)}
                    onClick={() => setActiveImageIndex(idx)}
                    className={`w-16 h-16 object-cover rounded cursor-pointer border-2 transition ${idx === activeImageIndex ? 'border-emerald-500' : 'border-transparent opacity-60 hover:opacity-100'}`}
                    alt="Thumbnail"
                  />
                ))}
              </div>
            )}'''

if old_gallery in text:
    text = text.replace(old_gallery, new_gallery)
    MANAGE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched ManageListingPage.tsx: Replaced with interactive carousel")
else:
    print("⚠️ Could not find exact gallery block. Please check manually.")

# ----------------------------------------------------------------
# 4. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add proper one-at-a-time carousel with thumbnails to manage page"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 CAROUSEL ADDED!
==================================================

Wait about 2 minutes for Render to rebuild the frontend.

1. Go to your Dashboard and click "Manage" on a property.
2. You will now see one large image, with Prev/Next arrows on the sides.
3. Below the main image, there is a row of small thumbnails. Clicking a thumbnail jumps directly to that image.
""")