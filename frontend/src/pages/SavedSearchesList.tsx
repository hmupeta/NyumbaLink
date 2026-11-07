import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { searchApi } from '../api/search'
import Loading from '../components/Loading'

export default function SavedSearchesList() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['saved-searches'],
    queryFn: searchApi.list,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => searchApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['saved-searches'] })
  })

  if (isLoading) return <Loading />

  return (
    <div className="space-y-4">
      {data?.results.length === 0 && (
        <div className="text-center py-12 bg-white rounded border">
          <p className="text-gray-500">You haven't saved any searches yet.</p>
          <Link to="/" className="text-emerald-600 hover:underline mt-2 block">Go to home page to search</Link>
        </div>
      )}
      {data?.results.map((search: any) => (
        <div key={search.id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
          <div>
            <h3 className="font-bold text-lg text-gray-900">{search.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {search.transaction_type || 'Any type'} 
              {search.property_type ? ` · ${search.property_type}` : ''}
              {search.max_price ? ` · Under ${search.max_price}` : ''}
              {search.district ? ` · ${search.district}` : ''}
            </p>
          </div>
          <div className="flex gap-4">
            <Link 
              to={`/?search=${search.query}&type=${search.transaction_type?.toLowerCase()}`}
              className="text-emerald-600 hover:underline font-medium text-sm"
            >
              View Results
            </Link>
            <button 
              onClick={() => deleteMutation.mutate(search.id)}
              className="text-red-500 hover:text-red-700 text-sm font-medium"
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
