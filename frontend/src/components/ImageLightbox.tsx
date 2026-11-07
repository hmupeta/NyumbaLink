import { useEffect, useState } from 'react'
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
