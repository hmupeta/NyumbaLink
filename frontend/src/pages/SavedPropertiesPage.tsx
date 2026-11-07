import { useQuery } from '@tanstack/react-query'
import { listingsApi } from '../api/listings'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'

export default function SavedPropertiesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['saved-listings'],
    queryFn: () => listingsApi.listSaved(),
  })

  if (isLoading) return <Loading />

  const listings = data?.results.map((r: any) => r.listing) || []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Saved Properties</h1>
      {listings.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-white rounded border">
          You haven't saved any properties yet. Click the heart icon on a listing to save it.
        </div>
      ) : (
        <ListingGrid listings={listings} />
      )}
    </div>
  )
}
