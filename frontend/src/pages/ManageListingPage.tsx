import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ManageListingPage() {
  const { id } = useParams<{ id: string }>()
  const [activeImageIndex, setActiveImageIndex] = useState(0)
  
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['manage-listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) return <Loading />
  const images = listing?.media.filter((m) => m.media_type === 'IMAGE') || [];
  if (error || !listing) return <div className="p-8"><ErrorMessage message="Listing not found." /></div>

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Link to="/dashboard" className="text-sm text-emerald-700 hover:underline">
          ← Back to Dashboard
        </Link>
        <Link to={`/dashboard/listings/${listing.id}/edit`} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900 text-sm">
          Edit Listing
        </Link>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white border rounded-lg overflow-hidden">
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
            )}
            <div className="p-6">
              <div className="flex justify-between items-start mb-2">
                <h1 className="text-2xl font-bold">{listing.title}</h1>
                <span className={`px-3 py-1 rounded text-xs font-bold ${
                  listing.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {listing.status}
                </span>
              </div>
              <p className="text-gray-600 mb-4">{listing.property_summary.neighbourhood} · {listing.property_summary.property_type}</p>
              
              <h2 className="font-semibold border-b pb-2 mb-2 mt-6">Description</h2>
              <p className="whitespace-pre-line text-gray-700">{listing.description || 'No description provided.'}</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white border rounded-lg p-6">
            <h3 className="font-bold text-lg mb-4">Rental Tracking</h3>
            <p className="text-sm text-gray-500 mb-4">Manage tenants and rent collection for this property.</p>
            
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Current Tenant</span>
                <span className="font-medium text-gray-400">None assigned</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Lease Start</span>
                <span className="font-medium text-gray-400">-</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Rent Due</span>
                <span className="font-medium text-gray-400">-</span>
              </div>
            </div>
            <button disabled className="mt-6 w-full bg-gray-100 text-gray-500 py-2 rounded cursor-not-allowed text-sm">
              Add Tenant (Coming in Phase 5)
            </button>
          </div>

          <div className="bg-white border rounded-lg p-6">
            <h3 className="font-bold text-lg mb-2">Financials</h3>
            <p className="text-3xl font-bold text-emerald-700">
              {listing.currency} {Number(listing.price).toLocaleString()}
              <span className="text-sm font-normal text-gray-500">/mo</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
