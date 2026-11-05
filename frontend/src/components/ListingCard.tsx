import { Link } from 'react-router-dom'
import type { Listing } from '../api/types'

function formatPrice(price: string, currency: string, period: string) {
  const n = Number(price)
  const fmt = new Intl.NumberFormat('en-ZM', {
    style: 'currency', currency, maximumFractionDigits: 0,
  }).format(n)
  if (period === 'MONTH') return `${fmt}/mo`
  if (period === 'YEAR') return `${fmt}/yr`
  return fmt
}

export default function ListingCard({ listing }: { listing: Listing }) {
  const cover = listing.media.find((m) => m.media_type === 'IMAGE')

  return (
    <Link
      to={`/listings/${listing.id}`}
      className="block bg-white border rounded-lg overflow-hidden hover:shadow-lg transition"
    >
      <div className="aspect-video bg-gray-100">
        {cover ? (
          <img src={cover.file} alt={listing.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
            No photo
          </div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold truncate">{listing.title}</h3>
        <p className="text-sm text-gray-600 mt-1">{listing.property_summary.neighbourhood}</p>
        <p className="mt-2 font-bold text-emerald-700">
          {formatPrice(listing.price, listing.currency, listing.price_period)}
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {listing.property_summary.property_type}
          {listing.property_summary.bedrooms ? ` · ${listing.property_summary.bedrooms} bed` : ''}
        </p>
      </div>
    </Link>
  )
}
