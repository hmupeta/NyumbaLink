import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { messagingApi } from '../api/messaging'
import Loading from '../components/Loading'

export default function ViewingsList() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['viewings'],
    queryFn: () => messagingApi.listViewings(),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => messagingApi.updateViewingStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['viewings'] })
  })

  if (isLoading) return <Loading />

  return (
    <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
      <table className="w-full text-left">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 font-semibold text-sm">Property</th>
            <th className="px-4 py-3 font-semibold text-sm">Seeker</th>
            <th className="px-4 py-3 font-semibold text-sm">Requested Date</th>
            <th className="px-4 py-3 font-semibold text-sm">Status</th>
            <th className="px-4 py-3 font-semibold text-sm text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data?.results.map((v: any) => (
            <tr key={v.id}>
              <td className="px-4 py-3 text-sm">{v.listing_title}</td>
              <td className="px-4 py-3 text-sm">{v.seeker_email}</td>
              <td className="px-4 py-3 text-sm">{new Date(v.requested_date).toLocaleString()}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  v.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                  v.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>{v.status}</span>
              </td>
              <td className="px-4 py-3 text-right space-x-3">
                {v.status === 'PENDING' ? (
                  <>
                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'APPROVED' })} className="text-emerald-600 text-sm font-medium hover:underline">Approve</button>
                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'REJECTED' })} className="text-red-600 text-sm font-medium hover:underline">Reject</button>
                  </>
                ) : (
                  <span className="text-gray-400 text-sm italic">Action taken</span>
                )}
              </td>
            </tr>
          ))}
          {data?.results.length === 0 && (
            <tr><td colSpan={5} className="p-8 text-center text-gray-500">No viewing requests yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
