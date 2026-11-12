import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { managementApi } from '../api/management'
import MomoPaymentModal from '../components/MomoPaymentModal'
import Loading from '../components/Loading'

export default function TenantsList() {
const [expandedLease, setExpandedLease] = useState<string | null>(null)
  const [payingRecord, setPayingRecord] = useState<any>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['leases'],
    queryFn: managementApi.listLeases,
  })


  if (isLoading) return <Loading />

  return (<>
    <div className="space-y-4">
      {data?.results.length === 0 && (
        <div className="text-center py-12 bg-white rounded border">
          <p className="text-gray-500">You don't have any active tenants yet.</p>
        </div>
      )}
      
      {data?.results.map((lease: any) => {
        const pendingRent = lease.rent_records.filter((r: any) => r.status === 'PENDING')
        const isExpanded = expandedLease === lease.id

        return (
          <div key={lease.id} className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div 
              className="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50 transition"
              onClick={() => setExpandedLease(isExpanded ? null : lease.id)}
            >
              <div>
                <div className="flex items-center gap-4">
                        <h3 className="font-bold text-lg text-gray-900">{lease.tenant_name}</h3>
                        <a href={`/leases/${lease.id}`} className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded hover:bg-emerald-200 transition">
                          Manage Lease / Sign
                        </a>
                      </div>
                <p className="text-sm text-gray-600">{lease.property_name} Â· {lease.tenant_phone}</p>
                <p className="text-xs text-gray-500 mt-1">Lease ends: {new Date(lease.end_date).toLocaleDateString()}</p>
              </div>
              <div className="text-right">
                <p className="font-bold text-emerald-700">K {Number(lease.monthly_rent).toLocaleString()}/mo</p>
                <span className={`inline-block mt-1 px-2 py-1 rounded text-xs font-bold ${
                  pendingRent.length > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}>
                  {pendingRent.length > 0 ? `${pendingRent.length} Rent Unpaid` : 'Rent Up to Date'}
                </span>
              </div>
            </div>

            {/* Expanded Rent History */}
            {isExpanded && (
              <div className="border-t bg-gray-50 p-4">
                <h4 className="font-semibold text-sm text-gray-700 mb-3">Rent Schedule (Next 12 Months)</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {lease.rent_records.map((record: any) => (
                    <div key={record.id} className={`p-3 rounded border ${record.status === 'PAID' ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                      <p className="text-xs text-gray-500 font-medium">{new Date(record.due_date).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</p>
                      <p className="font-bold text-sm mt-1">K {Number(record.amount).toLocaleString()}</p>
                      
                      {record.status === 'PAID' ? (
                        <div className="mt-2 flex flex-col gap-1">
                          <p className="text-xs text-green-700 font-medium flex items-center gap-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Paid
                          </p>
                          <a
                            href={`https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${lease.id}/rent-records/${record.id}/download_invoice/`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-blue-600 hover:underline"
                          >
                            Download Receipt
                          </a>
                        </div>
                      ) : (
                        <button 
                          onClick={() => setPayingRecord(record)}
                          className="mt-2 text-xs bg-emerald-600 text-white px-2 py-1 rounded hover:bg-emerald-700 w-full"
                        >
                          Pay Rent via MTN
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
    </div>
    
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
  </>
  )
}
