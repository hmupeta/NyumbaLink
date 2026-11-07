import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ManageListingPage() {
  const { id } = useParams<{ id: string }>()
  
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['manage-listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) return <Loading />
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
            <div className="aspect-video bg-gray-100 flex items-center justify-center">
              {listing.media[0] ? (
                <img src={getMediaUrl(listing.media[0].file)} alt="Cover" className="w-full h-full object-cover" />
              ) : (
                <span className="text-gray-400">No image uploaded</span>
              )}
            </div>
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
