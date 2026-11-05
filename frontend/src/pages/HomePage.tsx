import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, type ListingFilters } from '../api/listings'
import SearchBar from '../components/SearchBar'
import ListingGrid from '../components/ListingGrid'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function HomePage() {
  const [filters, setFilters] = useState<ListingFilters>({})

  const { data, isLoading, error } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => listingsApi.list(filters),
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Find your place in Zambia</h1>
        <p className="text-gray-600 mb-6">
          Browse verified listings in Lusaka and beyond.
        </p>
        <SearchBar
          initialValue={filters.search}
          onSearch={(v) => setFilters((f) => ({ ...f, search: v || undefined }))}
        />
      </div>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Could not load listings. Is the backend running?" />}
      {data && (
        <>
          <p className="text-sm text-gray-600 mb-4">
            {data.count} listing{data.count === 1 ? '' : 's'}
          </p>
          <ListingGrid listings={data.results} />
        </>
      )}
    </div>
  )
}
