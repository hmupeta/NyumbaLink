import ListingCard from './ListingCard'
import type { Listing } from '../api/types'

export default function ListingGrid({ listings }: { listings: Listing[] }) {
  if (listings.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 bg-white rounded border">
        No listings found. Try adjusting your search.
      </div>
    )
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {listings.map((l) => <ListingCard key={l.id} listing={l} />)}
    </div>
  )
}
