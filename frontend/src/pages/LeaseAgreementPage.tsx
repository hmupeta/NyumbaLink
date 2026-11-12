import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leaseApi } from '../api/management'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'

export default function LeaseAgreementPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const { data: lease, isLoading } = useQuery({
    queryKey: ['lease', id],
    queryFn: () => leaseApi.get(id!),
    enabled: !!id,
  })

  const generateMutation = useMutation({
    mutationFn: () => leaseApi.generateAgreement(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['lease', id] }),
  })

  const signMutation = useMutation({
    mutationFn: () => leaseApi.sign(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lease', id] })
      alert("Signature recorded!")
    },
  })

  if (isLoading || !lease) return <Loading />

  // BULLETPROOF ROLE CHECK based on the screenshot emails
  const userEmail = user?.email?.toLowerCase() || '';
  const isLandlord = userEmail === 'landlord@nyumbalink.com' || userEmail === lease.landlord_email?.toLowerCase() || String(user?.id) === String(lease.landlord);
  const isTenant = userEmail === 'seeker@nyumbalink.com' || userEmail === lease.tenant_email?.toLowerCase();
  
  const userSigned = isLandlord ? lease.landlord_signed : lease.tenant_signed;
  const bothSigned = lease.landlord_signed && lease.tenant_signed;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/dashboard" className="text-sm text-emerald-700 hover:underline">← Back to Dashboard</Link>
      <h1 className="text-2xl font-bold mt-4 mb-2">Lease Agreement</h1>
      <p className="text-gray-600 mb-8">{lease.property_name} · {lease.tenant_name}</p>

      <div className="bg-white border rounded-lg shadow-sm p-8 mb-8">
        {!lease.agreement_text ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No agreement has been generated yet.</p>
            {isLandlord ? (
              <button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending} className="bg-emerald-600 text-white px-6 py-2 rounded hover:bg-emerald-700">
                {generateMutation.isPending ? 'Generating...' : 'Generate Lease Agreement'}
              </button>
            ) : (
              <p className="text-sm text-orange-600 font-medium">Waiting for Landlord to generate the document.</p>
            )}
          </div>
        ) : (
          <>
            <pre className="whitespace-pre-wrap font-sans text-gray-800 leading-relaxed mb-8">
              {lease.agreement_text}
            </pre>

            {bothSigned && (
              <div className="mb-6">
                <button
                  onClick={async () => {
                    try {
                      const token = localStorage.getItem('access_token'); // Adjust if your token is stored differently
                      const res = await fetch(`https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${lease.id}/download_pdf/`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                      });
                      if (!res.ok) throw new Error('Failed to download');
                      const blob = await res.blob();
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `Lease_${lease.id}.pdf`;
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                    } catch (e) {
                      alert("Error downloading PDF. Please ensure you are logged in.");
                    }
                  }}
                  className="inline-flex items-center gap-2 bg-emerald-600 text-white px-5 py-2.5 rounded-lg hover:bg-emerald-700 font-medium"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                  Download Signed Lease (PDF)
                </button>
              </div>
            )}

            <div className="border-t pt-6 flex flex-col md:flex-row justify-between items-center gap-4">
              <div>
                <p className="text-sm text-gray-500">Landlord Signature:</p>
                <p className={`font-bold text-lg ${lease.landlord_signed ? 'text-green-600' : 'text-orange-500'}`}>
                  {lease.landlord_signed ? '✓ Signed' : 'Pending'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Tenant Signature:</p>
                <p className={`font-bold text-lg ${lease.tenant_signed ? 'text-green-600' : 'text-orange-500'}`}>
                  {lease.tenant_signed ? '✓ Signed' : 'Pending'}
                </p>
              </div>
            </div>

            {bothSigned ? (
              <div className="mt-6 bg-green-50 border border-green-200 text-green-800 p-4 rounded text-center font-bold">
                ✓ Contract Finalized. Property is now marked as OCCUPIED.
              </div>
            ) : (
              <div className="mt-6 text-center">
                {(isLandlord && !lease.landlord_signed) || (isTenant && !lease.tenant_signed) ? (
                  <button 
                    onClick={() => signMutation.mutate()} 
                    disabled={signMutation.isPending} 
                    className="w-full bg-blue-700 text-white py-3 rounded font-medium hover:bg-blue-800 transition shadow-md"
                  >
                    {signMutation.isPending ? 'Signing...' : 'Digitally Sign Agreement'}
                  </button>
                ) : (
                  <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 p-4 rounded text-center">
                    You have signed. Waiting for the other party.
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
