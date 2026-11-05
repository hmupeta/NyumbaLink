import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listingsApi } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

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

      {images.length > 0 && (
        <div className="grid gap-2 mb-6" style={{ gridTemplateColumns: images.length > 1 ? '2fr 1fr' : '1fr' }}>
          {images.slice(0, 2).map((m) => (
            <img key={m.id} src={m.file} alt={m.caption || listing.title}
              className="w-full h-64 object-cover rounded" />
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
        <aside className="border rounded-lg p-4 h-fit bg-white">
          <p className="text-2xl font-bold text-emerald-700">
            {listing.currency} {Number(listing.price).toLocaleString()}
            {listing.price_period === 'MONTH' && (
              <span className="text-base text-gray-500">/mo</span>
            )}
          </p>
          <p className="text-sm text-gray-600 mt-1">
            {listing.transaction_type === 'RENT' ? 'For rent'
              : listing.transaction_type === 'SALE' ? 'For sale'
              : 'Short let'}
          </p>
          <button className="mt-4 w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700">
            Contact advertiser
          </button>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Advertised by {listing.created_by_email}
          </p>
        </aside>
      </div>
    </div>
  )
}
