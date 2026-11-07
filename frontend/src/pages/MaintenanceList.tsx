import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { maintenanceApi } from '../api/maintenance'
import { api } from '../api/client'
import Loading from '../components/Loading'

export default function MaintenanceList() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({ title: '', description: '', priority: 'MEDIUM', property: '', lease: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['maintenance'],
    queryFn: maintenanceApi.list,
  })

  // Assuming we have properties and leases for the dropdowns
  const { data: properties } = useQuery({ queryKey: ['properties-list'], queryFn: () => api('/properties/') })
  const { data: leases } = useQuery({ queryKey: ['leases-list'], queryFn: () => api('/leases/') })

  const createMutation = useMutation({
    mutationFn: () => maintenanceApi.create({ 
      ...formData, 
      lease: formData.lease || null 
    }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['maintenance'] }); setShowModal(false); setFormData({ title: '', description: '', priority: 'MEDIUM', property: '', lease: '' }) }
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => maintenanceApi.updateStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['maintenance'] })
  })

  if (isLoading) return <Loading />

  const columns = [
    { key: 'OPEN', label: 'Open Issues', color: 'border-red-500' },
    { key: 'IN_PROGRESS', label: 'In Progress', color: 'border-yellow-500' },
    { key: 'RESOLVED', label: 'Resolved', color: 'border-emerald-500' }
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Maintenance Board</h2>
        <button onClick={() => setShowModal(true)} className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium shadow-sm">
          + Log Issue
        </button>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {columns.map(col => (
          <div key={col.key} className={`bg-gray-50 rounded-lg p-4 border-t-4 ${col.color} shadow-inner`}>
            <h3 className="font-bold text-gray-700 mb-4">{col.label} ({data?.results.filter((r: any) => r.status === col.key).length})</h3>
            <div className="space-y-3">
              {data?.results.filter((r: any) => r.status === col.key).map((req: any) => (
                <div key={req.id} className="bg-white p-4 rounded shadow-sm border">
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      req.priority === 'HIGH' ? 'bg-red-100 text-red-800' : req.priority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                    }`}>{req.priority}</span>
                  </div>
                  <h4 className="font-bold text-gray-900">{req.title}</h4>
                  <p className="text-xs text-gray-500 mb-2">{req.property_name} {req.tenant_name ? `· ${req.tenant_name}` : ''}</p>
                  <p className="text-sm text-gray-700 line-clamp-3 mb-3">{req.description}</p>
                  
                  <div className="flex gap-2 border-t pt-3">
                    {req.status === 'OPEN' && (
                      <button onClick={() => updateMutation.mutate({ id: req.id, status: 'IN_PROGRESS' })} className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded hover:bg-yellow-200 w-full font-medium">Start Work</button>
                    )}
                    {req.status === 'IN_PROGRESS' && (
                      <button onClick={() => updateMutation.mutate({ id: req.id, status: 'RESOLVED' })} className="text-xs bg-emerald-100 text-emerald-800 px-2 py-1 rounded hover:bg-emerald-200 w-full font-medium">Mark Resolved</button>
                    )}
                    {req.status === 'RESOLVED' && (
                      <p className="text-xs text-emerald-600 font-medium w-full text-center">✓ Completed {new Date(req.resolved_at).toLocaleDateString()}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Log Maintenance Issue</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="p-6 space-y-3">
              <input required placeholder="Issue Title (e.g. Leaking Roof)" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <textarea required placeholder="Describe the problem..." rows={3} value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <select required value={formData.priority} onChange={e => setFormData({...formData, priority: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="LOW">Low Priority</option>
                <option value="MEDIUM">Medium Priority</option>
                <option value="HIGH">High / Urgent</option>
              </select>
              <select required value={formData.property} onChange={e => setFormData({...formData, property: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">Select Property...</option>
                {properties?.results.map((p: any) => <option key={p.id} value={p.id}>{p.neighbourhood_name} ({p.property_type})</option>)}
              </select>
              <select value={formData.lease} onChange={e => setFormData({...formData, lease: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">No Specific Tenant</option>
                {leases?.results.map((l: any) => <option key={l.id} value={l.id}>{l.tenant_name}</option>)}
              </select>
              
              <button type="submit" disabled={createMutation.isPending} className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50 mt-2 font-medium">
                {createMutation.isPending ? 'Saving...' : 'Log Issue'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
