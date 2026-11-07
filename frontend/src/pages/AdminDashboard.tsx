import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { adminApi } from '../api/admin'
import Loading from '../components/Loading'

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
  })

  if (isLoading) return <Loading />
  if (!data) return <p className="text-gray-500">Access denied or failed to load.</p>

  const { stats, alerts, recent_users, recent_listings } = data

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Overview</h1>
          <p className="text-gray-600">Monitor NyumbaLink's growth, revenue, and moderation health.</p>
        </div>
        <Link to="/moderation" className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 font-medium shadow-sm">
          Go to Moderation Console
        </Link>
      </div>

      {/* KEY METRICS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Users</p>
          <p className="text-3xl font-bold text-gray-900">{stats.total_users}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Active Listings</p>
          <p className="text-3xl font-bold text-emerald-600">{stats.active_listings}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Credits Sold</p>
          <p className="text-3xl font-bold text-gray-900">{stats.credits_sold}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Contacts Unlocked</p>
          <p className="text-3xl font-bold text-gray-900">{stats.total_unlocks}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* LEFT COLUMN: NEEDS ATTENTION */}
        <div>
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Needs Attention</h2>
          <div className="space-y-4">
            <Link to="/moderation?tab=listings" className="block bg-white border-l-4 border-yellow-500 p-4 rounded shadow-sm hover:shadow-md transition flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-800">Pending Listings</h3>
                <p className="text-sm text-gray-500">Listings waiting for approval</p>
              </div>
              <span className="bg-yellow-100 text-yellow-800 font-bold px-3 py-1 rounded-full">{alerts.pending_listings}</span>
            </Link>
            <Link to="/moderation?tab=kyc" className="block bg-white border-l-4 border-blue-500 p-4 rounded shadow-sm hover:shadow-md transition flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-800">Pending KYC</h3>
                <p className="text-sm text-gray-500">Landlords awaiting ID verification</p>
              </div>
              <span className="bg-blue-100 text-blue-800 font-bold px-3 py-1 rounded-full">{alerts.pending_kyc}</span>
            </Link>
            <Link to="/moderation?tab=reports" className="block bg-white border-l-4 border-red-500 p-4 rounded shadow-sm hover:shadow-md transition flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-800">Open Reports</h3>
                <p className="text-sm text-gray-500">Reported listings or users</p>
              </div>
              <span className="bg-red-100 text-red-800 font-bold px-3 py-1 rounded-full">{alerts.open_reports}</span>
            </Link>
          </div>
        </div>

        {/* RIGHT COLUMN: RECENT ACTIVITY */}
        <div>
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Recent Activity</h2>
          <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div className="p-4 bg-gray-50 border-b font-semibold text-sm text-gray-600">Newest Users</div>
            <ul className="divide-y">
              {recent_users.map((u: any, i: number) => (
                <li key={i} className="p-3 text-sm flex justify-between">
                  <span className="font-medium text-gray-800">{u.email}</span>
                  <span className="text-gray-400">{new Date(u.date_joined).toLocaleDateString()}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white border rounded-lg shadow-sm overflow-hidden mt-4">
            <div className="p-4 bg-gray-50 border-b font-semibold text-sm text-gray-600">Newest Listings</div>
            <ul className="divide-y">
              {recent_listings.map((l: any, i: number) => (
                <li key={i} className="p-3 text-sm flex justify-between">
                  <span className="font-medium text-gray-800 truncate max-w-[200px]">{l.title}</span>
                  <span className="text-emerald-600 font-bold">{l.currency} {Number(l.price).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
