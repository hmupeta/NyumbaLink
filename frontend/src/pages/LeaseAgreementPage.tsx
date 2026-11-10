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

  const isLandlord = user?.id === lease.landlord
  const isTenant = user?.email?.toLowerCase() === lease.tenant_email?.toLowerCase()
  const userSigned = isLandlord ? lease.landlord_signed : lease.tenant_signed
  const bothSigned = lease.landlord_signed && lease.tenant_signed

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

            <div className="border-t pt-6 flex flex-col md:flex-row justify-between items-center gap-4">
              <div>
                <p className="text-sm text-gray-500">Landlord Signature:</p>
                <p className="font-bold text-lg">{lease.landlord_signed ? '✓ Signed' : 'Pending'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Tenant Signature:</p>
                <p className="font-bold text-lg">{lease.tenant_signed ? '✓ Signed' : 'Pending'}</p>
              </div>
            </div>

            {bothSigned ? (
              <div className="mt-6 bg-green-50 border border-green-200 text-green-800 p-4 rounded text-center font-bold">
                ✓ Contract Finalized. Property is now marked as OCCUPIED.
              </div>
            ) : (
              <div className="mt-6">
                {(isLandlord || isTenant) && !userSigned ? (
                  <button onClick={() => signMutation.mutate()} disabled={signMutation.isPending} className="w-full bg-blue-700 text-white py-3 rounded font-medium hover:bg-blue-800">
                    {signMutation.isPending ? 'Signing...' : 'Digitally Sign Agreement'}
                  </button>
                ) : (
                  <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 p-4 rounded text-center">
                    {userSigned ? "You have signed. Waiting for the other party." : "You are not a party to this lease."}
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
