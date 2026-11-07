import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { listingsApi } from '../api/listings'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ViewingsList from './ViewingsList'
import SavedSearchesList from './SavedSearchesList'
import TenantsList from './TenantsList'
import MaintenanceList from './MaintenanceList'
import AnalyticsDashboard from './AnalyticsDashboard'

export default function DashboardPage() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') || 'listings'
  const queryClient = useQueryClient()

  const submitMutation = useMutation({
    mutationFn: (id: string) => listingsApi.submitForReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-listings'] })
      alert('Listing submitted for review!')
    }
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['my-listings'],
    queryFn: () => listingsApi.getMyListings(),
  })

  const myListings = data?.results || []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold">Landlord Dashboard</h1>
          <p className="text-gray-600">Manage your properties and listing requests.</p>
        </div>
        <div className="flex gap-3">
          <Link
            to={`/profiles/${user?.id}`}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 font-medium text-sm transition"
          >
            View Public Profile
          </Link>
          <Link
            to="/dashboard/listings/new"
            className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium text-sm transition shadow-sm"
          >
            + Create Listing
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b mb-6">
        <button 
          onClick={() => setSearchParams({ tab: 'listings' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'listings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          My Listings
        </button>
        <button 
          onClick={() => setSearchParams({ tab: 'viewings' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'viewings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Viewing Requests
        </button>
        <button 
          onClick={() => setSearchParams({ tab: 'analytics' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'analytics' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Analytics
        </button>
        <button 
          onClick={() => setSearchParams({ tab: 'searches' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'searches' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Saved Searches
        </button>
        <button 
          onClick={() => setSearchParams({ tab: 'tenants' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'tenants' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Tenants
        </button>
        <button 
          onClick={() => setSearchParams({ tab: 'maintenance' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'maintenance' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Maintenance
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'listings' ? (
        <>
          {isLoading && <Loading />}
          {error && <ErrorMessage message="Could not load your listings." />}
          
          {data && myListings.length === 0 && (
            <div className="text-center py-12 bg-white rounded border shadow-sm">
              <p className="text-gray-500 mb-4">You haven't created any listings yet.</p>
              <Link to="/dashboard/listings/new" className="text-emerald-600 hover:underline">
                Create your first listing
              </Link>
            </div>
          )}

          {myListings.length > 0 && (
            <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 font-semibold text-sm">Title</th>
                    <th className="px-4 py-3 font-semibold text-sm">Price</th>
                    <th className="px-4 py-3 font-semibold text-sm">Status</th>
                    <th className="px-4 py-3 font-semibold text-sm text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {myListings.map(l => (
                    <tr key={l.id}>
                      <td className="px-4 py-3 text-sm">{l.title}</td>
                      <td className="px-4 py-3 text-sm">{l.currency} {Number(l.price).toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          l.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' :
                          l.status === 'SUBMITTED' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {l.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-3">
                        {l.status === 'DRAFT' && (
                          <button 
                            onClick={() => submitMutation.mutate(l.id)}
                            disabled={submitMutation.isPending}
                            className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded text-xs font-bold hover:bg-emerald-200 transition"
                          >
                            Submit for Review
                          </button>
                        )}
                        <Link to={`/dashboard/listings/${l.id}`} className="text-gray-600 hover:underline text-sm font-medium">Manage</Link>
                        <Link to={`/dashboard/listings/${l.id}/edit`} className="text-emerald-600 hover:underline text-sm font-medium">Edit</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : activeTab === 'viewings' ? (
        <ViewingsList />
      ) : activeTab === 'analytics' ? (
        <AnalyticsDashboard />
      ) : activeTab === 'searches' ? (
        <SavedSearchesList />
      ) : activeTab === 'tenants' ? (
        <TenantsList />
      ) : (
        <MaintenanceList />
      )}
    </div>
  )
}
