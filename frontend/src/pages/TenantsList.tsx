import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { managementApi } from '../api/management'
import { api } from '../api/client'
import MomoPaymentModal from '../components/MomoPaymentModal'
import Loading from '../components/Loading'

export default function TenantsList() {
  const [expandedLease, setExpandedLease] = useState<string | null>(null)
  const [payingRecord, setPayingRecord] = useState<any>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [formData, setFormData] = useState({ tenant_email: '', property: '', start_date: '', end_date: '', monthly_rent: '', deposit: '' })
  const queryClient = useQueryClient()

  // Fetch Leases
  const { data: leasesData, isLoading: isLoadingLeases } = useQuery({
    queryKey: ['leases'],
    queryFn: managementApi.listLeases,
  })

  // Fetch Properties
  const { data: propertiesData } = useQuery({
    queryKey: ['properties'],
    queryFn: () => api<any>('/properties/'),
  })

  // Fetch Viewing Requests
  const { data: viewingsData } = useQuery({
    queryKey: ['viewings'],
    queryFn: () => api<any>('/viewings/'),
  })

  const createMutation = useMutation({
    mutationFn: () => managementApi.createLease(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leases'] })
      setShowCreateModal(false)
      setFormData({ tenant_email: '', property: '', start_date: '', end_date: '', monthly_rent: '', deposit: '' })
      alert("Lease issued successfully!")
    },
    onError: (err: any) => alert("Error: " + err.message)
  })

  // Handle API pagination (results or raw array)
  const propsList = propertiesData?.results || propertiesData || []
  const viewingsList = viewingsData?.results || viewingsData || []
  
  const availableProperties = propsList.filter((p: any) => {
    const status = (p.status || p.occupancy_status || '').toUpperCase();
    return status !== 'OCCUPIED';
  })

  // --- ROBUST FIELD EXTRACTION ---
  
  // Properties
  const getPropName = (p: any) => p.property_name || p.title || p.name || 'Unnamed Property'
  const getPropLoc = (p: any) => p.location || p.address || p.city || p.town || ''
  const getPropPrice = (p: any) => p.price || p.rent_amount || p.rent || p.monthly_rent || 0

  // Viewings - handle nested serializers (e.g., v.seeker.email)
  const getViewingPropertyId = (v: any) => {
    if (typeof v.property === 'object' && v.property !== null) return v.property.id;
    return v.property || v.property_id || v.listing_id || v.listing;
  }
  
  const getViewingEmail = (v: any) => {
    return v.tenant_email || v.seeker_email || v.email || 
           v.seeker?.email || v.tenant?.email || v.user?.email || '';
  }
  
  const getViewingName = (v: any) => {
    return v.tenant_name || v.seeker_name || 
           v.seeker?.full_name || v.seeker?.first_name || 
           v.tenant?.full_name || v.user?.full_name || 'Seeker';
  }

  // Filter viewing requests for the selected property
  const interestedViewings = viewingsList.filter((v: any) => 
    String(getViewingPropertyId(v)) === String(formData.property)
  )
  
  // Extract unique tenants from the viewings
  const uniqueTenants = Array.from(new Set(interestedViewings.map(getViewingEmail)))
    .filter(Boolean)
    .map(email => {
       const v = interestedViewings.find((v: any) => getViewingEmail(v) === email);
       return { email, name: getViewingName(v) };
    });

  // Auto-fill rent when property is selected
  const handlePropertyChange = (propId: string) => {
    const selectedProp = availableProperties.find((p: any) => String(p.id) === String(propId));
    const price = selectedProp ? getPropPrice(selectedProp) : '';
    setFormData({ ...formData, property: propId, monthly_rent: price ? String(price) : formData.monthly_rent });
  }

  if (isLoadingLeases) return <Loading />

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Your Tenants</h2>
        <button onClick={() => setShowCreateModal(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-medium shadow-sm transition">
          + Issue New Lease
        </button>
      </div>

      {leasesData?.results.length === 0 && (
        <div className="text-center py-12 bg-white rounded border">
          <p className="text-gray-500">You don't have any active tenants yet.</p>
        </div>
      )}

      {leasesData?.results.map((lease: any) => {
        const pendingRent = (lease.rent_records || []).filter((r: any) => r.status === 'PENDING')
        const isExpanded = expandedLease === lease.id

        return (
          <div key={lease.id} className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div
              className="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50 transition"
              onClick={() => setExpandedLease(isExpanded ? null : lease.id)}
            >
              <div>
                <div className="flex items-center gap-4">
                  <h3 className="font-bold text-lg text-gray-900">{lease.tenant_name || lease.tenant_email}</h3>
                  <a href={`/leases/${lease.id}`} className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded hover:bg-emerald-200 transition" onClick={(e) => e.stopPropagation()}>
                    Manage Lease / Sign
                  </a>
                </div>
                <p className="text-sm text-gray-600">{lease.property_name} · {lease.tenant_phone}</p>
                <p className="text-xs text-gray-500 mt-1">Lease ends: {new Date(lease.end_date).toLocaleDateString()}</p>
              </div>
              <div className="text-right">
                <p className="font-bold text-emerald-700">K {Number(lease.monthly_rent || 0).toLocaleString()}/mo</p>
                <span className={`inline-block mt-1 px-2 py-1 rounded text-xs font-bold ${
                  pendingRent.length > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}>
                  {pendingRent.length > 0 ? `${pendingRent.length} Pending` : 'Rent Up to Date'}
                </span>
              </div>
            </div>

            {isExpanded && (
              <div className="border-t bg-gray-50 p-4">
                <h4 className="font-semibold text-sm text-gray-700 mb-3">Rent Schedule</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {(lease.rent_records || []).map((record: any) => (
                    <div key={record.id} className={`p-3 rounded border ${record.status === 'PAID' ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                      <p className="text-xs text-gray-500 font-medium">{new Date(record.due_date).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</p>
                      <p className="font-bold text-sm mt-1">K {Number(record.amount).toLocaleString()}</p>
                      {record.status === 'PAID' ? (
                        <p className="text-xs text-green-600 font-bold mt-1">Paid</p>
                      ) : (
                        <button onClick={() => setPayingRecord({ ...record, rent_record_id: record.id })} className="mt-2 text-xs bg-emerald-600 text-white px-2 py-1 rounded">
                          Pay Now
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      })}

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-4">Issue New Lease</h2>
            <div className="space-y-3">
              
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Property</label>
                <select 
                  className="w-full border rounded px-3 py-2 bg-white" 
                  value={formData.property} 
                  onChange={e => handlePropertyChange(e.target.value)}
                >
                  <option value="">Select a property...</option>
                  {availableProperties.map((p: any) => {
                    const loc = getPropLoc(p);
                    const name = getPropName(p);
                    return (
                      <option key={p.id} value={p.id}>
                        {name} {loc ? `(${loc})` : ''} - K{Number(getPropPrice(p)).toLocaleString()}/mo
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Tenant Email</label>
                <input 
                  type="email"
                  list="tenant-options"
                  placeholder="Type email or select from viewers..."
                  className="w-full border rounded px-3 py-2 bg-white"
                  value={formData.tenant_email} 
                  onChange={e => setFormData({...formData, tenant_email: e.target.value})}
                />
                <datalist id="tenant-options">
                  {uniqueTenants.map((t: any) => (
                    <option key={t.email} value={t.email}>{t.name} ({t.email})</option>
                  ))}
                </datalist>
                {formData.property && uniqueTenants.length === 0 && (
                  <p className="text-xs text-orange-500 mt-1">No viewing requests found for this property. You can type an email manually.</p>
                )}
              </div>

              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Start Date</label>
                  <input type="date" className="w-full border rounded px-3 py-2" value={formData.start_date} onChange={e => setFormData({...formData, start_date: e.target.value})} />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-700 mb-1">End Date</label>
                  <input type="date" className="w-full border rounded px-3 py-2" value={formData.end_date} onChange={e => setFormData({...formData, end_date: e.target.value})} />
                </div>
              </div>

              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Monthly Rent</label>
                  <input placeholder="ZMW" type="number" className="w-full border rounded px-3 py-2" value={formData.monthly_rent} onChange={e => setFormData({...formData, monthly_rent: e.target.value})} />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Deposit</label>
                  <input placeholder="ZMW" type="number" className="w-full border rounded px-3 py-2" value={formData.deposit} onChange={e => setFormData({...formData, deposit: e.target.value})} />
                </div>
              </div>

            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={() => setShowCreateModal(false)} className="flex-1 bg-gray-100 py-2 rounded">Cancel</button>
              <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !formData.property || !formData.tenant_email} className="flex-1 bg-emerald-600 text-white py-2 rounded font-medium disabled:opacity-50">
                {createMutation.isPending ? 'Creating...' : 'Issue Lease'}
              </button>
            </div>
          </div>
        </div>
      )}

      {payingRecord && (
        <MomoPaymentModal
          rentRecordId={payingRecord.id}
          amount={Number(payingRecord.amount)}
          onSuccess={() => {
            setPayingRecord(null);
            window.location.reload();
          }}
          onClose={() => setPayingRecord(null)}
        />
      )}
    </div>
  )
}
