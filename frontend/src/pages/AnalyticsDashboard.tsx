import { useQuery } from '@tanstack/react-query'
import { listingsApi } from '../api/listings'
import Loading from '../components/Loading'

export default function AnalyticsDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: listingsApi.getAnalytics,
  })

  if (isLoading) return <Loading />
  if (!data) return <p className="text-gray-500">Could not load analytics.</p>

  const { totals, chart_data } = data
  const maxViews = Math.max(...chart_data.map((d: any) => d.views), 1)

  return (
    <div className="space-y-8">
      
      {/* Top Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Views</p>
          <p className="text-3xl font-bold text-gray-900">{totals.views}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Saves</p>
          <p className="text-3xl font-bold text-gray-900">{totals.saves}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Contacts Unlocked</p>
          <p className="text-3xl font-bold text-gray-900">{totals.unlocks}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm text-center">
          <p className="text-sm font-medium text-gray-500 mb-1">Inquiries Received</p>
          <p className="text-3xl font-bold text-gray-900">{totals.conversations}</p>
        </div>
      </div>

      {/* Bar Chart */}
      <div className="bg-white border rounded-lg p-6 shadow-sm">
        <h3 className="font-bold text-lg mb-6">Views per Listing</h3>
        <div className="space-y-4">
          {chart_data.map((item: any) => (
            <div key={item.id}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium truncate max-w-xs">{item.title}</span>
                <span className="font-bold">{item.views} views</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div 
                  className="bg-emerald-500 h-3 rounded-full" 
                  style={{ width: `${(item.views / maxViews) * 100}%` }}
                ></div>
              </div>
            </div>
          ))}
          {chart_data.length === 0 && <p className="text-gray-500 text-sm">No listing data yet.</p>}
        </div>
      </div>

    </div>
  )
}
