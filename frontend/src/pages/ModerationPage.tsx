import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { moderationApi } from '../api/moderation'
import { getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'

export default function ModerationPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'listings' | 'kyc' | 'reports' | 'history'>('listings')
  
  // Rejection state
  const [rejectReason, setRejectReason] = useState('')
  const [rejectingId, setRejectingId] = useState<string | null>(null)

  // --- Queries ---
  const { data: pendingListings, isLoading: loadingListings } = useQuery({
    queryKey: ['pending-listings'],
    queryFn: moderationApi.getPendingListings,
  })

  const { data: pendingKYC, isLoading: loadingKYC } = useQuery({
    queryKey: ['pending-kyc'],
    queryFn: moderationApi.getPendingKYC,
    enabled: activeTab === 'kyc',
  })

  const { data: history, isLoading: loadingHistory } = useQuery({
    queryKey: ['kyc-history'],
    queryFn: moderationApi.getKycHistory,
    enabled: activeTab === 'history',
  })

  const { data: reports, isLoading: loadingReports } = useQuery({
    queryKey: ['open-reports'],
    queryFn: moderationApi.getReports,
    enabled: activeTab === 'reports',
  })

  // --- Mutations ---
  const approveListing = useMutation({
    mutationFn: (id: string) => moderationApi.approveListing(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-listings'] })
  })
  const rejectListing = useMutation({
    mutationFn: ({ id, reason }: { id: string, reason: string }) => moderationApi.rejectListing(id, reason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending-listings'] }); setRejectingId(null); setRejectReason('') }
  })

  const approveKYC = useMutation({
    mutationFn: (id: string) => moderationApi.approveKYC(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pending-kyc'] })
  })
  const rejectKYC = useMutation({
    mutationFn: ({ id, reason }: { id: string, reason: string }) => moderationApi.rejectKYC(id, reason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending-kyc'] }); setRejectingId(null); setRejectReason('') }
  })

  const resolveReport = useMutation({
    mutationFn: (id: string) => moderationApi.resolveReport(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['open-reports'] })
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Moderation Console</h1>
        <p className="text-gray-600">Review pending listings, KYC applications, and user reports.</p>
      </div>

      <div className="flex gap-6 border-b mb-6">
        <button onClick={() => setActiveTab('listings')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'listings' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          Listings {pendingListings?.results.length ? `(${pendingListings.results.length})` : ''}
        </button>
        <button onClick={() => setActiveTab('kyc')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'kyc' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          KYC Requests {pendingKYC?.results.length ? `(${pendingKYC.results.length})` : ''}
        </button>
        <button onClick={() => setActiveTab('history')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'history' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          Approval History
        </button>
        <button onClick={() => setActiveTab('reports')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'reports' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          User Reports {reports?.results.length ? `(${reports.results.length})` : ''}
        </button>
      </div>

      {/* LISTINGS TAB */}
      {activeTab === 'listings' && (
        <>
          {loadingListings && <Loading />}
          {pendingListings?.results.length === 0 && <p className="text-gray-500 py-8">No pending listings.</p>}
          <div className="grid gap-4">
            {pendingListings?.results.map(listing => (
              <div key={listing.id} className="bg-white border rounded-lg p-4 flex gap-4 shadow-sm">
                <div className="w-32 h-32 bg-gray-100 rounded flex-shrink-0">
                  {listing.media[0] && <img src={getMediaUrl(listing.media[0].file)} className="w-full h-full object-cover rounded" />}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-lg">{listing.title}</h3>
                  <p className="text-sm text-gray-500 mb-1">{listing.property_summary.neighbourhood} · {listing.currency} {Number(listing.price).toLocaleString()}</p>
                  <p className="text-xs text-gray-500">By: {listing.created_by_email}</p>
                </div>
                <div className="flex flex-col justify-center gap-2 w-32">
                  {listing.status !== 'SUBMITTED' ? (
                     <span className="text-xs text-center text-gray-500 italic">Already Published</span>
                  ) : rejectingId === listing.id ? (
                    <div className="space-y-2">
                      <input type="text" placeholder="Reason..." value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="w-full border rounded px-2 py-1 text-sm" />
                      <button onClick={() => rejectListing.mutate({ id: listing.id, reason: rejectReason })} className="w-full bg-red-600 text-white py-1 rounded text-sm">Confirm</button>
                      <button onClick={() => setRejectingId(null)} className="w-full bg-gray-200 text-gray-700 py-1 rounded text-sm">Cancel</button>
                    </div>
                  ) : (
                    <>
                      <button onClick={() => approveListing.mutate(listing.id)} className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium">Approve</button>
                      <button onClick={() => setRejectingId(listing.id)} className="w-full bg-white border border-red-600 text-red-600 py-2 rounded hover:bg-red-50 font-medium">Reject</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* KYC TAB */}
      {activeTab === 'kyc' && (
        <>
          {loadingKYC && <Loading />}
          {pendingKYC?.results.length === 0 && <p className="text-gray-500 py-8">No pending KYC requests.</p>}
          <div className="grid gap-4">
            {pendingKYC?.results.map((kyc: any) => (
              <div key={kyc.id} className="bg-white border rounded-lg p-4 shadow-sm">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-bold text-lg text-gray-900">{kyc.type_label}</h3>
                    <p className="text-sm text-gray-600">User: <span className="font-medium text-gray-900">{kyc.user_email}</span></p>
                    <p className="text-xs text-gray-400 mt-1">Submitted: {new Date(kyc.created_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex gap-2">
                    {rejectingId === kyc.id ? (
                      <div className="flex gap-2 items-center">
                        <input type="text" placeholder="Reason..." value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="border rounded px-2 py-1 text-sm w-48" />
                        <button onClick={() => rejectKYC.mutate({ id: kyc.id, reason: rejectReason })} className="bg-red-600 text-white px-3 py-1 rounded text-sm">Confirm</button>
                        <button onClick={() => setRejectingId(null)} className="bg-gray-200 px-3 py-1 rounded text-sm">Cancel</button>
                      </div>
                    ) : (
                      <>
                        <button 
                          onClick={() => approveKYC.mutate(kyc.id)} 
                          disabled={kyc.documents.length === 0}
                          className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Approve
                        </button>
                        <button onClick={() => setRejectingId(kyc.id)} className="bg-white border border-red-600 text-red-600 px-4 py-2 rounded hover:bg-red-50 font-medium text-sm">Reject</button>
                      </>
                    )}
                  </div>
                </div>
                
                {/* Documents */}
                <div className="bg-gray-50 p-3 rounded border">
                  <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Attached Documents</h4>
                  <div className="flex flex-wrap gap-4">
                    {kyc.documents.map((doc: any) => (
                      <a 
                        key={doc.id} 
                        href={getMediaUrl(doc.file)} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 px-4 py-2 rounded-lg shadow-sm hover:shadow hover:bg-emerald-100 transition group"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#047857" strokeWidth="2" className="group-hover:scale-110 transition-transform"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        <span className="text-sm font-bold text-emerald-800">View {doc.document_type}</span>
                      </a>
                    ))}
                    {kyc.documents.length === 0 && <span className="text-sm text-red-500 font-medium">No documents uploaded. You must reject this request.</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* HISTORY TAB */}
      {activeTab === 'history' && (
        <>
          {loadingHistory && <Loading />}
          {history?.results.length === 0 && <p className="text-gray-500 py-8">No KYC history found.</p>}
          <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
            <table className="w-full text-left">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 font-semibold text-sm">User</th>
                  <th className="px-4 py-3 font-semibold text-sm">Type</th>
                  <th className="px-4 py-3 font-semibold text-sm">Status</th>
                  <th className="px-4 py-3 font-semibold text-sm">Reviewed By</th>
                  <th className="px-4 py-3 font-semibold text-sm">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {history?.results.map((h: any) => (
                  <tr key={h.id}>
                    <td className="px-4 py-3 text-sm">{h.user_email}</td>
                    <td className="px-4 py-3 text-sm">{h.type_label}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        h.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                        h.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>{h.status}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">{h.reviewed_by_email || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {h.reviewed_at ? new Date(h.reviewed_at).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* REPORTS TAB */}
      {activeTab === 'reports' && (
        <>
          {loadingReports && <Loading />}
          {reports?.results.length === 0 && <p className="text-gray-500 py-8">No open reports.</p>}
          <div className="grid gap-4">
            {reports?.results.map(report => (
              <div key={report.id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
                <div>
                  <h3 className="font-bold text-red-600">Report: {report.reason}</h3>
                  <p className="text-sm text-gray-700 mt-1">{report.description}</p>
                  <p className="text-xs text-gray-500 mt-2">By: {report.reporter_email}</p>
                </div>
                <button onClick={() => resolveReport.mutate(report.id)} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-black font-medium text-sm">Mark Resolved</button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
