import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { locationsApi } from '../api/locations'

export default function TopNeighbourhoods() {
  const { data: hoods, isLoading } = useQuery({
    queryKey: ['top-neighbourhoods'],
    queryFn: locationsApi.getTopNeighbourhoods,
  })

  if (isLoading || !hoods || hoods.length === 0) return null

  return (
    <div className="bg-[#F8F9FA] py-12 border-b">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Explore popular areas</h2>
          <p className="text-gray-600">Discover properties in the most active neighbourhoods.</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {hoods.map((hood: any) => (
            <Link
              key={hood.id}
              to={`/?neighbourhood=${hood.slug}`}
              className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group flex flex-col items-center justify-center text-center"
            >
              <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mb-4 group-hover:bg-emerald-100 transition">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
              </div>
              <h3 className="font-bold text-gray-900 text-lg">{hood.name}</h3>
              <p className="text-xs text-gray-500 mt-1">{hood.locality_name}</p>
              <p className="text-sm font-medium text-emerald-600 mt-2 bg-emerald-50 px-2 py-1 rounded-full">
                {hood.listing_count} {hood.listing_count === 1 ? 'listing' : 'listings'}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
