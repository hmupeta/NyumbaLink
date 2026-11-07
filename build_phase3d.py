#!/usr/bin/env python3
"""NyumbaLink Phase 3d: Image Lightbox (Hero Gallery) for public listings."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- Lightbox Component
LIGHTBOX_COMPONENT = '''import { useEffect } from 'react'
import { getMediaUrl } from '../api/listings'
import type { ListingMedia } from '../api/types'

interface Props {
  images: ListingMedia[]
  initialIndex: number
  onClose: () => void
}

export default function ImageLightbox({ images, initialIndex, onClose }: Props) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex)

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') setCurrentIndex((prev) => (prev + 1) % images.length)
      if (e.key === 'ArrowLeft') setCurrentIndex((prev) => (prev - 1 + images.length) % images.length)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [images.length, onClose])

  if (images.length === 0) return null

  const currentImage = images[currentIndex]

  const goNext = () => setCurrentIndex((prev) => (prev + 1) % images.length)
  const goPrev = () => setCurrentIndex((prev) => (prev - 1 + images.length) % images.length)

  return (
    <div className="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center">
      {/* Close Button */}
      <button 
        onClick={onClose}
        className="absolute top-4 right-4 text-white hover:text-gray-300 p-2"
        aria-label="Close"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>

      {/* Main Image Container */}
      <div className="relative w-full max-w-7xl h-full max-h-[85vh] flex items-center justify-center px-4">
        <img
          src={getMediaUrl(currentImage.file)}
          alt={currentImage.caption || 'Property image'}
          className="max-w-full max-h-full object-contain"
        />

        {/* Navigation Arrows (only show if more than 1 image) */}
        {images.length > 1 && (
          <>
            <button 
              onClick={goPrev}
              className="absolute left-4 md:left-8 text-white hover:text-gray-300 bg-black/50 p-3 rounded-full hover:bg-black/70 transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>
            <button 
              onClick={goNext}
              className="absolute right-4 md:right-8 text-white hover:text-gray-300 bg-black/50 p-3 rounded-full hover:bg-black/70 transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
          </>
        )}
      </div>

      {/* Thumbnails / Counter */}
      <div className="absolute bottom-6 w-full flex justify-center items-center gap-4">
        <span className="text-white text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
          {currentIndex + 1} / {images.length}
        </span>
      </div>
    </div>
  )
}
'''

# ---------------------------------------------------------------- Updated Detail Page
DETAIL_PAGE = '''import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ImageLightbox from '../components/ImageLightbox'

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  if (isLoading) return <Loading />
  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <ErrorMessage message="Listing not found or no longer available." />
      </div>
    )
  }
  if (!listing) return null

  const images = listing.media.filter((m) => m.media_type === 'IMAGE')

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/" className="text-sm text-emerald-700 hover:underline">
        ← Back to listings
      </Link>

      <h1 className="text-3xl font-bold mt-4 mb-2">{listing.title}</h1>
      <p className="text-gray-600 mb-6">
        {listing.property_summary.neighbourhood} · {listing.property_summary.property_type}
        {listing.property_summary.bedrooms ? ` · ${listing.property_summary.bedrooms} bedrooms` : ''}
      </p>

      {/* Image Grid */}
      {images.length > 0 && (
        <div className="mb-6 grid gap-2" style={{ gridTemplateColumns: images.length > 1 ? '2fr 1fr' : '1fr' }}>
          {images.slice(0, 2).map((m, idx) => (
            <div 
              key={m.id} 
              className="relative cursor-pointer group overflow-hidden rounded-lg bg-gray-100"
              onClick={() => setLightboxIndex(idx)}
            >
              <img 
                src={getMediaUrl(m.file)} 
                alt={m.caption || listing.title}
                className="w-full h-64 md:h-80 object-cover transition duration-300 group-hover:scale-105 group-hover:opacity-90" 
              />
              {/* Hover overlay */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-0 group-hover:opacity-100 transition drop-shadow-lg scale-75 group-hover:scale-100"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="font-semibold text-lg mb-2">Description</h2>
          <p className="whitespace-pre-line text-gray-700">
            {listing.description || 'No description provided.'}
          </p>
        </div>
        <aside className="border rounded-lg p-4 h-fit bg-white shadow-sm">
          <p className="text-2xl font-bold text-emerald-700">
            {listing.currency} {Number(listing.price).toLocaleString()}
            {listing.price_period === 'MONTH' && (
              <span className="text-base text-gray-500">/mo</span>
            )}
          </p>
          <p className="text-sm text-gray-600 mt-1 mb-4">
            {listing.transaction_type === 'RENT' ? 'For rent'
              : listing.transaction_type === 'SALE' ? 'For sale'
              : 'Short let'}
          </p>
          <button className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium">
            Contact advertiser
          </button>
          <p className="text-xs text-gray-500 mt-4 text-center">
            Advertised by {listing.created_by_email}
          </p>
        </aside>
      </div>

      {/* Lightbox Render */}
      {lightboxIndex !== null && (
        <ImageLightbox 
          images={images} 
          initialIndex={lightboxIndex} 
          onClose={() => setLightboxIndex(null)} 
        />
      )}
    </div>
  )
}
'''

FRONTEND_FILES = {
    "src/components/ImageLightbox.tsx": LIGHTBOX_COMPONENT,
    "src/pages/ListingDetailPage.tsx": DETAIL_PAGE,
}

def run():
    print(f"NyumbaLink Phase 3d (Lightbox Gallery) -> {ROOT}\n")
    
    print("Writing frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("""
Next steps:

  1. The Vite dev server will automatically hot-reload.

  2. Open a listing in the browser.
  3. Click on the main image. It will expand into a full-screen hero.
  4. If you uploaded multiple images, use the Left/Right arrows (or your keyboard) to scroll through them.
  5. Press Escape or click the 'X' to close.
""")

if __name__ == "__main__":
    run()