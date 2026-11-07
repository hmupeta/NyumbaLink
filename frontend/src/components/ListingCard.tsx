import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import type { Listing } from '../api/types'

function formatPrice(price: string, currency: string, period: string) {
  const n = Number(price)
  const fmt = new Intl.NumberFormat('en-ZM', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n)
  if (period === 'MONTH') return `${fmt}/mo`
  if (period === 'YEAR') return `${fmt}/yr`
  return fmt
}

export default function ListingCard({ listing }: { listing: Listing & { is_saved?: boolean } }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const cover = listing.media.find((m) => m.media_type === 'IMAGE')

  const saveMutation = useMutation({
    mutationFn: () => listingsApi.toggleSave(listing.id, !!listing.is_saved),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['listings'] })
      queryClient.invalidateQueries({ queryKey: ['saved-listings'] })
    }
  })

  const handleSave = (e: React.MouseEvent) => {
    e.preventDefault()
    if (!user) {
      alert("Please log in to save properties.")
      return
    }
    saveMutation.mutate()
  }

  return (
    <Link to={`/listings/${listing.id}`} className="block bg-white border rounded-lg overflow-hidden hover:shadow-lg transition group relative">
      
      {/* Heart / Save Button */}
      <button 
        onClick={handleSave}
        className="absolute top-3 right-3 z-10 p-2 bg-white/80 backdrop-blur rounded-full shadow hover:bg-white transition"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill={listing.is_saved ? "#ef4444" : "none"} stroke={listing.is_saved ? "#ef4444" : "currentColor"} strokeWidth="2" className={listing.is_saved ? "text-red-500" : "text-gray-600"}>
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
        </svg>
      </button>

      <div className="aspect-video bg-gray-100">
        {cover && cover.file ? (
          <img 
            src={getMediaUrl(cover.file)} 
            alt={listing.title} 
            className="w-full h-full object-cover" 
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'https://placehold.co/600x400/e2e8f0/64748b?text=No+Image+Available';
            }}
          />
        ) : (
          <img src="https://placehold.co/600x400/e2e8f0/64748b?text=No+Image+Available" className="w-full h-full object-cover" />
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold truncate pr-6">{listing.title}</h3>
        <p className="text-sm text-gray-600 mt-1">{listing.property_summary.neighbourhood}</p>
        <p className="mt-2 font-bold text-emerald-700">{formatPrice(listing.price, listing.currency, listing.price_period)}</p>
        <p className="text-sm text-gray-500 mt-1">
          {listing.property_summary.property_type}
          {listing.property_summary.bedrooms ? ` · ${listing.property_summary.bedrooms} bed` : ''}
        </p>
      </div>
    </Link>
  )
}
